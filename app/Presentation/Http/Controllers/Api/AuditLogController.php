<?php
namespace App\Presentation\Http\Controllers\Api;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class AuditLogController {
    public function index(Request $request) {
        $user = $request->user();
        $logs = DB::table('audit_logs')
            ->leftJoin('devices', 'audit_logs.device_id', '=', 'devices.id')
            ->where('audit_logs.owner_id', $user->id)
            ->select('audit_logs.*', 'devices.device_name')
            ->orderByDesc('audit_logs.created_at')
            ->limit(200)
            ->get()
            ->map(function ($log) use ($user) {
                $details = json_decode($log->details, true) ?? [];
                $payload = $details['payload'] ?? null;

                // Resolve target_uid → human-readable device name
                $targetDeviceName = null;
                if (!empty($payload['target_uid'])) {
                    $targetDevice = DB::table('devices')
                        ->where('owner_id', $user->id)
                        ->where(function ($q) use ($payload) {
                            $q->where('device_uid', $payload['target_uid'])
                              ->orWhere('device_uid', 'LIKE', '%' . $payload['target_uid'] . '%');
                        })
                        ->value('device_name');
                    $targetDeviceName = $targetDevice ?: $payload['target_uid'];
                }

                return [
                    'id'                 => $log->id,
                    'timestamp'          => $log->created_at,
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
        $device = $request->attributes->get('device');
        $request->validate([
            'message' => 'required|string', 
            'severity' => 'nullable|string', 
            'payload' => 'nullable|array'
        ]);
        
        DB::table('audit_logs')->insert([
            'owner_id' => $device->owner_id,
            'device_id' => $device->id,
            'action' => 'mobile_activity',
            'details' => json_encode([
                'message' => $request->message, 
                'severity' => $request->severity ?? 'info', 
                'payload' => $request->payload
            ]),
            'created_at' => now(),
            'updated_at' => now()
        ]);
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
}
