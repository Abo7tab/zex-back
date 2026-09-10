<?php

namespace App\Application\Command\Actions;

use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Models\Command;
use App\Domain\Command\Repositories\CommandRepositoryInterface;
use App\Domain\Device\Models\Device;
use Illuminate\Validation\ValidationException;
use Symfony\Component\HttpKernel\Exception\HttpException;

class ProcessCommandResponseAction
{
    public function __construct(
        private CommandRepositoryInterface $commands,
        private \App\Domain\Contracts\NotificationServiceInterface $firebase
    ) {}
    public function execute(Device $device, Command $command, CommandStatus $status, ?array $response): Command
    {
        if ($command->device_id !== $device->id) {
            throw new HttpException(403, 'This device does not own the command.');
        }
        if (! in_array($command->status, [CommandStatus::PENDING, CommandStatus::SENT], true)) {
            throw ValidationException::withMessages(['status' => ['This command cannot be updated.']]);
        }
        if (! in_array($status, [CommandStatus::EXECUTED, CommandStatus::FAILED], true)) {
            throw ValidationException::withMessages(['status' => ['Only EXECUTED or FAILED is accepted.']]);
        }
        $updated = $this->commands->update($command, ['status' => $status, 'response' => $response, 'executed_at' => $status === CommandStatus::EXECUTED ? now() : null]);
        
        $device->update(['last_heartbeat_at' => now()]);
        $this->firebase->updateDeviceState($device->device_uid, [
            'last_heartbeat_at' => now()->toIso8601String(),
        ]);
        
        $this->firebase->removeCommandRealtime($device->device_uid, $command->id);
        return $updated;
    }
}
