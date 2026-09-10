<?php

namespace App\Infrastructure\Firebase;

use Kreait\Firebase\Contract\Database;
use Kreait\Firebase\Contract\Messaging;
use Kreait\Firebase\Messaging\CloudMessage;
use Kreait\Firebase\Messaging\Notification;
use Throwable;
use Illuminate\Support\Facades\Log;

use App\Domain\Contracts\NotificationServiceInterface;

class FirebaseService implements NotificationServiceInterface
{
    public function __construct(
        private Database $database,
        private Messaging $messaging
    ) {}

    public function syncLastLocation(string $deviceUid, array $location): void
    {
        try {
            $this->database->getReference("devices/{$deviceUid}/last_location")
                ->set($location);
        } catch (Throwable $e) {
            Log::warning('Firebase syncLastLocation failed: ' . $e->getMessage());
        }
    }

    public function updateDeviceState(string $deviceUid, array $status): void
    {
        try {
            $this->database->getReference("devices/{$deviceUid}/status")
                ->update($status);
        } catch (Throwable $e) {
            Log::warning('Firebase syncDeviceStatus failed: ' . $e->getMessage());
        }
    }

    public function deleteDeviceState(string $deviceUid): void
    {
        try {
            $this->database->getReference("devices/{$deviceUid}")->remove();
        } catch (Throwable $e) {
            Log::warning('Firebase deleteDeviceState failed: ' . $e->getMessage());
        }
    }

    public function pushCommandRealtime(string $deviceUid, array $command): void
    {
        try {
            $this->database->getReference("devices/{$deviceUid}/pending_commands/{$command['id']}")
                ->set($command);
        } catch (Throwable $e) {
            Log::warning('Firebase pushCommandRealtime failed: ' . $e->getMessage());
        }
    }

    public function removeCommandRealtime(string $deviceUid, string|int $commandId): void
    {
        try {
            $this->database->getReference("devices/{$deviceUid}/pending_commands/{$commandId}")
                ->remove();
        } catch (Throwable $e) {
            Log::warning('Firebase removeCommandRealtime failed: ' . $e->getMessage());
        }
    }

    public function pushAlertRealtime(string $deviceUid, array $alert): void
    {
        try {
            $this->database->getReference("devices/{$deviceUid}/alerts/{$alert['id']}")
                ->set($alert);
        } catch (Throwable $e) {
            Log::warning('Firebase pushAlertRealtime failed: ' . $e->getMessage());
        }
    }

    public function sendToDevice(?string $fcmToken, string $title, string $body, array $data = []): void
    {
        if (!$fcmToken) {
            return;
        }

        try {
            $config = \Kreait\Firebase\Messaging\AndroidConfig::fromArray([
                'priority' => 'high',
                'ttl' => '3600s',
            ]);

            $message = CloudMessage::withTarget('token', $fcmToken)
                ->withData($data)
                ->withAndroidConfig($config);

            $this->messaging->send($message);
        } catch (Throwable $e) {
            Log::warning('Firebase sendFcmToDevice failed: ' . $e->getMessage());
        }
    }
}
