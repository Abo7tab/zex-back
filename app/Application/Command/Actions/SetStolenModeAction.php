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
        $commands = [];
        $commands[] = $this->commands->execute($owner, $device, CommandType::STOLEN_MODE, [], [
            'is_stolen' => true,
            'is_screaming' => true,
            'is_searching' => true
        ]);
        $commands[] = $this->commands->execute($owner, $device, CommandType::CONTINUOUS_TRACK, ['interval' => 30, 'force_net' => true]);
        $commands[] = $this->commands->execute($owner, $device, CommandType::SCREAM, []);
        $commands[] = $this->commands->execute($owner, $device, CommandType::ENABLE_NET);
        return $commands;
    }
}
