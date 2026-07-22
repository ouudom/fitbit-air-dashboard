<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Analytics\HealthDataService;
use App\Http\Controllers\Controller;
use Inertia\Inertia;
use Inertia\Response;

final class SleepController extends Controller
{
    public function __invoke(HealthDataService $health): Response
    {
        $sleep = $health->sleep(90);
        $vitals = $health->vitals();

        return Inertia::render('Dashboard/Sleep', [...$sleep, 'respiratory' => $vitals['daily-respiratory-rate'] ?? []]);
    }
}
