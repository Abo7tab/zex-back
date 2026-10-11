<?php

namespace App\Application\Jobs;

use App\Domain\Contracts\NotificationServiceInterface;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;

class SyncFirebaseLastLocation implements ShouldQueue
{
    use Queueable;

    public int $tries = 2;
    public int $timeout = 20;

    public function __construct(
        private string $deviceUid,
        private array $location
    ) {
        $this->onQueue('firebase');
    }

    public function handle(NotificationServiceInterface $firebase): void
    {
        $firebase->syncLastLocation($this->deviceUid, $this->location);
    }
}
