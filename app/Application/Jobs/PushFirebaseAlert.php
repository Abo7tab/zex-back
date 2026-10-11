<?php

namespace App\Application\Jobs;

use App\Domain\Contracts\NotificationServiceInterface;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;

class PushFirebaseAlert implements ShouldQueue
{
    use Queueable;

    public int $tries = 2;
    public int $timeout = 20;

    public function __construct(
        private string $deviceUid,
        private array $alert
    ) {
        $this->onQueue('firebase');
    }

    public function handle(NotificationServiceInterface $firebase): void
    {
        $firebase->pushAlertRealtime($this->deviceUid, $this->alert);
    }
}
