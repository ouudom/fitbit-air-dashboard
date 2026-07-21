<?php

declare(strict_types=1);

use App\Http\Controllers\Dashboard\ActivityController;
use App\Http\Controllers\Dashboard\CoachController;
use App\Http\Controllers\Dashboard\DashboardController;
use App\Http\Controllers\Dashboard\FoodController;
use App\Http\Controllers\Dashboard\JournalController;
use App\Http\Controllers\Dashboard\StrengthController;
use App\Http\Controllers\Dashboard\TrendsController;
use App\Http\Controllers\Dashboard\WellnessController;
use Illuminate\Support\Facades\Route;

Route::redirect('/', '/dashboard');

Route::middleware('health.connected')->prefix('dashboard')->group(function (): void {
    Route::get('/', DashboardController::class)->name('dashboard');
    Route::get('/recovery', [WellnessController::class, 'recovery'])->name('dashboard.recovery');
    Route::get('/sleep', [WellnessController::class, 'sleep'])->name('dashboard.sleep');
    Route::get('/strain', [WellnessController::class, 'strain'])->name('dashboard.strain');
    Route::get('/activity', [ActivityController::class, 'index'])->name('dashboard.activity');
    Route::get('/heart', [ActivityController::class, 'heart'])->name('dashboard.heart');
    Route::get('/trends', TrendsController::class)->name('dashboard.trends');
    Route::get('/data', [ActivityController::class, 'data'])->name('dashboard.data');
    Route::get('/data/{type}', [ActivityController::class, 'dataType'])->name('dashboard.data.type');
    Route::get('/coach', [CoachController::class, 'index'])->name('dashboard.coach');
    Route::post('/coach', [CoachController::class, 'store'])->name('dashboard.coach.store');

    Route::get('/food', [FoodController::class, 'index'])->name('dashboard.food');
    Route::post('/food', [FoodController::class, 'store'])->name('dashboard.food.store');
    Route::delete('/food/{food}', [FoodController::class, 'destroy'])->name('dashboard.food.destroy');
    Route::get('/journal', [JournalController::class, 'index'])->name('dashboard.journal');
    Route::post('/journal', [JournalController::class, 'store'])->name('dashboard.journal.store');
    Route::delete('/journal/{journal}', [JournalController::class, 'destroy'])->name('dashboard.journal.destroy');
    Route::get('/strength', [StrengthController::class, 'index'])->name('dashboard.strength');
    Route::post('/strength', [StrengthController::class, 'store'])->name('dashboard.strength.store');
    Route::delete('/strength/{strength}', [StrengthController::class, 'destroy'])->name('dashboard.strength.destroy');
});
