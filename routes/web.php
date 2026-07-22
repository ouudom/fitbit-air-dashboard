<?php

declare(strict_types=1);

use App\Http\Controllers\Dashboard\ActivityController;
use App\Http\Controllers\Dashboard\DashboardController;
use App\Http\Controllers\Dashboard\FoodController;
use App\Http\Controllers\Dashboard\SleepController;
use Illuminate\Support\Facades\Route;

Route::redirect('/', '/dashboard');

Route::middleware('health.connected')->group(function (): void {
    Route::get('/dashboard', DashboardController::class)->name('dashboard');
    Route::get('/fitness', [ActivityController::class, 'index'])->name('fitness');
    Route::get('/sleep', SleepController::class)->name('sleep');
    Route::get('/health', [ActivityController::class, 'heart'])->name('health');

    Route::get('/health/nutrition', [FoodController::class, 'index'])->name('health.nutrition');
    Route::post('/health/nutrition', [FoodController::class, 'store'])->name('health.nutrition.store');
    Route::delete('/health/nutrition/{food}', [FoodController::class, 'destroy'])->name('health.nutrition.destroy');
});
