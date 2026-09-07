<?php

namespace App\Domain\Device\Repositories;

use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Support\Collection;

interface DeviceRepositoryInterface
{
    public function createForOwner(Owner $owner, array $attributes): Device;
    public function findByUid(string $uid): ?Device;
    public function findOwnedById(Owner $owner, int $id): ?Device;
    public function allForOwner(Owner $owner): Collection;
    public function update(Device $device, array $attributes): Device;
}
