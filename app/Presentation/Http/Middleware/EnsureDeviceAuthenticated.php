<?php

namespace App\Presentation\Http\Middleware;

use App\Domain\Device\Repositories\DeviceRepositoryInterface;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Symfony\Component\HttpFoundation\Response;

class EnsureDeviceAuthenticated
{
    public function __construct(private DeviceRepositoryInterface $devices) {}

    public function handle(Request $request, Closure $next): Response
    {
        $token = (string) $request->header('X-Device-Token');
        $uid = $request->input('device_uid');
        $device = is_string($uid) && trim($uid) !== ''
            ? $this->devices->findByUid($uid)
            : $this->devices->findByToken($token);

        // Legacy mobile BLE/SMS relay payloads omit device_uid. The token still
        // identifies the source device, and an explicit UID remains cross-checked.
        if (! $device || trim($token) === '' || ! Hash::check($token, (string) $device->device_token_hash)) {
            return response()->json(['message' => 'Unauthenticated device.'], 401);
        }
        $request->attributes->set('device', $device);
        return $next($request);
    }
}
