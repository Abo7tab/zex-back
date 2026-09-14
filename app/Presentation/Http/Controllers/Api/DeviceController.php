<?php

namespace App\Presentation\Http\Controllers\Api;

use App\Application\Device\Actions\ProcessHeartbeatAction;
use App\Application\Device\Actions\RegisterDeviceAction;
use App\Application\Device\Actions\GetOwnedDeviceAction;
use App\Application\Device\Actions\GetOwnerDevicesAction;
use App\Domain\Device\Models\Device;
use App\Presentation\Http\Requests\HeartbeatRequest;
use App\Presentation\Http\Requests\RegisterDeviceRequest;
use App\Presentation\Http\Resources\CommandResource;
use App\Presentation\Http\Resources\DeviceResource;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class DeviceController
{
    public function index(Request $request, GetOwnerDevicesAction $action) { return DeviceResource::collection($action->execute($request->user())); }
    public function show(Request $request, Device $device, GetOwnedDeviceAction $action): DeviceResource { 
        $device = $action->execute($request->user(), $device);
        $device->load(['lastLocation', 'alerts' => fn($q) => $q->where('is_read', false)->latest()->limit(10)]);
        return DeviceResource::make($device); 
    }
    
    public function relayTelemetry(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'target_device_uid' => 'required|string',
            'latitude' => 'required|numeric',
            'longitude' => 'required|numeric',
            'relay_source' => 'required|string|in:BLE_MESH,SMS_RELAY',
            'battery_level' => 'nullable|integer|min:0|max:100',
        ]);

        $device = Device::where('device_uid', $validated['target_device_uid'])->orWhere('device_uid', 'LIKE', '%' . $validated['target_device_uid'])->firstOrFail();
        
        // Ensure the owner owns the target device
        abort_if($device->owner_id !== $request->user()->id, 403, 'Unauthorized');

        $device->update([
            'last_seen_at' => now(),
            'last_heartbeat_at' => now()
        ]);

        $device->locations()->create([
            'latitude' => $validated['latitude'],
            'longitude' => $validated['longitude'],
            'accuracy' => 10,
            'is_offline_relay' => true,
            'recorded_at' => now()
        ]);
        
        \App\Application\Services\AuditLogService::log(
            $request->user()->id, 
            $device->id, 
            'RELAY_TELEMETRY_' . $validated['relay_source'], 
            $request->ip(), 
            $request->userAgent(),
            [
                'message' => $validated['relay_source'] === 'SMS_RELAY'
                    ? 'SMS location reply received and relayed'
                    : 'BLE peer location discovered and relayed',
                'severity' => 'info',
                'payload' => [
                    'lat' => (float) $validated['latitude'],
                    'lng' => (float) $validated['longitude'],
                    'target_uid' => $device->device_uid,
                    'source' => $validated['relay_source'] === 'SMS_RELAY' ? 'SMS_REPLY' : 'BLE_RELAY',
                    'relay_source' => $validated['relay_source'],
                    'battery_level' => $validated['battery_level'] ?? null,
                    'received_at' => now()->toIso8601String(),
                ],
            ]
        );

        try {
            app(\App\Domain\Contracts\NotificationServiceInterface::class)->updateDeviceState($device->device_uid, [
                'last_seen_at' => $device->last_seen_at->toIso8601String(),
                'last_heartbeat_at' => $device->last_heartbeat_at->toIso8601String(),
                'relay_source' => $validated['relay_source']
            ]);
            // Keep the same RTDB shape used by online location updates so all
            // clients render an SMS-derived fix on the normal device map.
            app(\App\Domain\Contracts\NotificationServiceInterface::class)->syncLastLocation($device->device_uid, [
                'latitude' => (float) $validated['latitude'],
                'longitude' => (float) $validated['longitude'],
                'accuracy' => 10.0,
                'provider' => 'sms_relay',
                'recorded_at' => now()->toIso8601String(),
                'relay_source' => $validated['relay_source'],
            ]);
        } catch (\Exception $e) {}

        return response()->json(['message' => 'Relay processed successfully']);
    }

    public function register(RegisterDeviceRequest $request, RegisterDeviceAction $action): JsonResponse { [$device, $token] = $action->execute($request->user(), $request->validated()); return response()->json(['device' => DeviceResource::make($device), 'device_token' => $token], 201); }
    
    public function destroy(Request $request, Device $device, \App\Domain\Contracts\NotificationServiceInterface $firebase): JsonResponse 
    {
        abort_if($device->owner_id !== $request->user()->id, 403, 'Unauthorized');
        abort_if(!\Illuminate\Support\Facades\Hash::check($request->input('password'), $request->user()->password), 403, 'Invalid password');
        
        \App\Application\Services\AuditLogService::log($request->user()->id, $device->id, 'DELETE_DEVICE', $request->ip(), $request->userAgent());
        
        $firebase->deleteDeviceState($device->device_uid);
        $device->delete();
        return response()->json(['message' => 'Device deleted']);
    }
    
    public function heartbeat(HeartbeatRequest $request, ProcessHeartbeatAction $action): JsonResponse 
    { 
        [$device, $commands] = $action->execute($request->attributes->get('device'), $request->validated('battery_level'), $request->input('fcm_token')); 
        return response()->json([
            'device' => DeviceResource::make($device), 
            'pending_commands' => CommandResource::collection($commands),
            'owner_is_searching' => (bool) $device->is_searching,
            'search_interval_seconds' => (int) $device->search_interval_seconds,
            'is_power_saver' => (bool) $device->is_power_saver,
        ]); 
    }

    public function powerSaver(Request $request, Device $device): JsonResponse {
        abort_if($device->owner_id !== $request->user()->id, 403, 'Unauthorized');
        $validated = $request->validate(['is_power_saver' => 'required|boolean']);
        $device->update(['is_power_saver' => $validated['is_power_saver']]);
        
        $device->commands()->create([
            'type' => $validated['is_power_saver'] ? 'POWER_SAVER_ON' : 'POWER_SAVER_OFF',
            'status' => 'PENDING',
            'owner_id' => $request->user()->id
        ]);
        
        try {
            app(\App\Domain\Contracts\NotificationServiceInterface::class)->updateDeviceState($device->device_uid, [
                'is_power_saver' => (bool) $device->is_power_saver,
            ]);
        } catch (\Exception $e) {}

        return response()->json(['status' => 'success', 'is_power_saver' => $device->is_power_saver, 'data' => DeviceResource::make($device)]);
    }

    public function searchMode(Request $request, Device $device, \App\Application\Device\Actions\SetSearchModeAction $action): JsonResponse
    {
        abort_if($device->owner_id !== $request->user()->id, 403, 'Unauthorized');
        $validated = $request->validate(['interval_seconds' => 'nullable|integer|min:5|max:3600']);
        $device = $action->execute($device, $validated);
        return response()->json(['device' => DeviceResource::make($device)]);
    }

    public function stopSearch(Request $request, Device $device, \App\Application\Device\Actions\StopSearchModeAction $action): JsonResponse
    {
        abort_if($device->owner_id !== $request->user()->id, 403, 'Unauthorized');
        $device = $action->execute($device);
        return response()->json(['device' => DeviceResource::make($device)]);
    }

    public function status(Request $request, Device $device): JsonResponse
    {
        $user = \Illuminate\Support\Facades\Auth::guard('sanctum')->user();
        $isOwner = $user && $device->owner_id === $user->id;
        $isDevice = $request->header('X-Device-Token') && \Illuminate\Support\Facades\Hash::check($request->header('X-Device-Token'), $device->device_token_hash);
        
        abort_if(!$isOwner && !$isDevice, 403, 'Unauthorized');

        return response()->json([
            'device_uid' => $device->device_uid,
            'is_searching' => (bool) $device->is_searching,
            'is_stolen' => (bool) $device->is_stolen,
            'is_screaming' => (bool) $device->is_screaming,
            'is_tracking_continuous' => (bool) $device->is_tracking_continuous,
            'is_power_saver' => (bool) $device->is_power_saver,
            'tracking_interval_minutes' => 0,
            'search_interval_seconds' => (int) $device->search_interval_seconds,
            'last_seen_at' => $device->last_seen_at,
            'battery_level' => $device->battery_level,
        ]);
    }
}
