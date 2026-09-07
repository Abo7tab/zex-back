<?php

namespace App\Application\Command\Actions;

use App\Domain\Command\Enums\CommandType;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Support\Facades\Hash;
use Symfony\Component\HttpKernel\Exception\HttpException;

class SetFoundModeAction
{
    public function __construct(private IssueDeviceCommandAction $commands) {}
    public function execute(Owner $owner, Device $device, string $pin) { if (! Hash::check($pin, $owner->pin_code)) throw new HttpException(403, 'Invalid PIN.'); return $this->commands->execute($owner, $device, CommandType::FOUND_MODE, [], ['is_stolen' => false]); }
}
