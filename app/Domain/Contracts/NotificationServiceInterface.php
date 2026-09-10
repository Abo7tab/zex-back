<?php
namespace App\Domain\Contracts;

interface NotificationServiceInterface
{
    public function sendToDevice(string $fcmToken, string $title, string $body, array $data = []): void;
    public function updateDeviceState(string $deviceUid, array $state): void;
    public function pushCommandRealtime(string $deviceUid, array $command): void;
    public function deleteDeviceState(string $deviceUid): void;
}
