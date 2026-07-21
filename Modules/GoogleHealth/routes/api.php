<?php

declare(strict_types=1);

use Illuminate\Support\Facades\Route;
use Modules\GoogleHealth\Http\Controllers\SyncController;

Route::post('/cron/sync', [SyncController::class, 'cron'])->name('cron.sync');
