<?php

namespace App\Application\Jobs;

use App\Domain\Contracts\NotificationServiceInterface;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;

class SendFirebaseDeviceNotification implements ShouldQueue
{
    use Queueable;

    public int $tries = 2;
    public int $timeout = 20;

    public function __construct(
        private string $fcmToken,
        private string $title,
        private string $body,
        private array $data = []
    ) {
        $this->onQueue('firebase');
    }

    public function handle(NotificationServiceInterface $firebase): void
    {
        $firebase->sendToDevice($this->fcmToken, $this->title, $this->body, $this->data);
    }
}
