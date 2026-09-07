<?php

namespace App\Application\Location\Actions;

use App\Domain\Device\Models\Device;
use App\Domain\Location\Repositories\LocationRepositoryInterface;
use App\Domain\Owner\Models\Owner;
use Illuminate\Auth\Access\AuthorizationException;

class GetLocationHistoryAction
{
    public function __construct(private LocationRepositoryInterface $locations) {}
    public function execute(Owner $owner, Device $device)
    {
        if ($device->owner_id !== $owner->id) throw new AuthorizationException();
        return $this->locations->history($device);
    }
}
