<?php

namespace App\Application\Services;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

class AuditLogService
{
    private static ?bool $hasExpiresAt = null;

    public static function log($ownerId, $deviceId, string $action, ?string $ipAddress = null, ?string $userAgent = null, array $details = []): void
    {
        self::writeNow($ownerId, $deviceId, $action, $ipAddress, $userAgent, $details);
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

            self::$hasExpiresAt ??= \Illuminate\Support\Facades\Cache::remember('schema:audit_logs:has_expires_at', now()->addDay(), function () {
                return Schema::hasColumn('audit_logs', 'expires_at');
            });

            if (self::$hasExpiresAt) {
                $row['expires_at'] = $now->copy()->addDays(3);
            }

            DB::table('audit_logs')->insert($row);

            if ($ownerId) {
                \Illuminate\Support\Facades\Cache::forget("user:{$ownerId}:audit_logs_response");
            }
        } catch (\Throwable $e) {
            \Illuminate\Support\Facades\Log::error("Failed to write audit log: " . $e->getMessage());
        }
    }
}
