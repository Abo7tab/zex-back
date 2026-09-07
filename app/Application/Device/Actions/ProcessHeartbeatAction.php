<?php

namespace App\Application\Device\Actions;

use App\Domain\Command\Repositories\CommandRepositoryInterface;
use App\Domain\Device\Models\Device;
use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use Illuminate\Support\Facades\DB;

class ProcessHeartbeatAction
{
    public function __construct(private DeviceRepositoryInterface $devices, private CommandRepositoryInterface $commands) {}

    public function execute(Device $device, ?int $batteryLevel): array
    {
        return DB::transaction(function () use ($device, $batteryLevel) {
            $device = $this->devices->update($device, array_filter([
                'last_heartbeat_at' => now(), 'last_seen_at' => now(), 'battery_level' => $batteryLevel,
            ], static fn ($value) => $value !== null));
            $commands = $this->commands->pendingForDevice($device);
            $this->commands->markSent($commands);
            return [$device, $commands->each->refresh()];
        });
    }
}
