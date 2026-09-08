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
        return [$device, $token];
    }
}
