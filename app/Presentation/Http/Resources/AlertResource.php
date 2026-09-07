<?php

namespace App\Presentation\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class AlertResource extends JsonResource
{
    public function toArray(Request $request): array { return ['id' => $this->id, 'device_id' => $this->device_id, 'type' => $this->type, 'message' => $this->message, 'is_read' => $this->is_read, 'created_at' => $this->created_at]; }
}
