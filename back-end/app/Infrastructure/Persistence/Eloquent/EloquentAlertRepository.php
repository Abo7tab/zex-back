<?php

namespace App\Infrastructure\Persistence\Eloquent;

use App\Domain\Alert\Models\Alert;
use App\Domain\Alert\Repositories\AlertRepositoryInterface;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Contracts\Pagination\LengthAwarePaginator;

class EloquentAlertRepository implements AlertRepositoryInterface
{
    public function create(Device $device, array $attributes): Alert { return $device->alerts()->create($attributes + ['owner_id' => $device->owner_id]); }
    public function forOwner(Owner $owner): LengthAwarePaginator { return $owner->alerts()->latest()->paginate(50); }
    public function findOwnedById(Owner $owner, int $id): ?Alert { return $owner->alerts()->find($id); }
    public function unreadCount(Owner $owner): int { return $owner->alerts()->where('is_read', false)->count(); }
}
