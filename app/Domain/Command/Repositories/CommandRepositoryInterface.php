<?php

namespace App\Domain\Command\Repositories;

use App\Domain\Command\Models\Command;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Support\Collection;

interface CommandRepositoryInterface
{
    public function create(Device $device, Owner $owner, array $attributes): Command;
    public function pendingForDevice(Device $device): Collection;
    public function markSent(Collection $commands): void;
    public function update(Command $command, array $attributes): Command;
}
