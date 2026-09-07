<?php

use App\Presentation\Http\Controllers\Api\AuthController;
use App\Presentation\Http\Controllers\Api\CommandController;
use App\Presentation\Http\Controllers\Api\DeviceController;
use App\Presentation\Http\Controllers\Api\LocationController;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| Public Routes (Device/Owner)
|--------------------------------------------------------------------------
*/

// Owner Auth
Route::post('/auth/register', [AuthController::class, 'register']);
Route::post('/auth/login', [AuthController::class, 'login']);

// Device Public API (using device_uid)
Route::post('/devices/register', [DeviceController::class, 'register']);
Route::post('/devices/heartbeat', [DeviceController::class, 'heartbeat']);
Route::post('/locations', [LocationController::class, 'store']);
Route::post('/commands/response', [CommandController::class, 'storeResponse']);


/*
|--------------------------------------------------------------------------
| Protected Routes (Owner)
|--------------------------------------------------------------------------
*/

Route::middleware('auth:sanctum')->group(function () {
    // Auth
    Route::get('/auth/me', [AuthController::class, 'me']);
    Route::post('/auth/logout', [AuthController::class, 'logout']);

    // Devices
    Route::get('/devices', [DeviceController::class, 'index']);
    Route::get('/devices/{id}', [DeviceController::class, 'show']);

    // Locations
    Route::get('/devices/{deviceId}/locations', [LocationController::class, 'history']);

    // Commands
    Route::post('/commands', [CommandController::class, 'send']);
});
