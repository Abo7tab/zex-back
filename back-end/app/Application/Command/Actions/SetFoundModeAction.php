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

    public function execute(Owner $owner, Device $device, string $pin)
    {
        $storedPin = (string) $owner->pin_code;
        $valid = preg_match('/^\$2[aby]\$\d{2}\$/', $storedPin) === 1
            ? Hash::check($pin, $storedPin)
            : hash_equals($storedPin, $pin);
        if (! $valid) throw new HttpException(403, 'Invalid PIN.');
        if (! Hash::isHashed($storedPin)) {
            $owner->forceFill(['pin_code' => $pin])->save();
        }
        return $this->commands->execute($owner, $device, CommandType::FOUND_MODE, [], ['is_stolen' => false]);
    }
}
