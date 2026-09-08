<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('devices', function (Blueprint $table) {
            if (! Schema::hasColumn('devices', 'device_token_hash')) $table->string('device_token_hash', 255)->nullable();
            if (! Schema::hasColumn('devices', 'device_model')) $table->string('device_model')->nullable();
            if (! Schema::hasColumn('devices', 'android_version')) $table->string('android_version')->nullable();
            if (! Schema::hasColumn('devices', 'last_seen_at')) $table->timestamp('last_seen_at')->nullable();
            if (! Schema::hasColumn('devices', 'last_heartbeat_at')) $table->timestamp('last_heartbeat_at')->nullable();
            if (! Schema::hasColumn('devices', 'battery_level')) $table->tinyInteger('battery_level')->nullable();
        });

        Schema::table('owners', function (Blueprint $table) {
            if (Schema::hasColumn('owners', 'pin_code')) $table->string('pin_code', 255)->change();
            else $table->string('pin_code', 255);
        });
    }

    public function down(): void
    {
        // Production tables are manually managed; rolling this back must not destroy live data.
    }
};
