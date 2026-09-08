<?php

namespace App\Presentation\Http\Controllers\Api;

use App\Application\Location\Actions\GetLocationHistoryAction;
use App\Application\Location\Actions\StoreLocationAction;
use App\Domain\Device\Models\Device;
use App\Presentation\Http\Requests\StoreLocationRequest;
use App\Presentation\Http\Resources\LocationResource;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class LocationController
{
    public function history(Request $request, Device $device, GetLocationHistoryAction $action) { return LocationResource::collection($action->execute($request->user(), $device)); }
    public function store(StoreLocationRequest $request, StoreLocationAction $action): JsonResponse { $location = $action->execute($request->attributes->get('device'), $request->safe()->except('device_uid')); return response()->json(LocationResource::make($location), 201); }
}
