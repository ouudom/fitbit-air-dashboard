<?php

declare(strict_types=1);

use Illuminate\Support\Facades\Route;
use Modules\GoogleHealth\Http\Controllers\GoogleHealthAuthController;
use Modules\GoogleHealth\Http\Controllers\SyncController;

Route::get('/login', [GoogleHealthAuthController::class, 'show'])->name('login');
Route::get('/api/auth/login', [GoogleHealthAuthController::class, 'redirect'])->name('auth.google.redirect');
// Preserve the connect URL used by the previous deployment.
Route::get('/auth/fitbit/redirect', [GoogleHealthAuthController::class, 'redirect']);
Route::get('/api/auth/callback', [GoogleHealthAuthController::class, 'callback'])->name('auth.google.callback');
Route::post('/api/auth/logout', [GoogleHealthAuthController::class, 'logout'])->name('logout');
Route::post('/logout', [GoogleHealthAuthController::class, 'logout']);

Route::middleware('health.connected')->prefix('dashboard')->group(function (): void {
    Route::post('/sync', [SyncController::class, 'store'])->name('dashboard.sync');
});
