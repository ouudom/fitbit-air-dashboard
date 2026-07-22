<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Analytics\HealthDataService;
use App\Http\Controllers\Controller;
use Inertia\Inertia;
use Inertia\Response;

final class ActivityController extends Controller
{
    public function index(HealthDataService $health): Response
    {
        return Inertia::render('Dashboard/Activity', $health->activity(90));
    }

    public function heart(HealthDataService $health): Response
    {
        return Inertia::render('Dashboard/Heart', ['vitals' => $health->vitals()]);
    }
}
