<?php

namespace App\Application\Command\Actions;

use App\Domain\Command\Enums\CommandType;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Support\Facades\DB;

class SetStolenModeAction
{
    public function __construct(private IssueDeviceCommandAction $commands) {}
    public function execute(Owner $owner, Device $device)
    {
        return DB::transaction(function () use ($owner, $device) {
            $commands = [];
            $commands[] = $this->commands->execute($owner, $device, CommandType::STOLEN_MODE, [], ['is_stolen' => true]);
            $commands[] = $this->commands->execute($owner, $device, CommandType::CONTINUOUS_TRACK, ['interval' => 1, 'force_net' => true], ['is_tracking_continuous' => true]);
            $commands[] = $this->commands->execute($owner, $device, CommandType::SCREAM, [], ['is_screaming' => true]);
            $commands[] = $this->commands->execute($owner, $device, CommandType::ENABLE_NET);
            return $commands;
        });
    }
}
