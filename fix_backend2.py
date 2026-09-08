import os
import re

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# Update Actions to use NotificationServiceInterface
def update_action_deps(path):
    if not os.path.exists(path): return
    with open(path, 'r', encoding='utf-8') as f:
        data = f.read()
    data = data.replace('use App\\Infrastructure\\Firebase\\FirebaseService;', 'use App\\Domain\\Contracts\\NotificationServiceInterface;')
    data = data.replace('FirebaseService $firebase', 'NotificationServiceInterface $firebase')
    data = data.replace('->syncDeviceStatus(', '->updateDeviceState(')
    data = data.replace('->sendFcmToDevice(', '->sendToDevice(')
    write_file(path, data)

actions_to_update = [
    r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Device\Actions\StopSearchModeAction.php",
    r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Device\Actions\SetSearchModeAction.php",
    r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Device\Actions\ProcessHeartbeatAction.php",
    r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Command\Actions\SendCommandAction.php",
    r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Command\Actions\ProcessCommandResponseAction.php",
    r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Command\Actions\SetFoundModeAction.php",
    r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Alert\Actions\CreateAlertAction.php",
    r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Location\Actions\StoreLocationAction.php"
]
for p in actions_to_update:
    update_action_deps(p)

# A1 & A4. RegisterDeviceAction
rda_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Device\Actions\RegisterDeviceAction.php"
with open(rda_path, 'r', encoding='utf-8') as f:
    rda_data = f.read()

# Add alarm_secret logic
rda_data = rda_data.replace("return [$device, $token];", """
        $alarmSecret = (string) random_int(100000, 999999);
        $device->alarm_secret_hash = \\Illuminate\\Support\\Facades\\Hash::make($alarmSecret);
        if (isset($attributes['fcm_token'])) {
            $device->fcm_token = $attributes['fcm_token'];
        }
        $device->save();
        $device->alarm_secret_plain = $alarmSecret; // temporary attribute for response
        return [$device, $token];
""")
write_file(rda_path, rda_data)

# RegisterDeviceRequest to accept fcm_token
rdr_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Requests\RegisterDeviceRequest.php"
with open(rdr_path, 'r', encoding='utf-8') as f:
    rdr_data = f.read()
if "'fcm_token'" not in rdr_data:
    rdr_data = rdr_data.replace("'sim_iccid' => 'nullable|string|max:50',", "'sim_iccid' => 'nullable|string|max:50',\n            'fcm_token' => 'nullable|string|max:255',")
    write_file(rdr_path, rdr_data)

# DeviceResource to return alarm_secret ONLY ONCE
dr_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Resources\DeviceResource.php"
with open(dr_path, 'r', encoding='utf-8') as f:
    dr_data = f.read()
if "'alarm_secret'" not in dr_data:
    dr_data = dr_data.replace("]; }", ", 'alarm_secret' => $this->when(isset($this->alarm_secret_plain), $this->alarm_secret_plain)]; }")
    write_file(dr_path, dr_data)

# Heartbeat Request to accept fcm_token
hr_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Requests\HeartbeatRequest.php"
with open(hr_path, 'r', encoding='utf-8') as f:
    hr_data = f.read()
if "'fcm_token'" not in hr_data:
    hr_data = hr_data.replace("];", ",\n            'fcm_token' => 'nullable|string|max:255'\n        ];")
    write_file(hr_path, hr_data)

# DeviceController: remove owner_password_hash
dc_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Controllers\Api\DeviceController.php"
with open(dc_path, 'r', encoding='utf-8') as f:
    dc_data = f.read()
dc_data = dc_data.replace("'owner_password_hash' => $device->owner?->password,", "")

# Also DeviceController@heartbeat needs to pass fcm_token to ProcessHeartbeatAction
dc_data = dc_data.replace("$request->validated('battery_level')", "$request->validated('battery_level'), $request->validated('fcm_token')")
write_file(dc_path, dc_data)

# ProcessHeartbeatAction: Update FCM token if provided, and timeout firebase sync
pha_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Device\Actions\ProcessHeartbeatAction.php"
with open(pha_path, 'r', encoding='utf-8') as f:
    pha_data = f.read()

pha_data = pha_data.replace("public function execute(Device $device, ?int $batteryLevel = null)", "public function execute(Device $device, ?int $batteryLevel = null, ?string $fcmToken = null)")
pha_data = pha_data.replace("if ($batteryLevel !== null) $state['battery_level'] = $batteryLevel;", "if ($batteryLevel !== null) $state['battery_level'] = $batteryLevel;\n        if ($fcmToken !== null) $state['fcm_token'] = $fcmToken;")

# Move Firebase OUTSIDE DB transaction!
pha_data = pha_data.replace("""return \\Illuminate\\Support\\Facades\\DB::transaction(function () use ($device, $state) {
            $device = $this->devices->update($device, $state);
            $commands = $this->commands->pendingForDevice($device);
            $this->commands->markSent($commands);
            $this->firebase->updateDeviceState($device->device_uid, $device->only([
                'last_seen_at', 'last_heartbeat_at', 'battery_level', 'is_screaming', 'is_tracking_continuous', 'is_locked', 'is_stolen', 'is_searching'
            ]));
            return [$device, $commands];
        });""", """$result = \\Illuminate\\Support\\Facades\\DB::transaction(function () use ($device, $state) {
            $device = $this->devices->update($device, $state);
            $commands = $this->commands->pendingForDevice($device);
            $this->commands->markSent($commands);
            return [$device, $commands];
        });
        try {
            // Firebase outside transaction with timeout handling (simulated via try-catch as guzzle configures it)
            $this->firebase->updateDeviceState($result[0]->device_uid, $result[0]->only([
                'last_seen_at', 'last_heartbeat_at', 'battery_level', 'is_screaming', 'is_tracking_continuous', 'is_locked', 'is_stolen', 'is_searching'
            ]));
        } catch (\\Throwable $e) {
            \\Illuminate\\Support\\Facades\\Log::warning('Firebase sync failed on heartbeat', ['error' => $e->getMessage()]);
        }
        return $result;""")
write_file(pha_path, pha_data)


# SendCommandAction FCM token use
sca_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Command\Actions\SendCommandAction.php"
with open(sca_path, 'r', encoding='utf-8') as f:
    sca_data = f.read()
sca_data = sca_data.replace("$fcmToken = $device->fcm_token ?? $device->device_token_hash;", "$fcmToken = $device->fcm_token;")
write_file(sca_path, sca_data)

# StopScreamAction: alarm_secret validation
ssa_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Application\Command\Actions\StopScreamAction.php"
with open(ssa_path, 'r', encoding='utf-8') as f:
    ssa_data = f.read()
ssa_data = ssa_data.replace("public function execute(Owner $owner, Device $device, string $password)", "public function execute(Owner $owner, Device $device, string $alarmSecret)")
ssa_data = ssa_data.replace("$valid = \\Illuminate\\Support\\Facades\\Hash::check($password, $owner->password);", "$valid = \\Illuminate\\Support\\Facades\\Hash::check($alarmSecret, $device->alarm_secret_hash);")
ssa_data = ssa_data.replace("throw new \\Illuminate\\Auth\\Access\\AuthorizationException('Invalid owner password.');", "throw new \\Symfony\\Component\\HttpKernel\\Exception\\HttpException(403, 'Invalid alarm secret.');")
write_file(ssa_path, ssa_data)

# StopScreamRequest: password -> alarm_secret
ssr_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Requests\StopScreamRequest.php"
with open(ssr_path, 'r', encoding='utf-8') as f:
    ssr_data = f.read()
ssr_data = ssr_data.replace("'password' => 'required|string'", "'alarm_secret' => 'required|string'")
write_file(ssr_path, ssr_data)

# CommandController@stopScream: parameter change
cc_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Controllers\Api\CommandController.php"
with open(cc_path, 'r', encoding='utf-8') as f:
    cc_data = f.read()
cc_data = cc_data.replace("$request->validated('password')", "$request->validated('alarm_secret')")
write_file(cc_path, cc_data)

# AuthController@me: Fix return OwnerResource
ac_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Controllers\Api\AuthController.php"
with open(ac_path, 'r', encoding='utf-8') as f:
    ac_data = f.read()
ac_data = ac_data.replace("public function me(Request $request): JsonResponse { return response()->json(['owner' => \\App\\Presentation\\Http\\Resources\\OwnerResource::make($request->user())]); }", "public function me(Request $request): JsonResponse { return response()->json(\\App\\Presentation\\Http\\Resources\\OwnerResource::make($request->user())); }")
write_file(ac_path, ac_data)

# AlertController and CreateAlertAction: Contract fixing
alert_c_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Controllers\Api\AlertController.php"
with open(alert_c_path, 'r', encoding='utf-8') as f:
    alert_c_data = f.read()
if "StoreAlertRequest" not in alert_c_data:
    alert_c_data = alert_c_data.replace("use Illuminate\\Http\\Request;", "use Illuminate\\Http\\Request;\nuse App\\Presentation\\Http\\Requests\\StoreAlertRequest;")
    alert_c_data = alert_c_data.replace("public function store(Request $request, CreateAlertAction $action): JsonResponse { return response()->json(\\App\\Presentation\\Http\\Resources\\AlertResource::make($action->execute($request->attributes->get('device'), $request->all())), 201); }", "public function store(StoreAlertRequest $request, CreateAlertAction $action): JsonResponse { return response()->json(\\App\\Presentation\\Http\\Resources\\AlertResource::make($action->execute($request->attributes->get('device'), $request->validated())), 201); }")
    write_file(alert_c_path, alert_c_data)

req_alert_path = r"C:\Users\moham\OneDrive\Desktop\z\app\Presentation\Http\Requests\StoreAlertRequest.php"
write_file(req_alert_path, """<?php
namespace App\Presentation\Http\Requests;
use Illuminate\Foundation\Http\FormRequest;

class StoreAlertRequest extends FormRequest
{
    public function authorize(): bool { return true; }
    public function rules(): array
    {
        return [
            'type' => 'required|string|max:50',
            'message' => 'required|string|max:1000',
            'photo_url' => 'nullable|string|url',
            'latitude' => 'nullable|numeric',
            'longitude' => 'nullable|numeric',
        ];
    }
}
""")
