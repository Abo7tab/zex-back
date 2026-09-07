<?php

namespace App\Application\Command\Actions;

use App\Domain\Command\Enums\CommandType;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;

class SendCommandAction
{
    public function __construct(
        private IssueDeviceCommandAction $commands,
        private \App\Infrastructure\Firebase\FirebaseService $firebase
    ) {}
    public function execute(Owner $owner, Device $device, CommandType $type, array $parameters = []) 
    { 
        $command = $this->commands->execute($owner, $device, $type, $parameters); 
        $this->firebase->pushCommandRealtime($device->device_uid, $command->toArray());
        $fcmToken = $device->fcm_token ?? $device->device_token_hash;
        if ($fcmToken) {
            $this->firebase->sendFcmToDevice($fcmToken, 'New Command', "Command: {$type->value}", $parameters);
        }
        return $command;
    }
}
