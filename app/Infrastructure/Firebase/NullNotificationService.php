<?php

namespace App\Infrastructure\Firebase;

use App\Domain\Contracts\NotificationServiceInterface;

class NullNotificationService implements NotificationServiceInterface
{
    public function sendToDevice(?string $fcmToken, string $title, string $body, array $data = []): void {}

    public function updateDeviceState(string $deviceUid, array $state): void {}

    public function syncLastLocation(string $deviceUid, array $location): void {}

    public function pushCommandRealtime(string $deviceUid, array $command): void {}

    public function removeCommandRealtime(string $deviceUid, string|int $commandId): void {}

    public function pushAlertRealtime(string $deviceUid, array $alert): void {}

    public function deleteDeviceState(string $deviceUid): void {}
}
