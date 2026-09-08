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
    public function show(Request $request, Device $device, GetOwnedDeviceAction $action): DeviceResource { return DeviceResource::make($action->execute($request->user(), $device)); }
    public function register(RegisterDeviceRequest $request, RegisterDeviceAction $action): JsonResponse { [$device, $token] = $action->execute($request->user(), $request->validated()); return response()->json(['device' => DeviceResource::make($device), 'device_token' => $token], 201); }
    public function heartbeat(HeartbeatRequest $request, ProcessHeartbeatAction $action): JsonResponse 
    { 
        [$device, $commands] = $action->execute($request->attributes->get('device'), $request->validated('battery_level')); 
        return response()->json([
            'device' => DeviceResource::make($device), 
            'pending_commands' => CommandResource::collection($commands),
            'owner_is_searching' => (bool) $device->is_searching,
            'search_interval_seconds' => (int) $device->search_interval_seconds,
            'owner_password_hash' => $device->owner?->password,
        ]); 
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
        // Check auth: owner or device token
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
            'tracking_interval_minutes' => 0, // placeholder since not stored on device yet
            'search_interval_seconds' => (int) $device->search_interval_seconds,
            'last_seen_at' => $device->last_seen_at,
            'battery_level' => $device->battery_level,
        ]);
    }
}
