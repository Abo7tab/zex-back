<?php

namespace App\Presentation\Http\Controllers\Api;

use App\Application\Location\DTOs\LocationDataDTO;
use App\Domain\Device\Models\Device;
use App\Domain\Location\Models\Location;
use App\Presentation\Http\Requests\StoreLocationRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class LocationController
{
    public function history(Request $request, int $deviceId): JsonResponse
    {
        $device = $request->user()->devices()->findOrFail($deviceId);
        $locations = $device->locations()->orderBy('recorded_at', 'desc')->paginate(50);

        return response()->json($locations);
    }

    public function store(StoreLocationRequest $request): JsonResponse
    {
        $device = Device::where('device_uid', $request->validated('device_uid'))->firstOrFail();

        $dto = new LocationDataDTO(
            latitude: (float) $request->validated('latitude'),
            longitude: (float) $request->validated('longitude'),
            accuracy: $request->validated('accuracy') ? (float) $request->validated('accuracy') : null,
            speed: $request->validated('speed') ? (float) $request->validated('speed') : null,
            recorded_at: $request->validated('recorded_at')
        );

        $location = $device->locations()->create([
            'latitude' => $dto->latitude,
            'longitude' => $dto->longitude,
            'accuracy' => $dto->accuracy,
            'speed' => $dto->speed,
            'recorded_at' => $dto->recorded_at ?? now(),
        ]);

        return response()->json($location, 201);
    }
}
