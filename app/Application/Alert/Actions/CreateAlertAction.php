<?php

namespace App\Application\Alert\Actions;

use App\Application\Jobs\PushFirebaseAlert;
use App\Application\Jobs\SendFirebaseDeviceNotification;
use App\Domain\Alert\Models\Alert;
use App\Domain\Alert\Repositories\AlertRepositoryInterface;
use App\Domain\Device\Models\Device;
use Illuminate\Support\Facades\Bus;

class CreateAlertAction
{
    public function __construct(
        private AlertRepositoryInterface $alerts,
        private \App\Domain\Contracts\NotificationServiceInterface $firebase
    ) {}
    public function execute(Device $device, array $data): Alert 
    { 
        $alert = $this->alerts->create($device, $data); 
        $this->dispatchFirebaseJob(new PushFirebaseAlert($device->device_uid, $alert->toArray()));
        
        $fcmToken = $device->fcm_token ?? $device->device_token_hash;
        if ($fcmToken) {
            $this->dispatchFirebaseJob(new SendFirebaseDeviceNotification($fcmToken, 'New Alert', $data['type'] ?? 'Alert', $data));
        }

        return $alert;
    }

    private function dispatchFirebaseJob(object $job): void
    {
        try {
            Bus::dispatch($job);
        } catch (\Throwable $e) {
            if (method_exists($job, 'handle')) {
                $job->handle($this->firebase);
            }
        }
    }
}
