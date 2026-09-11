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
            'latitude' => 'required|numeric',
            'longitude' => 'required|numeric',
            'accuracy' => 'nullable|numeric',
            'battery_level' => 'nullable|integer',
        ]);

        $device = Device::where('device_uid', 'LIKE', $request->target_device_hash . '%')
            ->orWhere('device_name', $request->target_device_hash)
            ->first();

        if (!$device) {
            return response()->json(['message' => 'Target device not found'], 404);
        }

        $locationData = $request->only(['latitude', 'longitude', 'accuracy', 'battery_level']);
        $locationData['provider'] = 'ble_mesh';
        
        $location = $action->execute($device, $locationData);
        
        $device->update(['last_seen_at' => now()]);

        return response()->json(LocationResource::make($location), 201);
    }
}
