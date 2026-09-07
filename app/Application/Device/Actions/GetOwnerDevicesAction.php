<?php

namespace App\Application\Device\Actions;

use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use App\Domain\Owner\Models\Owner;

class GetOwnerDevicesAction
{
    public function __construct(private DeviceRepositoryInterface $devices) {}
    public function execute(Owner $owner) { return $this->devices->allForOwner($owner); }
}
