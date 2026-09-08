<?php

namespace Tests\Feature;

use App\Domain\Command\Enums\CommandStatus;
use App\Domain\Command\Enums\CommandType;
use App\Domain\Command\Models\Command;
use App\Domain\Device\Models\Device;
use App\Domain\Owner\Models\Owner;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Schema;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class ZexDeviceFlowTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        Schema::dropIfExists('commands');
        Schema::dropIfExists('devices');
        Schema::dropIfExists('owners');

        Schema::create('owners', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('email')->unique();
            $table->string('phone');
            $table->string('password');
            $table->string('pin_code', 255);
            $table->timestamps();
        });
        Schema::create('devices', function (Blueprint $table) {
            $table->id();
            $table->foreignId('owner_id');
            $table->string('device_uid')->unique();
            $table->string('device_name');
            $table->string('device_token_hash', 255)->nullable();
            $table->timestamp('last_seen_at')->nullable();
            $table->timestamp('last_heartbeat_at')->nullable();
            $table->tinyInteger('battery_level')->nullable();
            $table->boolean('is_screaming')->default(false);
            $table->boolean('is_tracking_continuous')->default(false);
            $table->boolean('is_locked')->default(false);
            $table->boolean('is_stolen')->default(false);
            $table->timestamps();
        });
        Schema::create('commands', function (Blueprint $table) {
            $table->id();
            $table->foreignId('device_id');
            $table->foreignId('owner_id');
            $table->string('type');
            $table->string('status');
            $table->json('parameters')->nullable();
            $table->json('response')->nullable();
            $table->timestamp('sent_at')->nullable();
            $table->timestamp('executed_at')->nullable();
            $table->timestamps();
        });
    }

    public function test_heartbeat_returns_pending_commands_and_marks_them_sent(): void
    {
        [$owner, $device, $token] = $this->device();
        $command = Command::create(['device_id' => $device->id, 'owner_id' => $owner->id, 'type' => CommandType::LOCATE, 'status' => CommandStatus::PENDING, 'parameters' => []]);

        $this->postJson('/api/devices/heartbeat', ['device_uid' => $device->device_uid, 'battery_level' => 81], ['X-Device-Token' => $token])
            ->assertOk()
            ->assertJsonPath('pending_commands.0.id', $command->id);

        $this->assertDatabaseHas('commands', ['id' => $command->id, 'status' => CommandStatus::SENT->value]);
        $this->assertDatabaseHas('devices', ['id' => $device->id, 'battery_level' => 81]);
    }

    public function test_found_accepts_a_legacy_pin_then_rehashes_it_and_clears_stolen_mode(): void
    {
        DB::table('owners')->insert(['name' => 'Owner', 'email' => 'owner@example.test', 'phone' => '01000000000', 'password' => Hash::make('secret-password'), 'pin_code' => '123456', 'created_at' => now(), 'updated_at' => now()]);
        $owner = Owner::where('email', 'owner@example.test')->firstOrFail();
        [, $device] = $this->device($owner, true);
        Sanctum::actingAs($owner);

        $this->postJson("/api/devices/{$device->id}/found", ['pin_code' => '123456'])->assertCreated();

        $this->assertDatabaseHas('devices', ['id' => $device->id, 'is_stolen' => false]);
        $this->assertTrue(Hash::check('123456', (string) $owner->fresh()->pin_code));
    }

    public function test_command_response_accepts_the_owning_device_token(): void
    {
        [$owner, $device, $token] = $this->device();
        $command = Command::create(['device_id' => $device->id, 'owner_id' => $owner->id, 'type' => CommandType::LOCATE, 'status' => CommandStatus::SENT, 'parameters' => []]);

        $this->postJson("/api/commands/{$command->id}/response", ['device_uid' => $device->device_uid, 'status' => CommandStatus::EXECUTED->value, 'response' => ['ok' => true]], ['X-Device-Token' => $token])
            ->assertOk();

        $this->assertDatabaseHas('commands', ['id' => $command->id, 'status' => CommandStatus::EXECUTED->value]);
    }

    private function device(?Owner $owner = null, bool $stolen = false): array
    {
        $owner ??= Owner::create(['name' => 'Owner', 'email' => 'owner'.uniqid().'@example.test', 'phone' => '01000000000', 'password' => 'secret-password', 'pin_code' => '123456']);
        $token = 'device-token';
        $device = Device::create(['owner_id' => $owner->id, 'device_uid' => 'uid-'.uniqid(), 'device_name' => 'Test Device', 'device_token_hash' => Hash::make($token), 'is_stolen' => $stolen]);
        return [$owner, $device, $token];
    }
}
