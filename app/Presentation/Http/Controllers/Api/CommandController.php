<?php

namespace App\Presentation\Http\Controllers\Api;

use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Models\Command;
use App\Domain\Device\Models\Device;
use App\Presentation\Http\Requests\SendCommandRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class CommandController
{
    public function send(SendCommandRequest $request): JsonResponse
    {
        $device = $request->user()->devices()->findOrFail($request->validated('device_id'));

        $command = $device->commands()->create([
            'owner_id' => $request->user()->id,
            'type' => $request->validated('type'),
            'status' => CommandStatus::PENDING,
            'parameters' => $request->validated('parameters') ?? [],
            'sent_at' => now(),
        ]);

        return response()->json($command, 201);
    }

    public function storeResponse(Request $request): JsonResponse
    {
        $request->validate([
            'device_uid' => ['required', 'string', 'exists:devices,device_uid'],
            'command_id' => ['required', 'integer'],
            'status' => ['required', 'string', 'enum:' . CommandStatus::class],
            'response' => ['nullable', 'array'],
        ]);

        $device = Device::where('device_uid', $request->input('device_uid'))->firstOrFail();
        
        $command = $device->commands()->where('id', $request->input('command_id'))->firstOrFail();

        $status = CommandStatus::from($request->input('status'));

        $command->update([
            'status' => $status,
            'response' => $request->input('response'),
            'executed_at' => match($status) {
                CommandStatus::EXECUTED => now(),
                CommandStatus::FAILED => now(),
                default => null,
            },
        ]);

        return response()->json($command);
    }
}
