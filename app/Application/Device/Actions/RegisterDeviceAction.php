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
        $token = bin2hex(random_bytes(32));
        $device = $this->devices->createForOwner($owner, $data + ['device_token_hash' => Hash::make($token)]);
        
        $alarmSecret = bin2hex(random_bytes(32));
        $device->alarm_secret_hash = \Illuminate\Support\Facades\Hash::make($alarmSecret);
        if (isset($data['fcm_token'])) {
            $device->fcm_token = $data['fcm_token'];
        }
        $device->save();
        $device->alarm_secret_plain = $alarmSecret;
        return [$device, $token];

    }
}
