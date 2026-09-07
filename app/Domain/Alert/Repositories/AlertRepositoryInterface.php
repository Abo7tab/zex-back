<?php

namespace App\Domain\Alert\Repositories;

use App\Domain\Alert\Models\Alert;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Contracts\Pagination\LengthAwarePaginator;

interface AlertRepositoryInterface
{
    public function create(Device $device, array $attributes): Alert;
    public function forOwner(Owner $owner): LengthAwarePaginator;
    public function findOwnedById(Owner $owner, int $id): ?Alert;
    public function unreadCount(Owner $owner): int;
}
