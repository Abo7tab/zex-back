<?php

namespace App\Application\Command\Actions;

use App\Domain\Command\Enums\CommandType;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use App\Infrastructure\Firebase\FirebaseService;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Log;
use Symfony\Component\HttpKernel\Exception\HttpException;

class SetFoundModeAction
{
    public function __construct(
        private IssueDeviceCommandAction $commands,
        private FirebaseService $firebase
    ) {}

    public function execute(Owner $owner, Device $device, string $pin): Device
    {
        $storedPin = (string) $owner->pin_code;
        $valid = preg_match('/^\$2[aby]\$\d{2}\$/', $storedPin) === 1
            ? Hash::check($pin, $storedPin)
            : hash_equals($storedPin, $pin);
            
        if (! $valid) {
            throw new HttpException(403, 'Invalid PIN.');
        }
        
        if (! Hash::isHashed($storedPin)) {
            $owner->forceFill(['pin_code' => $pin])->save();
        }

        // DB update MUST happen FIRST
        $device->update([
            'is_stolen' => false,
            'is_screaming' => false,
            'is_tracking_continuous' => false,
            'is_searching' => false,
        ]);

        $command = $this->commands->execute($owner, $device, CommandType::FOUND_MODE, [], []);

        // Wrap ALL Firebase RTDB calls in try-catch
        try {
            $this->firebase->pushCommandRealtime($device->device_uid, $command->toArray());
            $this->firebase->syncDeviceStatus($device->device_uid, $device->only([
                'last_seen_at', 'last_heartbeat_at', 'battery_level', 'is_screaming', 'is_tracking_continuous', 'is_locked', 'is_stolen', 'is_searching'
            ]));
        } catch (\Throwable $e) {
            Log::warning('Firebase sync failed on found mode', ['error' => $e->getMessage()]);
        }

        return $device->refresh();
    }
}
