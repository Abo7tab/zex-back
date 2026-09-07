<?php

namespace App\Application\Command\Actions;

use App\Domain\Command\Enums\CommandType;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;

class StartContinuousTrackingAction
{
    public function __construct(private IssueDeviceCommandAction $commands) {}
    public function execute(Owner $owner, Device $device, array $parameters) { return $this->commands->execute($owner, $device, CommandType::CONTINUOUS_TRACK, $parameters, ['is_tracking_continuous' => true]); }
}
