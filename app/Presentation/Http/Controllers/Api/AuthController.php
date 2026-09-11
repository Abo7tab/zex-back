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
    
    public function updateProfile(Request $request): JsonResponse {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'email' => 'required|email|max:255|unique:owners,email,' . $request->user()->id,
        ]);
        $request->user()->update($validated);
        return response()->json(['message' => 'Profile updated successfully', 'owner' => OwnerResource::make($request->user())]);
    }

    public function updateSecurity(Request $request): JsonResponse {
        $validated = $request->validate([
            'current_password' => 'required|string',
            'password' => 'nullable|string|min:8|confirmed',
            'pin_code' => 'nullable|string|size:6',
        ]);

        $user = $request->user();

        if (!\Illuminate\Support\Facades\Hash::check($validated['current_password'], $user->password)) {
            return response()->json(['message' => 'Current password is incorrect'], 422);
        }

        $updates = [];
        if (!empty($validated['password'])) {
            $updates['password'] = \Illuminate\Support\Facades\Hash::make($validated['password']);
        }
        if (!empty($validated['pin_code'])) {
            $updates['pin_code'] = \Illuminate\Support\Facades\Hash::make($validated['pin_code']);
        }

        if (!empty($updates)) {
            $user->update($updates);
        }

        return response()->json(['message' => 'Security settings updated successfully']);
    }
}
