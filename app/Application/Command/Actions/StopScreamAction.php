<?php

namespace App\Application\Command\Actions;

use App\Domain\Command\Enums\CommandType;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Support\Facades\Hash;
use Symfony\Component\HttpKernel\Exception\HttpException;

class StopScreamAction
{
    public function __construct(private IssueDeviceCommandAction $commands) {}
    public function execute(Owner $owner, Device $device, ?string $password, ?string $alarmSecret) {
        if (!empty($password)) {
            if (!Hash::check($password, $owner->password)) {
                throw new HttpException(403, 'Invalid password.');
            }
        } elseif (!empty($alarmSecret)) {
            if (!Hash::check($alarmSecret, $device->alarm_secret_hash)) {
                throw new HttpException(403, 'Invalid alarm secret.');
            }
        } else {
            throw new HttpException(422, 'Password or alarm secret required.');
        }
        return $this->commands->execute($owner, $device, CommandType::STOP_SCREAM, [], ['is_screaming' => false]);
    }
}
