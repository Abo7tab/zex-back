<?php

namespace App\Infrastructure\Persistence\Eloquent;

use App\Application\Services\AuditLogService;
use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Models\Command;
use App\Domain\Command\Repositories\CommandRepositoryInterface;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Support\Collection;

class EloquentCommandRepository implements CommandRepositoryInterface
{
    public function create(Device $device, Owner $owner, array $attributes): Command { return $device->commands()->create($attributes + ['owner_id' => $owner->id]); }
    public function pendingForDevice(Device $device): Collection
    {
        $timeoutSeconds = max(30, (int) env('COMMAND_IN_FLIGHT_SECONDS', 120));
        $expiredCommands = $device->commands()
            ->where('status', CommandStatus::SENT)
            ->where('sent_at', '<', now()->subSeconds($timeoutSeconds))
            ->get();

        foreach ($expiredCommands as $command) {
            $command->update([
                'status' => CommandStatus::FAILED,
                'response' => [
                    'error' => "No device response within {$timeoutSeconds} seconds.",
                    'timeout_seconds' => $timeoutSeconds,
                ],
            ]);

            AuditLogService::log(
                $device->owner_id,
                $device->id,
                'COMMAND_TIMEOUT',
                null,
                null,
                [
                    'command_id' => $command->id,
                    'command_type' => $command->type?->value,
                    'status' => CommandStatus::FAILED->value,
                    'timeout_seconds' => $timeoutSeconds,
                    'message' => 'No response received from the phone before timeout.',
                ]
            );
        }

        $hasInFlightCommand = $device->commands()
            ->where('status', CommandStatus::SENT)
            ->where('sent_at', '>=', now()->subSeconds($timeoutSeconds))
            ->exists();

        if ($hasInFlightCommand) {
            return collect();
        }

        return $device->commands()
            ->where('status', CommandStatus::PENDING)
            ->orderBy('id')
            ->limit(1)
            ->get();
    }

    public function markSent(Collection $commands): void { Command::whereKey($commands->modelKeys())->where('status', CommandStatus::PENDING)->update(['status' => CommandStatus::SENT, 'sent_at' => now()]); }
    public function update(Command $command, array $attributes): Command { $command->update($attributes); return $command->refresh(); }
}
