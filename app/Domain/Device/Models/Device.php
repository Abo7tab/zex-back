<?php

namespace App\Domain\Device\Models;

use App\Domain\Alert\Models\Alert;
use App\Domain\Command\Models\Command;
use App\Domain\Location\Models\Location;
use App\Domain\Owner\Models\Owner;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\HasOne;

class Device extends Model
{
    protected $hidden = ['device_token_hash'];

    protected $fillable = [
        'owner_id',
        'device_uid',
        'device_name',
        'device_model',
        'android_version',
        'last_heartbeat_at',
        'last_seen_at',
        'battery_level',
        'is_screaming',
        'is_tracking_continuous',
        'is_locked',
        'is_stolen',
        'is_searching',
        'searching_started_at',
        'search_interval_seconds',
        'device_token_hash',
        'alarm_secret_hash',
        'fcm_token',
    ];

    protected function casts(): array
    {
        return [
            'last_heartbeat_at' => 'datetime',
            'last_seen_at' => 'datetime',
            'searching_started_at' => 'datetime',
            'battery_level' => 'integer',
            'search_interval_seconds' => 'integer',
            'is_screaming' => 'boolean',
            'is_tracking_continuous' => 'boolean',
            'is_locked' => 'boolean',
            'is_stolen' => 'boolean',
            'is_searching' => 'boolean',
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

    public function lastLocation(): HasOne
    {
        return $this->hasOne(Location::class)->latestOfMany('recorded_at');
    }

    public function scopeActive($query)
    {
        return $query->whereNotNull('last_seen_at');
    }

    public function scopeOwnedBy($query, int $ownerId)
    {
        return $query->where('owner_id', $ownerId);
    }
}
