<?php

namespace App\Infrastructure\Persistence\Eloquent;

use App\Domain\Device\Models\Device;
use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use App\Domain\Owner\Models\Owner;
use Illuminate\Support\Collection;

class EloquentDeviceRepository implements DeviceRepositoryInterface
{
    public function createForOwner(Owner $owner, array $attributes): Device { return $owner->devices()->create($attributes); }
    public function findByUid(string $uid): ?Device { return Device::where('device_uid', $uid)->first(); }
    public function findOwnedById(Owner $owner, int $id): ?Device { return $owner->devices()->find($id); }
    public function allForOwner(Owner $owner): Collection { return $owner->devices()->latest()->get(); }
    public function update(Device $device, array $attributes): Device { $device->update($attributes); return $device->refresh(); }
}
