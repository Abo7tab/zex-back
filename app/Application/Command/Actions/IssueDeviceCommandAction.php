<?php

namespace App\Application\Command\Actions;

use App\Application\Jobs\PushFirebaseCommand;
use App\Application\Jobs\SendFirebaseDeviceNotification;
use App\Application\Jobs\SyncFirebaseDeviceState;
use App\Application\Services\AuditLogService;
use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Enums\CommandType;
use App\Domain\Command\Models\Command;
use App\Domain\Command\Repositories\CommandRepositoryInterface;
use App\Domain\Device\Models\Device;
use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use App\Domain\Owner\Models\Owner;
use Illuminate\Auth\Access\AuthorizationException;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\Schema;

class IssueDeviceCommandAction
{
    public function __construct(
        private CommandRepositoryInterface $commands, 
        private DeviceRepositoryInterface $devices,
        private \App\Domain\Contracts\NotificationServiceInterface $firebase
    ) {}

    public function execute(Owner $owner, Device $device, CommandType $type, array $parameters = [], array $deviceState = []): Command
    {
        if ($device->owner_id !== $owner->id) throw new AuthorizationException();

        if ($type === CommandType::LOCATE) {
            $existingLocate = Command::query()
                ->where('device_id', $device->id)
                ->where('type', CommandType::LOCATE->value)
                ->whereIn('status', [CommandStatus::PENDING->value, CommandStatus::SENT->value])
                ->where('created_at', '>=', now()->subSeconds((int) env('LOCATE_DEDUPE_SECONDS', 45)))
                ->latest('id')
                ->first();

            if ($existingLocate) {
                AuditLogService::log(
                    $owner->id,
                    $device->id,
                    'COMMAND_DEDUPED',
                    null,
                    null,
                    [
                        'command_id' => $existingLocate->id,
                        'command_type' => $type->value,
                        'message' => 'A recent location request is already waiting for the phone.',
                    ]
                );

                return $existingLocate;
            }
        }

        if ($deviceState !== []) {
            $persistedState = collect($deviceState)
                ->filter(fn ($value, $column) => Schema::hasColumn('devices', (string) $column))
                ->all();

            if ($persistedState !== []) {
                $this->devices->update($device, $persistedState);
            }

            $this->dispatchFirebaseJob(new SyncFirebaseDeviceState($device->device_uid, $persistedState !== [] ? $persistedState : $deviceState));
        }
        
        $command = $this->commands->create($device, $owner, ['type' => $type, 'status' => CommandStatus::PENDING, 'parameters' => $parameters]);

        \App\Application\Services\AuditLogService::log(
            $owner->id,
            $device->id,
            'COMMAND_QUEUED',
            null,
            null,
            [
                'command_id' => $command->id,
                'command_type' => $type->value,
                'queued_at' => now()->toIso8601String(),
                'parameters' => $parameters,
            ]
        );
        
        $this->dispatchFirebaseJob(new PushFirebaseCommand($device->device_uid, $command->toArray()));

        if ($device->fcm_token) {
            $fcmPayload = array_merge([
                'id'   => (string) $command->id,
                'type' => (string) $command->type->value,
            ], $parameters);
            $this->dispatchFirebaseJob(new SendFirebaseDeviceNotification($device->fcm_token, 'New Command', "Command: {$type->value}", $fcmPayload));
        }
        
        return $command;
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
