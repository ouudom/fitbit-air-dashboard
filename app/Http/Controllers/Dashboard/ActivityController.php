<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Analytics\Contracts\AnalyticsRepository;
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

    public function data(HealthDataService $health): Response
    {
        return Inertia::render('Dashboard/Data', $health->explorer());
    }

    public function dataType(string $type, AnalyticsRepository $repository): Response
    {
        abort_unless(preg_match('/^[a-z0-9-]+$/', $type) === 1, 404);

        return Inertia::render('Dashboard/DataType', ['type' => $type, 'records' => $repository->healthRecords($type, 500)]);
    }
}
