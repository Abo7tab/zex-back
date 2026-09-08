<?php

namespace App\Application\Device\Actions;

use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Auth\Access\AuthorizationException;

class GetOwnedDeviceAction
{
    public function execute(Owner $owner, Device $device): Device
    {
        if ($device->owner_id !== $owner->id) throw new AuthorizationException();
        return $device;
    }
}
