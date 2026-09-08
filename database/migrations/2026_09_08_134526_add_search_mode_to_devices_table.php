<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('devices', function (Blueprint $table) {
            if (!Schema::hasColumn('devices', 'is_searching')) {
                $table->boolean('is_searching')->default(false)->after('is_tracking_continuous');
            }
            if (!Schema::hasColumn('devices', 'searching_started_at')) {
                $table->timestamp('searching_started_at')->nullable()->after('is_searching');
            }
            if (!Schema::hasColumn('devices', 'search_interval_seconds')) {
                $table->integer('search_interval_seconds')->default(30)->after('searching_started_at');
            }
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('devices', function (Blueprint $table) {
            $table->dropColumn(['is_searching', 'searching_started_at', 'search_interval_seconds']);
        });
    }
};
