<?php

namespace App\Application\Jobs;

use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

class WriteAuditLog implements ShouldQueue
{
    use Queueable;

    public int $tries = 1;
    public int $timeout = 10;

    public function __construct(
        private mixed $ownerId,
        private mixed $deviceId,
        private string $action,
        private ?string $ipAddress = null,
        private ?string $userAgent = null,
        private array $details = []
    ) {
        $this->onQueue('logs');
    }

    public function handle(): void
    {
        $now = now();
        $row = [
            'owner_id' => $this->ownerId,
            'device_id' => $this->deviceId,
            'action' => $this->action,
            'details' => empty($this->details) ? null : json_encode($this->details),
            'ip_address' => $this->ipAddress,
            'user_agent' => $this->userAgent,
            'created_at' => $now,
            'updated_at' => $now,
        ];

        if (Schema::hasColumn('audit_logs', 'expires_at')) {
            $row['expires_at'] = $now->copy()->addDays(3);
        }

        DB::table('audit_logs')->insert($row);
    }
}
