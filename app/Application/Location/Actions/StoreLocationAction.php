<?php

namespace App\Application\Location\Actions;

use App\Domain\Device\Models\Device;
use App\Domain\Location\Models\Location;
use App\Domain\Location\Repositories\LocationRepositoryInterface;

class StoreLocationAction
{
    public function __construct(private LocationRepositoryInterface $locations) {}
    public function execute(Device $device, array $data): Location
    {
        return $this->locations->create($device, $data + ['recorded_at' => $data['recorded_at'] ?? now()]);
    }
}
