<?php

namespace App\Application\Command\Actions;

use App\Domain\Command\Enums\CommandType;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;

class LockDeviceAction
{
    public function __construct(private IssueDeviceCommandAction $commands) {}
    public function execute(Owner $owner, Device $device) { return $this->commands->execute($owner, $device, CommandType::LOCK, [], ['is_locked' => true]); }
}
