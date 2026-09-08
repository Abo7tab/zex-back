<?php

namespace App\Presentation\Http\Controllers\Api;

use App\Application\Owner\Actions\LoginOwnerAction;
use App\Application\Owner\Actions\RegisterOwnerAction;
use App\Presentation\Http\Requests\LoginOwnerRequest;
use App\Presentation\Http\Requests\RegisterOwnerRequest;
use App\Presentation\Http\Resources\OwnerResource;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class AuthController
{
    public function register(RegisterOwnerRequest $request, RegisterOwnerAction $action): JsonResponse { [$owner, $token] = $action->execute($request->validated()); return response()->json(['owner' => OwnerResource::make($owner), 'token' => $token], 201); }
    public function login(LoginOwnerRequest $request, LoginOwnerAction $action): JsonResponse { [$owner, $token] = $action->execute($request->validated('email'), $request->validated('password')); return response()->json(['owner' => OwnerResource::make($owner), 'token' => $token]); }
    public function me(Request $request): OwnerResource { return OwnerResource::make($request->user()); }
    public function logout(Request $request): JsonResponse { $request->user()->currentAccessToken()?->delete(); return response()->json(['message' => 'Logged out successfully']); }
}
