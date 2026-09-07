<?php

namespace App\Presentation\Http\Controllers\Api;

use App\Domain\Device\Models\Device;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class DeviceController
{
    public function index(Request $request): JsonResponse
    {
        $devices = $request->user()->devices()->get();

        return response()->json($devices);
    }

    public function show(Request $request, int $id): JsonResponse
    {
        $device = $request->user()->devices()->findOrFail($id);

        return response()->json($device);
    }

    public function register(Request $request): JsonResponse
    {
        $request->validate([
            'owner_id' => ['required', 'exists:owners,id'],
            'device_uid' => ['required', 'string', 'unique:devices,device_uid'],
            'name' => ['required', 'string'],
            'model' => ['nullable', 'string'],
            'os_version' => ['nullable', 'string'],
        ]);

        $device = Device::create([
            'owner_id' => $request->input('owner_id'),
            'device_uid' => $request->input('device_uid'),
            'name' => $request->input('name'),
            'model' => $request->input('model'),
            'os_version' => $request->input('os_version'),
        ]);

        return response()->json($device, 201);
    }

    public function heartbeat(Request $request): JsonResponse
    {
        $request->validate([
            'device_uid' => ['required', 'string', 'exists:devices,device_uid'],
        ]);

        $device = Device::where('device_uid', $request->input('device_uid'))->firstOrFail();
        
        $device->update([
            'last_heartbeat_at' => now(),
        ]);

        return response()->json(['message' => 'Heartbeat updated', 'last_heartbeat_at' => $device->last_heartbeat_at]);
    }
}
