<?php

namespace App\Application\Alert\Actions;

use App\Domain\Alert\Models\Alert;
use App\Domain\Alert\Repositories\AlertRepositoryInterface;
use App\Domain\Device\Models\Device;

class CreateAlertAction
{
    public function __construct(private AlertRepositoryInterface $alerts) {}
    public function execute(Device $device, array $data): Alert { return $this->alerts->create($device, $data); }
}
