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
        $device = is_string($request->input('device_uid')) ? $this->devices->findByUid($request->input('device_uid')) : null;
        if (! $device || ! Hash::check((string) $request->header('X-Device-Token'), $device->device_token_hash)) return response()->json(['message' => 'Unauthenticated device.'], 401);
        $request->attributes->set('device', $device);
        return $next($request);
    }
}
