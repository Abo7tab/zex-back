<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('devices', function (Blueprint $table) {
            if (! Schema::hasColumn('devices', 'device_name')) $table->string('device_name')->nullable();
            if (! Schema::hasColumn('devices', 'device_token_hash')) $table->string('device_token_hash')->nullable();
            if (! Schema::hasColumn('devices', 'last_seen_at')) $table->timestamp('last_seen_at')->nullable();
            if (! Schema::hasColumn('devices', 'battery_level')) $table->unsignedTinyInteger('battery_level')->nullable();
            foreach (['is_screaming', 'is_tracking_continuous', 'is_locked', 'is_stolen'] as $column) if (! Schema::hasColumn('devices', $column)) $table->boolean($column)->default(false);
        });
        Schema::table('locations', function (Blueprint $table) {
            if (! Schema::hasColumn('locations', 'provider')) $table->string('provider')->nullable();
            if (! Schema::hasColumn('locations', 'battery_level')) $table->unsignedTinyInteger('battery_level')->nullable();
            if (! Schema::hasColumn('locations', 'network_type')) $table->string('network_type')->nullable();
        });
    }

    public function down(): void
    {
        // Existing production tables are manually managed; this migration is intentionally non-destructive.
    }
};
