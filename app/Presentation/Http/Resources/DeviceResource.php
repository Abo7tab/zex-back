<?php

namespace App\Presentation\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class DeviceResource extends JsonResource
{
    public function toArray(Request $request): array { return ['id' => $this->id, 'device_uid' => $this->device_uid, 'device_name' => $this->device_name, 'model' => $this->model, 'os_version' => $this->os_version, 'battery_level' => $this->battery_level, 'last_seen_at' => $this->last_seen_at, 'is_screaming' => $this->is_screaming, 'is_tracking_continuous' => $this->is_tracking_continuous, 'is_locked' => $this->is_locked, 'is_stolen' => $this->is_stolen]; }
}
