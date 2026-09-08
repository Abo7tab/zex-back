<?php

namespace App\Application\Device\Actions;

use App\Domain\Command\Repositories\CommandRepositoryInterface;
use App\Domain\Device\Models\Device;
use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

class ProcessHeartbeatAction
{
    public function __construct(
        private DeviceRepositoryInterface $devices, 
        private CommandRepositoryInterface $commands,
        private \App\Infrastructure\Firebase\NotificationServiceInterface $firebase
    ) {}

    public function execute(Device $device, ?int $batteryLevel): array
    {
        return DB::transaction(function () use ($device, $batteryLevel) {
            $updates = [];
            if (Schema::hasColumn('devices', 'last_seen_at')) $updates['last_seen_at'] = now();
            if (Schema::hasColumn('devices', 'last_heartbeat_at')) $updates['last_heartbeat_at'] = now();
            if ($batteryLevel !== null && Schema::hasColumn('devices', 'battery_level')) $updates['battery_level'] = $batteryLevel;
            $device = $this->devices->update($device, $updates);
            
            $this->firebase->updateDeviceState($device->device_uid, $device->only([
                'last_seen_at', 'last_heartbeat_at', 'battery_level', 'is_screaming', 'is_tracking_continuous', 'is_locked', 'is_stolen'
            ]));

            $commands = $this->commands->pendingForDevice($device);
            $this->commands->markSent($commands);
            return [$device, $commands->each->refresh()];
        });
    }
}
