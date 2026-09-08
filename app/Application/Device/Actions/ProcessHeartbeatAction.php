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
        private \App\Domain\Contracts\NotificationServiceInterface $firebase
    ) {}

    public function execute(Device $device, ?int $batteryLevel = null, ?string $fcmToken = null): array
    {
        $result = DB::transaction(function () use ($device, $batteryLevel, $fcmToken) {
            $updates = [];
            if (Schema::hasColumn('devices', 'last_seen_at')) $updates['last_seen_at'] = now();
            if (Schema::hasColumn('devices', 'last_heartbeat_at')) $updates['last_heartbeat_at'] = now();
            if ($batteryLevel !== null && Schema::hasColumn('devices', 'battery_level')) $updates['battery_level'] = $batteryLevel;
            if ($fcmToken !== null && Schema::hasColumn('devices', 'fcm_token')) $updates['fcm_token'] = $fcmToken;
            $device = $this->devices->update($device, $updates);

            $commands = $this->commands->pendingForDevice($device);
            $this->commands->markSent($commands);
            return [$device, $commands->each->refresh()];
        });

        try {
            $this->firebase->updateDeviceState($result[0]->device_uid, $result[0]->only([
                'last_seen_at', 'last_heartbeat_at', 'battery_level', 'is_screaming', 'is_tracking_continuous', 'is_locked', 'is_stolen', 'is_searching'
            ]));
        } catch (\Throwable $e) {
            \Illuminate\Support\Facades\Log::warning('Firebase sync failed', ['error' => $e->getMessage()]);
        }

        return $result;
    }
}
