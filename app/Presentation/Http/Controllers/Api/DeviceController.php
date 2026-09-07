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
    public function heartbeat(HeartbeatRequest $request, ProcessHeartbeatAction $action): JsonResponse { [$device, $commands] = $action->execute($request->attributes->get('device'), $request->validated('battery_level')); return response()->json(['device' => DeviceResource::make($device), 'commands' => CommandResource::collection($commands)]); }
}
