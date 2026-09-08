import os
import re

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def append_to_migration():
    mig_dir = r"C:\Users\moham\OneDrive\Desktop\z\database\migrations"
    for f in os.listdir(mig_dir):
        if "add_alarm_secret_hash_to_devices_table" in f:
            mig_path = os.path.join(mig_dir, f)
            content = """<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('devices', function (Blueprint $table) {
            $table->string('alarm_secret_hash')->nullable()->after('device_token_hash');
            if (!Schema::hasColumn('devices', 'fcm_token')) {
                $table->string('fcm_token')->nullable()->after('device_token_hash');
            }
        });
    }

    public function down(): void
    {
        Schema::table('devices', function (Blueprint $table) {
            $table->dropColumn(['alarm_secret_hash', 'fcm_token']);
        });
    }
};
"""
            write_file(mig_path, content)

append_to_migration()

# A5. NotificationServiceInterface
os.makedirs(r"C:\Users\moham\OneDrive\Desktop\z\app\Domain\Contracts", exist_ok=True)
write_file(r"C:\Users\moham\OneDrive\Desktop\z\app\Domain\Contracts\NotificationServiceInterface.php", """<?php
namespace App\Domain\Contracts;

interface NotificationServiceInterface
{
    public function sendToDevice(string $fcmToken, string $title, string $body, array $data = []): void;
    public function updateDeviceState(string $deviceUid, array $state): void;
    public function pushCommandRealtime(string $deviceUid, array $command): void;
}
""")

# Fix FirebaseService to implement interface
fb_service = r"C:\Users\moham\OneDrive\Desktop\z\app\Infrastructure\Firebase\FirebaseService.php"
with open(fb_service, 'r', encoding='utf-8') as f:
    fb_data = f.read()
fb_data = fb_data.replace('class FirebaseService', 'use App\\Domain\\Contracts\\NotificationServiceInterface;\n\nclass FirebaseService implements NotificationServiceInterface')
fb_data = fb_data.replace('public function syncDeviceStatus', 'public function updateDeviceState')
fb_data = fb_data.replace('public function sendFcmToDevice', 'public function sendToDevice')
write_file(fb_service, fb_data)

# AppServiceProvider binding
sp_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Providers\AppServiceProvider.php"
with open(sp_path, 'r', encoding='utf-8') as f:
    sp_data = f.read()
if 'NotificationServiceInterface' not in sp_data:
    sp_data = sp_data.replace('public function register(): void', 'public function register(): void\n    {\n        $this->app->singleton(\\App\\Domain\\Contracts\\NotificationServiceInterface::class, \\App\\Infrastructure\\Firebase\\FirebaseService::class);')
    write_file(sp_path, sp_data)

