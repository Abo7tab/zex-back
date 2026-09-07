<?php

namespace App\Domain\Location\Repositories;

use App\Domain\Device\Models\Device;
use App\Domain\Location\Models\Location;
use Illuminate\Contracts\Pagination\LengthAwarePaginator;

interface LocationRepositoryInterface
{
    public function create(Device $device, array $attributes): Location;
    public function history(Device $device): LengthAwarePaginator;
}
