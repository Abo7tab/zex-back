<?php

namespace App\Presentation\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class CommandResource extends JsonResource
{
    public function toArray(Request $request): array { return ['id' => $this->id, 'device_id' => $this->device_id, 'type' => $this->type?->value, 'status' => $this->status?->value, 'parameters' => (object) ($this->parameters ?? []), 'response' => $this->response, 'sent_at' => $this->sent_at, 'executed_at' => $this->executed_at]; }
}
