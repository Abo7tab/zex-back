<?php

namespace App\Presentation\Http\Controllers\Api;

use App\Domain\Owner\Models\Owner;
use App\Presentation\Http\Requests\RegisterOwnerRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\ValidationException;

class AuthController
{
    public function register(RegisterOwnerRequest $request): JsonResponse
    {
        $owner = Owner::create([
            'name' => $request->validated('name'),
            'email' => $request->validated('email'),
            'phone' => $request->validated('phone'),
            'password' => Hash::make($request->validated('password')),
            'pin_code' => $request->validated('pin_code'),
        ]);

        $token = $owner->createToken('api-token')->plainTextToken;

        return response()->json([
            'owner' => $owner,
            'token' => $token,
        ], 201);
    }

    public function login(Request $request): JsonResponse
    {
        $request->validate([
            'email' => ['required', 'email'],
            'password' => ['required'],
        ]);

        $owner = Owner::where('email', $request->email)->first();

        if (! $owner || ! Hash::check($request->password, $owner->password)) {
            throw ValidationException::withMessages([
                'email' => ['Invalid credentials.'],
            ]);
        }

        $token = $owner->createToken('api-token')->plainTextToken;

        return response()->json([
            'owner' => $owner,
            'token' => $token,
        ]);
    }

    public function me(Request $request): JsonResponse
    {
        return response()->json($request->user());
    }

    public function logout(Request $request): JsonResponse
    {
        $request->user()->currentAccessToken()->delete();

        return response()->json(['message' => 'Logged out successfully']);
    }
}
