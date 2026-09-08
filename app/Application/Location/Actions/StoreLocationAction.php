<?php

namespace App\Application\Location\Actions;

use App\Domain\Device\Models\Device;
use App\Domain\Location\Models\Location;
use App\Domain\Location\Repositories\LocationRepositoryInterface;

class StoreLocationAction
{
    public function __construct(
        private LocationRepositoryInterface $locations,
        private \App\Domain\Contracts\NotificationServiceInterface $firebase
    ) {}
    public function execute(Device $device, array $data): Location
    {
        $location = $this->locations->create($device, $data + ['recorded_at' => $data['recorded_at'] ?? now()]);
        $this->firebase->syncLastLocation($device->device_uid, $location->toArray());
        return $location;
    }
}
