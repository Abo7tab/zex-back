<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('devices', function (Blueprint $table) {
            $table->string('alarm_secret_hash')->nullable()->after('device_token_hash');
            if (!Schema::hasColumn('devices', 'fcm_token')) {
                $table->string('fcm_token')->nullable()->after('device_token_hash');
            }
        });
    }

    public function down(): void
    {
        Schema::table('devices', function (Blueprint $table) {
            $table->dropColumn(['alarm_secret_hash', 'fcm_token']);
        });
    }
};
