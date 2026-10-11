<?php

namespace App\Application\Jobs;

use App\Domain\Contracts\NotificationServiceInterface;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;

class RemoveFirebaseCommand implements ShouldQueue
{
    use Queueable;

    public int $tries = 2;
    public int $timeout = 20;

    public function __construct(
        private string $deviceUid,
        private int|string $commandId
    ) {
        $this->onQueue('firebase');
    }

    public function handle(NotificationServiceInterface $firebase): void
    {
        $firebase->removeCommandRealtime($this->deviceUid, $this->commandId);
    }
}
