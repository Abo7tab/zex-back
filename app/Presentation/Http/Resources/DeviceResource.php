<?php

namespace App\Presentation\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Schema;

class DeviceResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        $lastLocation = Schema::hasTable('locations') ? $this->lastLocation : null;
        $cachedLocation = Cache::get("devices:{$this->id}:latest-location");

        return [
            'id' => $this->id,
            'device_uid' => $this->device_uid,
            'device_name' => $this->device_name,
            'device_model' => $this->device_model ?? $this->model,
            'android_version' => $this->android_version ?? $this->os_version,
            'battery_level' => $this->battery_level,
            'last_seen_at' => $this->last_seen_at,
            'last_heartbeat_at' => $this->last_heartbeat_at,
            'last_location' => $this->formatLastLocation($lastLocation, is_array($cachedLocation) ? $cachedLocation : null),
            'is_screaming' => (bool) ($this->is_screaming ?? false),
            'is_tracking_continuous' => (bool) ($this->is_tracking_continuous ?? false),
            'is_locked' => (bool) ($this->is_locked ?? false),
            'is_stolen' => (bool) ($this->is_stolen ?? false),
            'is_searching' => (bool) ($this->is_searching ?? false),
            'is_power_saver' => (bool) ($this->is_power_saver ?? false),
            'searching_started_at' => $this->searching_started_at,
            'search_interval_seconds' => $this->search_interval_seconds,
            'alarm_secret' => $this->when(isset($this->alarm_secret_plain), $this->alarm_secret_plain),
        ];
    }

    private function formatLastLocation($lastLocation, ?array $cachedLocation): ?array
    {
        if ($cachedLocation && isset($cachedLocation['latitude'], $cachedLocation['longitude'])) {
            return [
                'latitude' => (float) $cachedLocation['latitude'],
                'longitude' => (float) $cachedLocation['longitude'],
                'accuracy' => isset($cachedLocation['accuracy']) ? (float) $cachedLocation['accuracy'] : null,
                'provider' => $cachedLocation['provider'] ?? null,
                'battery_level' => $cachedLocation['battery_level'] ?? null,
                'recorded_at' => $cachedLocation['recorded_at'] ?? null,
            ];
        }

        if (! $lastLocation) {
            return null;
        }

        return [
            'id' => $lastLocation->id,
            'latitude' => (float) $lastLocation->latitude,
            'longitude' => (float) $lastLocation->longitude,
            'accuracy' => $lastLocation->accuracy !== null ? (float) $lastLocation->accuracy : null,
            'speed' => $lastLocation->speed !== null ? (float) $lastLocation->speed : null,
            'provider' => $lastLocation->provider,
            'battery_level' => $lastLocation->battery_level,
            'network_type' => $lastLocation->network_type,
            'recorded_at' => optional($lastLocation->recorded_at)->toIso8601String(),
        ];
    }
}
