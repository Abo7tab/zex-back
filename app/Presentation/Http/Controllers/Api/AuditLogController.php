<?php
namespace App\Presentation\Http\Controllers\Api;
use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Models\Command;
use App\Domain\Device\Models\Device;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

class AuditLogController {
    public function index(Request $request) {
        $this->pruneExpiredLogs();
        $this->surfaceCommandWaitStates($request->user()->id);

        $user = $request->user();
        $hasRetentionColumns = $this->hasRetentionColumns();
        $rawLogs = DB::table('audit_logs')
            ->leftJoin('devices', 'audit_logs.device_id', '=', 'devices.id')
            ->where('audit_logs.owner_id', $user->id)
            ->select('audit_logs.*', 'devices.device_name')
            ->orderByDesc('audit_logs.created_at')
            ->limit(200)
            ->get();

        $ownerDevices = DB::table('devices')
            ->where('owner_id', $user->id)
            ->pluck('device_name', 'device_uid');

        $logs = $rawLogs
            ->map(function ($log) use ($ownerDevices, $hasRetentionColumns) {
                $details = json_decode($log->details, true) ?? [];
                $payload = $details['payload'] ?? null;

                $targetDeviceName = null;
                if (!empty($payload['target_uid'])) {
                    $targetUid = (string) $payload['target_uid'];
                    $targetDeviceName = $ownerDevices[$targetUid] ?? null;

                    if (! $targetDeviceName) {
                        foreach ($ownerDevices as $deviceUid => $deviceName) {
                            if (str_contains((string) $deviceUid, $targetUid) || str_contains($targetUid, (string) $deviceUid)) {
                                $targetDeviceName = $deviceName;
                                break;
                            }
                        }
                    }

                    $targetDeviceName ??= $targetUid;
                }

                $expiresAt = $hasRetentionColumns && $log->expires_at ? \Carbon\Carbon::parse($log->expires_at) : null;
                $warnsBeforeDeletion = $expiresAt && $expiresAt->isFuture() && $expiresAt->lessThanOrEqualTo(now()->addDay());

                return [
                    'id'                 => $log->id,
                    'device_id'          => $log->device_id,
                    'timestamp'          => $log->created_at,
                    'expires_at'         => $hasRetentionColumns ? $log->expires_at : null,
                    'retention_warning'  => $warnsBeforeDeletion,
                    'retention_warning_message' => $warnsBeforeDeletion ? 'This phone log will be deleted in less than 24 hours.' : null,
                    'can_extend_retention' => $expiresAt && ! $log->retention_extended_at,
                    'action'             => $log->action,
                    'device_name'        => $log->device_name,
                    'target_device_name' => $targetDeviceName,
                    'severity'           => $details['severity'] ?? 'info',
                    'message'            => $details['message'] ?? 'Activity Logged',
                    'payload'            => $payload,
                    'metadata'           => collect($details)->except(['message', 'severity', 'payload'])->all(),
                ];
            });
        return response()->json($logs);
    }

    public function storeMobileActivity(Request $request) {
        $device = $request->attributes->get('device') ?: $request->route('device');
        abort_if(! $device instanceof Device, 422, 'Device context is required.');
        if ($request->user()) {
            abort_if((int) $device->owner_id !== (int) $request->user()->id, 403, 'Unauthorized');
        }

        $request->validate([
            'message' => 'required|string', 
            'severity' => 'nullable|string', 
            'payload' => 'nullable|array'
        ]);
        
        \App\Application\Services\AuditLogService::log(
            $device->owner_id,
            $device->id,
            'mobile_activity',
            null,
            null,
            [
                'message' => $request->message, 
                'severity' => $request->severity ?? 'info', 
                'payload' => $request->payload
            ]
        );

        return response()->json(['success' => true]);
    }

    public function destroy(Request $request, int $id) {
        $deleted = DB::table('audit_logs')
            ->where('id', $id)
            ->where('owner_id', $request->user()->id)
            ->delete();

        abort_if($deleted === 0, 404, 'Activity log not found');
        return response()->json(['success' => true]);
    }

    public function clear(Request $request) {
        $deleted = DB::table('audit_logs')
            ->where('owner_id', $request->user()->id)
            ->delete();

        return response()->json(['success' => true, 'deleted' => $deleted]);
    }

    public function extendRetention(Request $request, int $id) {
        abort_if(! $this->hasRetentionColumns(), 422, 'Activity log retention is not enabled yet.');

        $log = DB::table('audit_logs')
            ->where('id', $id)
            ->where('owner_id', $request->user()->id)
            ->first();

        abort_if(! $log, 404, 'Activity log not found');
        abort_if($log->retention_extended_at, 422, 'Activity log retention can only be extended once.');

        $currentExpiry = $log->expires_at ? \Carbon\Carbon::parse($log->expires_at) : now();
        $newExpiry = ($currentExpiry->isFuture() ? $currentExpiry : now())->addDays(3);

        DB::table('audit_logs')
            ->where('id', $id)
            ->update([
                'expires_at' => $newExpiry,
                'retention_extended_at' => now(),
                'updated_at' => now(),
            ]);

        return response()->json([
            'success' => true,
            'expires_at' => $newExpiry->toIso8601String(),
            'can_extend_retention' => false,
        ]);
    }

    private function pruneExpiredLogs(): void
    {
        $threeDaysAgo = now()->subDays(3);

        if (! $this->hasRetentionColumns()) {
            DB::table('audit_logs')
                ->where('created_at', '<=', $threeDaysAgo)
                ->delete();
            return;
        }

        DB::table('audit_logs')
            ->where(function ($query) use ($threeDaysAgo) {
                $query->where(function ($inner) {
                    $inner->whereNotNull('expires_at')
                        ->where('expires_at', '<=', now());
                })->orWhere(function ($inner) use ($threeDaysAgo) {
                    $inner->whereNull('expires_at')
                        ->where('created_at', '<=', $threeDaysAgo);
                });
            })
            ->delete();
    }

    private function surfaceCommandWaitStates(int $ownerId): void
    {
        $pendingSeconds = max(30, (int) env('COMMAND_PENDING_NOTICE_SECONDS', 60));
        $timeoutSeconds = max(30, (int) env('COMMAND_IN_FLIGHT_SECONDS', 120));

        Command::query()
            ->where('owner_id', $ownerId)
            ->where('status', CommandStatus::PENDING->value)
            ->where('created_at', '<=', now()->subSeconds($pendingSeconds))
            ->orderByDesc('id')
            ->limit(30)
            ->get()
            ->each(function (Command $command) use ($pendingSeconds) {
                $cacheKey = "commands:{$command->id}:pending-wait-notice";
                if (! Cache::add($cacheKey, true, now()->addMinutes(5))) {
                    return;
                }

                \App\Application\Services\AuditLogService::log(
                    $command->owner_id,
                    $command->device_id,
                    'COMMAND_WAITING',
                    null,
                    null,
                    [
                        'command_id' => $command->id,
                        'command_type' => $command->type?->value,
                        'status' => CommandStatus::PENDING->value,
                        'pending_seconds' => $pendingSeconds,
                        'message' => 'The command is still waiting for the phone to check in.',
                    ]
                );
            });

        Command::query()
            ->where('owner_id', $ownerId)
            ->where('status', CommandStatus::SENT->value)
            ->whereNotNull('sent_at')
            ->where('sent_at', '<', now()->subSeconds($timeoutSeconds))
            ->orderByDesc('id')
            ->limit(30)
            ->get()
            ->each(function (Command $command) use ($timeoutSeconds) {
                $command->update([
                    'status' => CommandStatus::FAILED,
                    'response' => [
                        'error' => "No device response within {$timeoutSeconds} seconds.",
                        'timeout_seconds' => $timeoutSeconds,
                    ],
                ]);

                $cacheKey = "commands:{$command->id}:timeout-notice";
                if (! Cache::add($cacheKey, true, now()->addDay())) {
                    return;
                }

                \App\Application\Services\AuditLogService::log(
                    $command->owner_id,
                    $command->device_id,
                    'COMMAND_TIMEOUT',
                    null,
                    null,
                    [
                        'command_id' => $command->id,
                        'command_type' => $command->type?->value,
                        'status' => CommandStatus::FAILED->value,
                        'timeout_seconds' => $timeoutSeconds,
                        'message' => 'The phone received the command but did not report completion in time.',
                    ]
                );
            });
    }

    private function hasRetentionColumns(): bool
    {
        return Schema::hasColumn('audit_logs', 'expires_at')
            && Schema::hasColumn('audit_logs', 'retention_extended_at');
    }
}
