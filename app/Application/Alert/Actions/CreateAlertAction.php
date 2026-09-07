<?php

namespace App\Application\Alert\Actions;

use App\Domain\Alert\Models\Alert;
use App\Domain\Alert\Repositories\AlertRepositoryInterface;
use App\Domain\Device\Models\Device;

class CreateAlertAction
{
    public function __construct(
        private AlertRepositoryInterface $alerts,
        private \App\Infrastructure\Firebase\FirebaseService $firebase
    ) {}
    public function execute(Device $device, array $data): Alert 
    { 
        $alert = $this->alerts->create($device, $data); 
        $this->firebase->pushAlertRealtime($device->device_uid, $alert->toArray());
        
        $fcmToken = $device->fcm_token ?? $device->device_token_hash;
        if ($fcmToken) {
            $this->firebase->sendFcmToDevice($fcmToken, 'New Alert', $data['type'] ?? 'Alert', $data);
        }

        return $alert;
    }
}
