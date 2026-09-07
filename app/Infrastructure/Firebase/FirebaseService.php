<?php

namespace App\Infrastructure\Firebase;

use Kreait\Firebase\Contract\Database;
use Kreait\Firebase\Contract\Messaging;
use Kreait\Firebase\Messaging\CloudMessage;
use Kreait\Firebase\Messaging\Notification;
use Exception;
use Illuminate\Support\Facades\Log;

class FirebaseService
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
        } catch (Exception $e) {
            Log::error('Firebase syncLastLocation failed: ' . $e->getMessage());
        }
    }

    public function syncDeviceStatus(string $deviceUid, array $status): void
    {
        try {
            $this->database->getReference("devices/{$deviceUid}/status")
                ->update($status);
        } catch (Exception $e) {
            Log::error('Firebase syncDeviceStatus failed: ' . $e->getMessage());
        }
    }

    public function pushCommandRealtime(string $deviceUid, array $command): void
    {
        try {
            $this->database->getReference("devices/{$deviceUid}/pending_commands/{$command['id']}")
                ->set($command);
        } catch (Exception $e) {
            Log::error('Firebase pushCommandRealtime failed: ' . $e->getMessage());
        }
    }

    public function removeCommandRealtime(string $deviceUid, string|int $commandId): void
    {
        try {
            $this->database->getReference("devices/{$deviceUid}/pending_commands/{$commandId}")
                ->remove();
        } catch (Exception $e) {
            Log::error('Firebase removeCommandRealtime failed: ' . $e->getMessage());
        }
    }

    public function pushAlertRealtime(string $deviceUid, array $alert): void
    {
        try {
            $this->database->getReference("devices/{$deviceUid}/alerts/{$alert['id']}")
                ->set($alert);
        } catch (Exception $e) {
            Log::error('Firebase pushAlertRealtime failed: ' . $e->getMessage());
        }
    }

    public function sendFcmToDevice(?string $fcmToken, string $title, string $body, array $data = []): void
    {
        if (!$fcmToken) {
            return;
        }

        try {
            $message = CloudMessage::withTarget('token', $fcmToken)
                ->withNotification(Notification::create($title, $body))
                ->withData($data);

            $this->messaging->send($message);
        } catch (Exception $e) {
            Log::error('Firebase sendFcmToDevice failed: ' . $e->getMessage());
        }
    }
}
