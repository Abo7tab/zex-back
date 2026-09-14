<?php

namespace App\Presentation\Http\Controllers\Api;

use App\Application\Location\Actions\GetLocationHistoryAction;
use App\Application\Location\Actions\StoreLocationAction;
use App\Domain\Device\Models\Device;
use App\Presentation\Http\Requests\StoreLocationRequest;
use App\Presentation\Http\Resources\LocationResource;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class LocationController
{
    public function history(Request $request, Device $device, GetLocationHistoryAction $action) { return LocationResource::collection($action->execute($request->user(), $device)); }
    public function store(StoreLocationRequest $request, StoreLocationAction $action): JsonResponse { $location = $action->execute($request->attributes->get('device'), $request->safe()->except('device_uid')); return response()->json(LocationResource::make($location), 201); }

    public function bleRelay(Request $request, StoreLocationAction $action): JsonResponse
    {
        $request->validate([
            'target_device_hash' => 'required|string',
            'latitude' => 'required|numeric|between:-90,90',
            'longitude' => 'required|numeric|between:-180,180',
            'accuracy' => 'nullable|numeric',
            'battery_level' => 'nullable|integer',
            'distance_meters' => 'nullable|numeric|min:0',
        ]);

        // The mobile beacon starts with a zeroed packet before its first GPS fix.
        // Never persist that placeholder as a real location or activity event.
        if ((float) $request->latitude === 0.0 && (float) $request->longitude === 0.0) {
            return response()->json(['message' => 'BLE location is waiting for a GPS fix.'], 422);
        }

        $sourceDevice = $request->attributes->get('device');
        $device = Device::where('device_uid', 'LIKE', $request->target_device_hash . '%')
            ->orWhereRaw('RIGHT(device_uid, 8) = ?', [$request->target_device_hash])
            ->orWhere('device_name', $request->target_device_hash)
            ->first();

        if (!$device) {
            return response()->json(['message' => 'Target device not found'], 404);
        }

        if ($sourceDevice && (int) $sourceDevice->owner_id !== (int) $device->owner_id) {
            return response()->json(['message' => 'Unauthorized BLE relay target'], 403);
        }

        $locationData = $request->only(['latitude', 'longitude', 'accuracy', 'battery_level']);
        $locationData['provider'] = 'ble_mesh';
        
        $location = $action->execute($device, $locationData);
        
        $device->update(['last_seen_at' => now()]);

        try {
            app(\App\Domain\Contracts\NotificationServiceInterface::class)->updateDeviceState($device->device_uid, [
                'last_seen_at' => $device->last_seen_at->toIso8601String(),
                'relay_source' => 'BLE_RELAY',
                'ble_distance_meters' => $request->distance_meters,
                'ble_proximity' => $request->distance_meters !== null && (float) $request->distance_meters <= 5 ? 'NEAR' : 'SEARCHING',
            ]);
        } catch (\Throwable $e) {
            \Illuminate\Support\Facades\Log::warning('BLE proximity RTDB sync failed', ['error' => $e->getMessage()]);
        }

        \App\Application\Services\AuditLogService::log(
            $device->owner_id,
            $device->id,
            'BLE_PROXIMITY_UPDATE',
            null,
            null,
            [
                'message' => 'BLE peer proximity update received',
                'severity' => 'info',
                'payload' => [
                    'lat' => (float) $request->latitude,
                    'lng' => (float) $request->longitude,
                    'target_uid' => $device->device_uid,
                    'source' => 'BLE_RELAY',
                    'battery' => $request->battery_level,
                    'distance_meters' => $request->distance_meters,
                    'proximity' => $request->distance_meters !== null && (float) $request->distance_meters <= 5 ? 'NEAR' : 'SEARCHING',
                    'received_at' => now()->toIso8601String(),
                ],
            ]
        );

        return response()->json(LocationResource::make($location), 201);
    }

    public function smsRelay(Request $request): JsonResponse
    {
        $request->validate([
            'target_device_uid' => 'required|string',
            'latitude' => 'required|numeric',
            'longitude' => 'required|numeric',
            'accuracy' => 'nullable|numeric'
        ]);

        $device = \App\Domain\Device\Models\Device::where('device_uid', $request->target_device_uid)->first();
        if (!$device) {
            return response()->json(['message' => 'Target device not found'], 404);
        }

        $device->update(['last_seen_at' => now()]);

        $device->locations()->create([
            'latitude' => $request->latitude,
            'longitude' => $request->longitude,
            'accuracy' => $request->accuracy ?? 10,
            'is_offline_relay' => true,
            'recorded_at' => now()
        ]);
        
        try {
            app(\App\Domain\Contracts\NotificationServiceInterface::class)->updateDeviceState($device->device_uid, [
                'last_seen_at' => $device->last_seen_at->toIso8601String(),
                'latest_lat' => $request->latitude,
                'latest_lng' => $request->longitude,
                'relay_source' => 'SMS'
            ]);
        } catch (\Exception $e) {}

        return response()->json(['message' => 'SMS Relay processed successfully']);
    }
}
