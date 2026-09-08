<?php

namespace App\Application\Device\Actions;

use App\Domain\Command\Models\Command;
use App\Domain\Device\Models\Device;
use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use App\Domain\Contracts\NotificationServiceInterface;
use Illuminate\Support\Facades\DB;

class StopSearchModeAction
{
    public function __construct(
        private DeviceRepositoryInterface $devices,
        private NotificationServiceInterface $firebase
    ) {}

    public function execute(Device $device): Device
    {
        $result = DB::transaction(function () use ($device) {
            $device = $this->devices->update($device, [
                'is_searching' => false,
            ]);

            Command::create([
                'device_id' => $device->id,
                'owner_id' => $device->owner_id,
                'type' => 'STOP_TRACKING',
                'status' => 'PENDING',
            ]);

            return $device;
        });

        try {
            $this->firebase->updateDeviceState($result->device_uid, $result->only([
                'last_seen_at', 'last_heartbeat_at', 'battery_level', 'is_screaming', 'is_tracking_continuous', 'is_locked', 'is_stolen', 'is_searching'
            ]));
        } catch (\Throwable $e) {
            \Illuminate\Support\Facades\Log::warning('Firebase sync failed', ['error' => $e->getMessage()]);
        }

        return $result;
    }
}
