<?php

namespace App\Infrastructure\Persistence\Eloquent;

use App\Domain\Device\Models\Device;
use App\Domain\Location\Models\Location;
use App\Domain\Location\Repositories\LocationRepositoryInterface;
use Illuminate\Contracts\Pagination\LengthAwarePaginator;

class EloquentLocationRepository implements LocationRepositoryInterface
{
    public function create(Device $device, array $attributes): Location { return $device->locations()->create($attributes); }
    public function history(Device $device): LengthAwarePaginator { return $device->locations()->latest('recorded_at')->paginate(50); }
}
