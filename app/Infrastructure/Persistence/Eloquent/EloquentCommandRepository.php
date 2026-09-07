<?php

namespace App\Infrastructure\Persistence\Eloquent;

use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Models\Command;
use App\Domain\Command\Repositories\CommandRepositoryInterface;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Support\Collection;

class EloquentCommandRepository implements CommandRepositoryInterface
{
    public function create(Device $device, Owner $owner, array $attributes): Command { return $device->commands()->create($attributes + ['owner_id' => $owner->id]); }
    public function pendingForDevice(Device $device): Collection { return $device->commands()->where('status', CommandStatus::PENDING)->orderBy('id')->get(); }
    public function markSent(Collection $commands): void { Command::whereKey($commands->modelKeys())->where('status', CommandStatus::PENDING)->update(['status' => CommandStatus::SENT, 'sent_at' => now()]); }
    public function update(Command $command, array $attributes): Command { $command->update($attributes); return $command->refresh(); }
}
