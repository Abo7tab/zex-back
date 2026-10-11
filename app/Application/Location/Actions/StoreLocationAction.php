<?php

namespace App\Application\Location\Actions;

use App\Application\Jobs\SyncFirebaseDeviceState;
use App\Application\Jobs\SyncFirebaseLastLocation;
use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Enums\CommandType;
use App\Domain\Command\Models\Command;
use App\Domain\Device\Models\Device;
use App\Domain\Location\Models\Location;
use App\Domain\Location\Repositories\LocationRepositoryInterface;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Schema;

class StoreLocationAction
{
    public function __construct(
        private LocationRepositoryInterface $locations,
        private \App\Domain\Contracts\NotificationServiceInterface $firebase
    ) {}

    public function execute(Device $device, array $data, bool $force = false): ?Location
    {
        $data = $data + ['recorded_at' => $data['recorded_at'] ?? now()];
        $this->cacheLatestLocation($device, $data);
        $this->syncLatestLocationForMap($device, $data, $force);
        $this->logLocationReceived($device, $data, $force);

        if (! $force && ! $this->shouldPersist($device)) {
            return null;
        }

        if (! $force && ! $this->reserveWriteSlot($device)) {
            return null;
        }

        $location = $this->locations->create($device, $data);
        
        $now = now();
        $device->update(['last_heartbeat_at' => $now]);

        $this->dispatchFirebaseJob(new SyncFirebaseDeviceState($device->device_uid, [
            'last_heartbeat_at' => $now->toIso8601String(),
        ]));

        return $location;
    }

    private function logLocationReceived(Device $device, array $data, bool $force): void
    {
        if (! isset($data['latitude'], $data['longitude'])) {
            return;
        }

        $latitude = (float) $data['latitude'];
        $longitude = (float) $data['longitude'];

        if ($latitude === 0.0 && $longitude === 0.0) {
            return;
        }

        $seconds = $force ? 5 : (int) env('LOCATION_RECEIVED_LOG_SECONDS', 20);
        if ($seconds > 0) {
            try {
                if (! Cache::add("devices:{$device->id}:location-received-log-slot", true, now()->addSeconds($seconds))) {
                    return;
                }
            } catch (\Throwable) {
                // Logging should never block location ingestion.
            }
        }

        $recordedAt = $data['recorded_at'] ?? now();
        if (! $recordedAt instanceof \DateTimeInterface) {
            $recordedAt = now();
        }

        \App\Application\Services\AuditLogService::log(
            $device->owner_id,
            $device->id,
            'LOCATION_RECEIVED',
            null,
            null,
            [
                'message' => 'The phone sent a fresh location update.',
                'severity' => 'info',
                'payload' => [
                    'lat' => $latitude,
                    'lng' => $longitude,
                    'accuracy' => isset($data['accuracy']) ? (float) $data['accuracy'] : null,
                    'provider' => $data['provider'] ?? null,
                    'battery_level' => $data['battery_level'] ?? null,
                    'recorded_at' => $recordedAt->format(\DateTimeInterface::ATOM),
                ],
            ]
        );
    }

    private function shouldPersist(Device $device): bool
    {
        if ($device->is_tracking_continuous || $device->is_searching || $device->is_stolen) {
            return true;
        }

        if (! Schema::hasTable('commands')) {
            return true;
        }

        return Command::query()
            ->where('device_id', $device->id)
            ->whereIn('type', [
                CommandType::LOCATE,
                CommandType::CONTINUOUS_TRACK,
                CommandType::STOLEN_MODE,
            ])
            ->whereIn('status', [
                CommandStatus::PENDING,
                CommandStatus::SENT,
                CommandStatus::EXECUTED,
            ])
            ->where(function ($query) {
                $query->where('created_at', '>=', now()->subMinutes(10))
                    ->orWhere('sent_at', '>=', now()->subMinutes(10))
                    ->orWhere('executed_at', '>=', now()->subMinutes(10));
            })
            ->exists();
    }

    private function reserveWriteSlot(Device $device): bool
    {
        $seconds = (int) env('LOCATION_MIN_WRITE_SECONDS', 15);
        if ($seconds <= 0) {
            return true;
        }

        try {
            return Cache::add("devices:{$device->id}:location-write-slot", true, now()->addSeconds($seconds));
        } catch (\Throwable) {
            return true;
        }
    }

    private function cacheLatestLocation(Device $device, array $data): void
    {
        $seconds = (int) env('LOCATION_CACHE_SECONDS', 5);
        if ($seconds > 0) {
            try {
                $reserved = Cache::add("devices:{$device->id}:location-cache-slot", true, now()->addSeconds($seconds));
                if (! $reserved) {
                    return;
                }
            } catch (\Throwable) {
                return;
            }
        }

        $recordedAt = $data['recorded_at'] ?? now();
        if (! $recordedAt instanceof \DateTimeInterface) {
            $recordedAt = now();
        }

        try {
            Cache::put("devices:{$device->id}:latest-location", [
                'latitude' => isset($data['latitude']) ? (float) $data['latitude'] : null,
                'longitude' => isset($data['longitude']) ? (float) $data['longitude'] : null,
                'accuracy' => isset($data['accuracy']) ? (float) $data['accuracy'] : null,
                'provider' => $data['provider'] ?? null,
                'battery_level' => $data['battery_level'] ?? null,
                'recorded_at' => $recordedAt->format(\DateTimeInterface::ATOM),
            ], now()->addMinutes(30));
        } catch (\Throwable) {
            // Location writes must keep working even if the cache backend is unavailable.
        }
    }

    private function syncLatestLocationForMap(Device $device, array $data, bool $force): void
    {
        if (! isset($data['latitude'], $data['longitude'])) {
            return;
        }

        $latitude = (float) $data['latitude'];
        $longitude = (float) $data['longitude'];

        if ($latitude === 0.0 && $longitude === 0.0) {
            return;
        }

        if (! $force && ! $this->reserveMapSyncSlot($device)) {
            return;
        }

        $recordedAt = $data['recorded_at'] ?? now();
        if (! $recordedAt instanceof \DateTimeInterface) {
            $recordedAt = now();
        }

        $this->dispatchFirebaseJob(new SyncFirebaseLastLocation($device->device_uid, [
            'device_id' => $device->id,
            'latitude' => $latitude,
            'longitude' => $longitude,
            'accuracy' => isset($data['accuracy']) ? (float) $data['accuracy'] : null,
            'speed' => isset($data['speed']) ? (float) $data['speed'] : null,
            'provider' => $data['provider'] ?? null,
            'battery_level' => $data['battery_level'] ?? null,
            'network_type' => $data['network_type'] ?? null,
            'recorded_at' => $recordedAt->format(\DateTimeInterface::ATOM),
        ]));
    }

    private function reserveMapSyncSlot(Device $device): bool
    {
        $seconds = (int) env('LOCATION_MAP_SYNC_SECONDS', 10);
        if ($seconds <= 0) {
            return true;
        }

        try {
            return Cache::add("devices:{$device->id}:location-map-sync-slot", true, now()->addSeconds($seconds));
        } catch (\Throwable) {
            return true;
        }
    }

    private function dispatchFirebaseJob(object $job): void
    {
        try {
            Bus::dispatch($job);
        } catch (\Throwable $e) {
            if (method_exists($job, 'handle')) {
                $job->handle($this->firebase);
            }
        }
    }
}
