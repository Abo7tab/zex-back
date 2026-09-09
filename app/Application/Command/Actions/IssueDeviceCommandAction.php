<?php

namespace App\Application\Command\Actions;

use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Enums\CommandType;
use App\Domain\Command\Models\Command;
use App\Domain\Command\Repositories\CommandRepositoryInterface;
use App\Domain\Device\Models\Device;
use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use App\Domain\Owner\Models\Owner;
use Illuminate\Auth\Access\AuthorizationException;

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
        if ($deviceState !== []) {
            $this->devices->update($device, $deviceState);
            // Sync status to RTDB if state changes
            try {
                $this->firebase->updateDeviceState($device->device_uid, $deviceState);
            } catch (\Throwable $e) {
                \Illuminate\Support\Facades\Log::warning('Firebase status sync failed', ['error' => $e->getMessage()]);
            }
        }
        
        $command = $this->commands->create($device, $owner, ['type' => $type, 'status' => CommandStatus::PENDING, 'parameters' => $parameters]);
        
        try {
            $this->firebase->pushCommandRealtime($device->device_uid, $command->toArray());
            if ($device->fcm_token) {
                $fcmPayload = array_merge([
                    'id'   => (string) $command->id,
                    'type' => (string) $command->type->value,
                ], $parameters);
                $this->firebase->sendToDevice($device->fcm_token, 'New Command', "Command: {$type->value}", $fcmPayload);
            }
        } catch (\Throwable $e) {
            \Illuminate\Support\Facades\Log::warning('Firebase command push failed', ['error' => $e->getMessage()]);
        }
        
        return $command;
    }
}
