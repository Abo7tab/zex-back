<?php

namespace App\Presentation\Http\Controllers\Api;

use App\Application\Command\Actions\IssueDeviceCommandAction;
use App\Application\Command\Actions\LockDeviceAction;
use App\Application\Command\Actions\ProcessCommandResponseAction;
use App\Application\Command\Actions\SetFoundModeAction;
use App\Application\Command\Actions\SetStolenModeAction;
use App\Application\Command\Actions\SendCommandAction;
use App\Application\Command\Actions\StartContinuousTrackingAction;
use App\Application\Command\Actions\StopScreamAction;
use App\Application\Command\Actions\TriggerScreamAction;
use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Enums\CommandType;
use App\Domain\Command\Models\Command;
use App\Domain\Device\Models\Device;
use App\Presentation\Http\Requests\CommandResponseRequest;
use App\Presentation\Http\Requests\FoundDeviceRequest;
use App\Presentation\Http\Requests\SendCommandRequest;
use App\Presentation\Http\Requests\StopScreamRequest;
use App\Presentation\Http\Requests\TrackDeviceRequest;
use App\Presentation\Http\Resources\CommandResource;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class CommandController
{
    public function send(SendCommandRequest $request, Device $device, SendCommandAction $action): JsonResponse { return response()->json(CommandResource::make($action->execute($request->user(), $device, $request->enum('type', CommandType::class), $request->validated('parameters') ?? [])), 201); }
    public function locate(Request $request, Device $device, IssueDeviceCommandAction $action): JsonResponse { return $this->issue($request, $device, CommandType::LOCATE, [], [], $action); }
    public function scream(Request $request, Device $device, TriggerScreamAction $action): JsonResponse { return response()->json(CommandResource::make($action->execute($request->user(), $device)), 201); }
    public function stopScream(StopScreamRequest $request, Device $device, StopScreamAction $action): JsonResponse { return response()->json(CommandResource::make($action->execute($request->user(), $device, $request->input('password'), $request->input('alarm_secret'))), 201); }
    public function track(TrackDeviceRequest $request, Device $device, StartContinuousTrackingAction $action): JsonResponse { return response()->json(CommandResource::make($action->execute($request->user(), $device, $request->validated())), 201); }
    public function stopTracking(Request $request, Device $device, IssueDeviceCommandAction $action): JsonResponse { return $this->issue($request, $device, CommandType::STOP_TRACKING, [], ['is_tracking_continuous' => false], $action); }
    public function lock(Request $request, Device $device, LockDeviceAction $action): JsonResponse { 
        \App\Application\Services\AuditLogService::log($request->user()->id, $device->id, 'LOCK_DEVICE', $request->ip(), $request->userAgent());
        return response()->json(CommandResource::make($action->execute($request->user(), $device)), 201); 
    }
    public function photo(Request $request, Device $device, IssueDeviceCommandAction $action): JsonResponse { return $this->issue($request, $device, CommandType::PHOTO, [], [], $action); }
    public function enableNet(Request $request, Device $device, IssueDeviceCommandAction $action): JsonResponse { 
        \App\Application\Services\AuditLogService::log($request->user()->id, $device->id, 'ENABLE_NET', $request->ip(), $request->userAgent());
        return $this->issue($request, $device, CommandType::ENABLE_NET, [], [], $action); 
    }
    public function stolen(Request $request, Device $device, SetStolenModeAction $action): JsonResponse { 
        \App\Application\Services\AuditLogService::log($request->user()->id, $device->id, 'STOLEN_MODE', $request->ip(), $request->userAgent());
        return response()->json(['message' => 'Stolen mode activated', 'commands' => CommandResource::collection($action->execute($request->user(), $device))], 201); 
    }
    public function found(FoundDeviceRequest $request, Device $device, SetFoundModeAction $action): JsonResponse { 
        \App\Application\Services\AuditLogService::log($request->user()->id, $device->id, 'FOUND_MODE', $request->ip(), $request->userAgent());
        return response()->json(\App\Presentation\Http\Resources\DeviceResource::make($action->execute($request->user(), $device, $request->validated('pin_code'))), 200); 
    }
    public function storeResponse(CommandResponseRequest $request, Command $command, ProcessCommandResponseAction $action): CommandResource { return CommandResource::make($action->execute($request->attributes->get('device'), $command, $request->enum('status', CommandStatus::class), $request->validated('response'))); }
    private function issue(Request $request, Device $device, CommandType $type, array $parameters, array $state, IssueDeviceCommandAction $action): JsonResponse { return response()->json(CommandResource::make($action->execute($request->user(), $device, $type, $parameters, $state)), 201); }
}
