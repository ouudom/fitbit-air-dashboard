<?php

declare(strict_types=1);

use App\Jobs\SyncHealthData;
use Illuminate\Support\Facades\Schedule;

Schedule::job(new SyncHealthData(3, true))
    ->hourly()
    ->name('health-sync')
    ->withoutOverlapping(30)
    ->onOneServer();
