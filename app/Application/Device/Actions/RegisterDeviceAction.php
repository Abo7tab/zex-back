<?php

namespace App\Application\Device\Actions;

use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use App\Domain\Owner\Models\Owner;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

class RegisterDeviceAction
{
    public function __construct(private DeviceRepositoryInterface $devices) {}

    public function execute(Owner $owner, array $data): array
    {
        $token = Str::random(64);
        $device = $this->devices->createForOwner($owner, $data + ['device_token_hash' => Hash::make($token)]);
        
        $alarmSecret = (string) random_int(100000, 999999);
        $device->alarm_secret_hash = \Illuminate\Support\Facades\Hash::make($alarmSecret);
        if (isset($attributes['fcm_token'])) {
            $device->fcm_token = $attributes['fcm_token'];
        }
        $device->save();
        $device->alarm_secret_plain = $alarmSecret; // temporary attribute for response
        return [$device, $token];

    }
}
