<?php

namespace App\Application\Device\Actions;

use App\Domain\Command\Models\Command;
use App\Domain\Device\Models\Device;
use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use App\Infrastructure\Firebase\FirebaseService;
use Illuminate\Support\Facades\DB;

class SetSearchModeAction
{
    public function __construct(
        private DeviceRepositoryInterface $devices,
        private FirebaseService $firebase
    ) {}

    public function execute(Device $device, array $data): Device
    {
        return DB::transaction(function () use ($device, $data) {
            $updates = [
                'is_searching' => true,
                'searching_started_at' => now(),
            ];
            
            if (isset($data['interval_seconds'])) {
                $updates['search_interval_seconds'] = $data['interval_seconds'];
            }

            $device = $this->devices->update($device, $updates);

            // Optionally create CONTINUOUS_TRACK and ENABLE_NET
            // For now, simply dispatch them if needed
            Command::create([
                'device_id' => $device->id,
                'owner_id' => $device->owner_id,
                'type' => 'CONTINUOUS_TRACK',
                'parameters' => ['interval' => ($data['interval_seconds'] ?? 30) * 1000],
                'status' => 'PENDING',
            ]);

            Command::create([
                'device_id' => $device->id,
                'owner_id' => $device->owner_id,
                'type' => 'ENABLE_NET',
                'status' => 'PENDING',
            ]);

            $this->firebase->syncDeviceStatus($device->device_uid, $device->only([
                'last_seen_at', 'last_heartbeat_at', 'battery_level', 'is_screaming', 'is_tracking_continuous', 'is_locked', 'is_stolen', 'is_searching'
            ]));

            return $device;
        });
    }
}
