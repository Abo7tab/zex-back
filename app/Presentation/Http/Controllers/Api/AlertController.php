<?php

namespace App\Presentation\Http\Controllers\Api;

use App\Application\Alert\Actions\CreateAlertAction;
use App\Application\Alert\Actions\GetOwnerAlertsAction;
use App\Application\Alert\Actions\MarkAlertReadAction;
use App\Domain\Alert\Models\Alert;
use App\Presentation\Http\Requests\StoreAlertRequest;
use App\Presentation\Http\Resources\AlertResource;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class AlertController
{
    public function store(StoreAlertRequest $request, CreateAlertAction $action): JsonResponse { $alert = $action->execute($request->attributes->get('device'), $request->safe()->except('device_uid')); return response()->json(AlertResource::make($alert), 201); }
    public function index(Request $request, GetOwnerAlertsAction $action): JsonResponse { [$alerts, $unread] = $action->execute($request->user()); return response()->json(['data' => AlertResource::collection($alerts), 'unread_count' => $unread]); }
    public function markRead(Request $request, Alert $alert, MarkAlertReadAction $action): AlertResource { return AlertResource::make($action->execute($request->user(), $alert)); }
}
