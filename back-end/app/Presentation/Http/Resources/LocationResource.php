<?php

namespace App\Presentation\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class LocationResource extends JsonResource
{
    public function toArray(Request $request): array { return ['id' => $this->id, 'latitude' => $this->latitude, 'longitude' => $this->longitude, 'accuracy' => $this->accuracy, 'speed' => $this->speed, 'provider' => $this->provider, 'battery_level' => $this->battery_level, 'network_type' => $this->network_type, 'recorded_at' => $this->recorded_at]; }
}
