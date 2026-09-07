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
    public function __construct(private CommandRepositoryInterface $commands, private DeviceRepositoryInterface $devices) {}
    public function execute(Owner $owner, Device $device, CommandType $type, array $parameters = [], array $deviceState = []): Command
    {
        if ($device->owner_id !== $owner->id) throw new AuthorizationException();
        if ($deviceState !== []) $this->devices->update($device, $deviceState);
        return $this->commands->create($device, $owner, ['type' => $type, 'status' => CommandStatus::PENDING, 'parameters' => $parameters]);
    }
}
