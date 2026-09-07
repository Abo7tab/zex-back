<?php

namespace App\Presentation\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class DeviceResource extends JsonResource
{
    public function toArray(Request $request): array { return ['id' => $this->id, 'device_uid' => $this->device_uid, 'device_name' => $this->device_name, 'device_model' => $this->device_model ?? $this->model, 'android_version' => $this->android_version ?? $this->os_version, 'battery_level' => $this->battery_level, 'last_seen_at' => $this->last_seen_at, 'last_heartbeat_at' => $this->last_heartbeat_at, 'is_screaming' => (bool) ($this->is_screaming ?? false), 'is_tracking_continuous' => (bool) ($this->is_tracking_continuous ?? false), 'is_locked' => (bool) ($this->is_locked ?? false), 'is_stolen' => (bool) ($this->is_stolen ?? false)]; }
}
