<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schedule;

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote')->hourly();

Artisan::command('audit-logs:prune-expired', function () {
    $deleted = DB::table('audit_logs')
        ->whereNotNull('expires_at')
        ->where('expires_at', '<=', now())
        ->delete();

    $this->info("Deleted {$deleted} expired audit logs.");
})->purpose('Delete phone activity logs after their retention window.');

Schedule::command('audit-logs:prune-expired')->dailyAt('02:00')->withoutOverlapping();
Schedule::command('queue:work --queue=firebase,logs,default --stop-when-empty --max-jobs=25 --tries=2 --sleep=1')->everyMinute()->withoutOverlapping();
