<?php

namespace App\Application\Services;

use App\Application\Jobs\WriteAuditLog;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\DB;

class AuditLogService
{
    public static function log($ownerId, $deviceId, string $action, ?string $ipAddress = null, ?string $userAgent = null, array $details = []): void
    {
        try {
            Bus::dispatch(new WriteAuditLog($ownerId, $deviceId, $action, $ipAddress, $userAgent, $details));
        } catch (\Throwable $e) {
            self::writeNow($ownerId, $deviceId, $action, $ipAddress, $userAgent, $details);
        }
    }

    public static function writeNow($ownerId, $deviceId, string $action, ?string $ipAddress = null, ?string $userAgent = null, array $details = []): void
    {
        try {
            $now = now();
            $row = [
                'owner_id' => $ownerId,
                'device_id' => $deviceId,
                'action' => $action,
                'details' => empty($details) ? null : json_encode($details),
                'ip_address' => $ipAddress,
                'user_agent' => $userAgent,
                'created_at' => $now,
                'updated_at' => $now,
            ];

            if (\Illuminate\Support\Facades\Schema::hasColumn('audit_logs', 'expires_at')) {
                $row['expires_at'] = $now->copy()->addDays(3);
            }

            DB::table('audit_logs')->insert($row);
        } catch (\Throwable $e) {
            \Illuminate\Support\Facades\Log::error("Failed to write audit log: " . $e->getMessage());
        }
    }
}
