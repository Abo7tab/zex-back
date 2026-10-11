<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('jobs')) {
            Schema::create('jobs', function (Blueprint $table) {
                $table->id();
                $table->string('queue')->index();
                $table->longText('payload');
                $table->unsignedTinyInteger('attempts');
                $table->unsignedInteger('reserved_at')->nullable();
                $table->unsignedInteger('available_at');
                $table->unsignedInteger('created_at');
            });
        }

        if (! Schema::hasTable('failed_jobs')) {
            Schema::create('failed_jobs', function (Blueprint $table) {
                $table->id();
                $table->string('uuid')->unique();
                $table->text('connection');
                $table->text('queue');
                $table->longText('payload');
                $table->longText('exception');
                $table->timestamp('failed_at')->useCurrent();
            });
        }

        if (! Schema::hasTable('cache')) {
            Schema::create('cache', function (Blueprint $table) {
                $table->string('key')->primary();
                $table->mediumText('value');
                $table->integer('expiration');
            });
        }

        if (! Schema::hasTable('cache_locks')) {
            Schema::create('cache_locks', function (Blueprint $table) {
                $table->string('key')->primary();
                $table->string('owner');
                $table->integer('expiration');
            });
        }

        Schema::table('audit_logs', function (Blueprint $table) {
            if (! Schema::hasColumn('audit_logs', 'expires_at')) {
                $table->timestamp('expires_at')->nullable()->after('user_agent')->index();
            }

            if (! Schema::hasColumn('audit_logs', 'retention_extended_at')) {
                $table->timestamp('retention_extended_at')->nullable()->after('expires_at');
            }
        });

        if (DB::connection()->getDriverName() === 'mysql') {
            DB::table('audit_logs')
                ->whereNull('expires_at')
                ->update(['expires_at' => DB::raw("DATE_ADD(created_at, INTERVAL 3 DAY)")]);

            return;
        }

        DB::table('audit_logs')
            ->whereNull('expires_at')
            ->orderBy('id')
            ->select(['id', 'created_at'])
            ->chunkById(500, function ($logs) {
                foreach ($logs as $log) {
                    DB::table('audit_logs')
                        ->where('id', $log->id)
                        ->update(['expires_at' => \Carbon\Carbon::parse($log->created_at)->addDays(3)]);
                }
            });
    }

    public function down(): void
    {
        Schema::table('audit_logs', function (Blueprint $table) {
            if (Schema::hasColumn('audit_logs', 'retention_extended_at')) {
                $table->dropColumn('retention_extended_at');
            }

            if (Schema::hasColumn('audit_logs', 'expires_at')) {
                $table->dropColumn('expires_at');
            }
        });
    }
};
