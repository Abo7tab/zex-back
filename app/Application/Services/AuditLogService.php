<?php

namespace App\Application\Services;

use Illuminate\Support\Facades\DB;

class AuditLogService
{
    public static function log($ownerId, $deviceId, string $action, ?string $ipAddress = null, ?string $userAgent = null, array $details = []): void
    {
        DB::table('audit_logs')->insert([
            'owner_id' => $ownerId,
            'device_id' => $deviceId,
            'action' => $action,
            'details' => empty($details) ? null : json_encode($details),
            'ip_address' => $ipAddress,
            'user_agent' => $userAgent,
            'created_at' => now(),
            'updated_at' => now(),
        ]);
    }
}
