<?php

namespace App\Domain\Command\Models;

use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Enums\CommandType;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Command extends Model
{
    protected $fillable = [
        'device_id',
        'owner_id',
        'type',
        'status',
        'parameters',
        'response',
        'sent_at',
        'executed_at',
    ];

    protected function casts(): array
    {
        return [
            'type' => CommandType::class,
            'status' => CommandStatus::class,
            'parameters' => 'array',
            'response' => 'array',
            'sent_at' => 'datetime',
            'executed_at' => 'datetime',
        ];
    }

    public function device(): BelongsTo
    {
        return $this->belongsTo(Device::class);
    }

    public function owner(): BelongsTo
    {
        return $this->belongsTo(Owner::class);
    }
}
