<?php

namespace App\Application\Command\Actions;

use App\Domain\Command\Enums\CommandType;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;

class SendCommandAction
{
    public function __construct(
        private IssueDeviceCommandAction $commands,
        private \App\Domain\Contracts\NotificationServiceInterface $firebase
    ) {}
    public function execute(Owner $owner, Device $device, CommandType $type, array $parameters = []) 
    { 
        $command = $this->commands->execute($owner, $device, $type, $parameters); 
        $this->firebase->pushCommandRealtime($device->device_uid, $command->toArray());
        $fcmToken = $device->fcm_token;
        if ($fcmToken) {
            $this->firebase->sendToDevice($fcmToken, 'New Command', "Command: {$type->value}", $parameters);
        }
        return $command;
    }
}
