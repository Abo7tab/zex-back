<?php

namespace App\Application\Device\Actions;

use App\Application\Jobs\SyncFirebaseDeviceState;
use App\Domain\Command\Repositories\CommandRepositoryInterface;
use App\Domain\Device\Models\Device;
use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

class ProcessHeartbeatAction
{
    public function __construct(
        private DeviceRepositoryInterface $devices, 
        private CommandRepositoryInterface $commands,
        private \App\Domain\Contracts\NotificationServiceInterface $firebase
    ) {}

    public function execute(Device $device, ?int $batteryLevel = null, ?string $fcmToken = null): array
    {
        $result = DB::transaction(function () use ($device, $batteryLevel, $fcmToken) {
            $updates = [];
            $now = now();
            $heartbeatWriteSeconds = (int) env('HEARTBEAT_MIN_WRITE_SECONDS', 30);
            $shouldTouchHeartbeat = ! $device->last_heartbeat_at
                || $heartbeatWriteSeconds <= 0
                || $device->last_heartbeat_at->lte($now->copy()->subSeconds($heartbeatWriteSeconds));

            if ($shouldTouchHeartbeat && Schema::hasColumn('devices', 'last_seen_at')) $updates['last_seen_at'] = $now;
            if ($shouldTouchHeartbeat && Schema::hasColumn('devices', 'last_heartbeat_at')) $updates['last_heartbeat_at'] = $now;
            if ($batteryLevel !== null && $device->battery_level !== $batteryLevel && Schema::hasColumn('devices', 'battery_level')) $updates['battery_level'] = $batteryLevel;
            if ($fcmToken !== null && $device->fcm_token !== $fcmToken && Schema::hasColumn('devices', 'fcm_token')) $updates['fcm_token'] = $fcmToken;
            $device = $updates === [] ? $device->refresh() : $this->devices->update($device, $updates);

            $commands = $this->commands->pendingForDevice($device);
            $this->commands->markSent($commands);
            return [$device, $commands->each->refresh(), $updates !== []];
        });

        if ($result[2]) {
            $this->dispatchFirebaseJob(new SyncFirebaseDeviceState($result[0]->device_uid, $result[0]->only([
                'last_seen_at', 'last_heartbeat_at', 'battery_level', 'is_screaming', 'is_tracking_continuous', 'is_locked', 'is_stolen', 'is_searching'
            ])));
        }

        foreach ($result[1] as $command) {
            \App\Application\Services\AuditLogService::log(
                $result[0]->owner_id,
                $result[0]->id,
                'COMMAND_SENT',
                null,
                null,
                [
                    'command_id' => $command->id,
                    'command_type' => $command->type?->value,
                    'sent_at' => optional($command->sent_at)->toIso8601String(),
                    'delivery_channel' => 'heartbeat',
                ]
            );
        }

        return $result;
    }

    private function dispatchFirebaseJob(object $job): void
    {
        try {
            Bus::dispatch($job);
        } catch (\Throwable $e) {
            if (method_exists($job, 'handle')) {
                $job->handle($this->firebase);
            }
        }
    }
}
