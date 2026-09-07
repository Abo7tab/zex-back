<?php

namespace App\Domain\Device\Models;

use App\Domain\Alert\Models\Alert;
use App\Domain\Command\Models\Command;
use App\Domain\Location\Models\Location;
use App\Domain\Owner\Models\Owner;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Device extends Model
{
    protected $fillable = [
        'owner_id',
        'device_uid',
        'name',
        'model',
        'os_version',
        'last_heartbeat_at',
    ];

    protected function casts(): array
    {
        return [
            'last_heartbeat_at' => 'datetime',
        ];
    }

    public function owner(): BelongsTo
    {
        return $this->belongsTo(Owner::class);
    }

    public function locations(): HasMany
    {
        return $this->hasMany(Location::class);
    }

    public function commands(): HasMany
    {
        return $this->hasMany(Command::class);
    }

    public function alerts(): HasMany
    {
        return $this->hasMany(Alert::class);
    }
}
