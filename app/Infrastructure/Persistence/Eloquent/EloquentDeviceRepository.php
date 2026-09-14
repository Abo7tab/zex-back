<?php

namespace App\Infrastructure\Persistence\Eloquent;

use App\Domain\Device\Models\Device;
use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use Illuminate\Support\Facades\Hash;
use App\Domain\Owner\Models\Owner;
use Illuminate\Support\Collection;

class EloquentDeviceRepository implements DeviceRepositoryInterface
{
    public function createForOwner(Owner $owner, array $attributes): Device { return $owner->devices()->create($attributes); }
    public function findByUid(string $uid): ?Device { return Device::where('device_uid', $uid)->first(); }

    public function findByToken(string $token): ?Device
    {
        if (trim($token) === '') return null;

        // Password hashes cannot be queried directly. This fallback is used by
        // legacy mobile payloads that authenticate with X-Device-Token only.
        return Device::whereNotNull('device_token_hash')
            ->get()
            ->first(fn (Device $device) => Hash::check($token, (string) $device->device_token_hash));
    }
    public function findOwnedById(Owner $owner, int $id): ?Device { return $owner->devices()->find($id); }
    public function allForOwner(Owner $owner): Collection { return $owner->devices()->with('lastLocation')->latest()->get(); }
    public function update(Device $device, array $attributes): Device { $device->update($attributes); return $device->refresh(); }
}
