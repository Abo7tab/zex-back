<?php

use App\Presentation\Http\Controllers\Api\AlertController;
use App\Presentation\Http\Controllers\Api\AuthController;
use App\Presentation\Http\Controllers\Api\CommandController;
use App\Presentation\Http\Controllers\Api\DeviceController;
use App\Presentation\Http\Controllers\Api\LocationController;
use Illuminate\Support\Facades\Route;

Route::post('/auth/register', [AuthController::class, 'register'])->middleware('throttle:3,1');
Route::post('/auth/login', [AuthController::class, 'login'])->middleware('throttle:5,1');

Route::middleware('device.auth')->group(function () {
    Route::post('/devices/heartbeat', [DeviceController::class, 'heartbeat'])->middleware('throttle:120,1');
    Route::post('/locations', [LocationController::class, 'store'])->middleware('throttle:120,1');
    Route::post('/locations/ble-relay', [LocationController::class, 'bleRelay'])->middleware('throttle:60,1');
    Route::post('/commands/{command}/response', [CommandController::class, 'storeResponse'])->middleware('throttle:120,1');
    Route::post('/alerts', [AlertController::class, 'store'])->middleware('throttle:120,1');
});

Route::middleware('auth:sanctum')->group(function () {
    Route::get('/auth/me', [AuthController::class, 'me']);
    Route::post('/auth/logout', [AuthController::class, 'logout']);
    Route::post('/devices/register', [DeviceController::class, 'register']);
    Route::delete('/devices/{device}', [DeviceController::class, 'destroy']);
    Route::get('/devices', [DeviceController::class, 'index']);
    Route::get('/devices/{device}', [DeviceController::class, 'show']);
    Route::get('/devices/{device}/locations', [LocationController::class, 'history']);
    Route::post('/devices/{device}/commands', [CommandController::class, 'send']);
    Route::post('/devices/{device}/locate', [CommandController::class, 'locate']);
    Route::post('/devices/{device}/scream', [CommandController::class, 'scream']);
    Route::post('/devices/{device}/stop-scream', [CommandController::class, 'stopScream']);
    Route::post('/devices/{device}/track', [CommandController::class, 'track']);
    Route::post('/devices/{device}/stop-tracking', [CommandController::class, 'stopTracking']);
    Route::post('/devices/{device}/lock', [CommandController::class, 'lock']);
    Route::post('/devices/{device}/photo', [CommandController::class, 'photo']);
    Route::post('/devices/{device}/enable-net', [CommandController::class, 'enableNet']);
    Route::post('/devices/{device}/stolen', [CommandController::class, 'stolen']);
    Route::post('/devices/{device}/found', [CommandController::class, 'found']);
    Route::post('/devices/{device}/search-mode', [DeviceController::class, 'searchMode']);
    Route::post('/devices/{device}/stop-search', [DeviceController::class, 'stopSearch']);
    Route::get('/alerts', [AlertController::class, 'index']);
    Route::post('/alerts/{alert}/read', [AlertController::class, 'markRead']);
});

// Device status endpoint that supports both owner and device token auth without middleware strictly blocking it
Route::get('/devices/{device}/status', [DeviceController::class, 'status']);

