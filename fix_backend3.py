import os

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f: f.write(content)

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f: return f.read()

# A1. RegisterDeviceAction.php
rda_path = r'C:\Users\moham\OneDrive\Desktop\z\app\Application\Device\Actions\RegisterDeviceAction.php'
rda = read_file(rda_path)
rda = rda.replace("$attributes['fcm_token']", "$data['fcm_token']")
write_file(rda_path, rda)

# A2. Migration
mig_dir = r'C:\Users\moham\OneDrive\Desktop\z\database\migrations'
for f in os.listdir(mig_dir):
    if 'add_alarm_secret_hash_to_devices_table' in f:
        mig_path = os.path.join(mig_dir, f)
        mig = read_file(mig_path)
        mig = mig.replace("$table->string('alarm_secret_hash')->nullable()->after('device_token_hash');", 
            "if (!Schema::hasColumn('devices', 'alarm_secret_hash')) { $table->string('alarm_secret_hash')->nullable()->after('device_token_hash'); }")
        write_file(mig_path, mig)

# A3. Namespace FIX
actions_dir = r'C:\Users\moham\OneDrive\Desktop\z\app\Application'
for root, dirs, files in os.walk(actions_dir):
    for f in files:
        if f.endswith('.php'):
            fpath = os.path.join(root, f)
            content = read_file(fpath)
            if 'use App\\Infrastructure\\Firebase\\NotificationServiceInterface;' in content:
                content = content.replace('use App\\Infrastructure\\Firebase\\NotificationServiceInterface;', 'use App\\Domain\\Contracts\\NotificationServiceInterface;')
                write_file(fpath, content)

# A4. FCM Persistence
# RegisterDeviceRequest
rdr_path = r'C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Requests\RegisterDeviceRequest.php'
rdr = read_file(rdr_path)
if 'fcm_token' not in rdr:
    rdr = rdr.replace("'sim_iccid' => 'nullable|string|max:50',", "'sim_iccid' => 'nullable|string|max:50',\n            'fcm_token' => 'nullable|string|max:255',")
    write_file(rdr_path, rdr)

# ProcessHeartbeatAction
pha_path = r'C:\Users\moham\OneDrive\Desktop\z\app\Application\Device\Actions\ProcessHeartbeatAction.php'
pha = read_file(pha_path)
if "if ($fcmToken !== null) $state['fcm_token'] = $fcmToken;" not in pha:
    pha = pha.replace("if ($batteryLevel !== null) $state['battery_level'] = $batteryLevel;", "if ($batteryLevel !== null) $state['battery_level'] = $batteryLevel;\n        if ($fcmToken !== null) $state['fcm_token'] = $fcmToken;")
write_file(pha_path, pha)

# DeviceController
dc_path = r'C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Controllers\Api\DeviceController.php'
dc = read_file(dc_path)
dc = dc.replace("$request->validated('fcm_token')", "$request->input('fcm_token')")
write_file(dc_path, dc)
