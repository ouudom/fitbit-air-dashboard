<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Analytics\DashboardProjectionService;
use App\Http\Controllers\Controller;
use Inertia\Inertia;
use Inertia\Response;

final class DashboardController extends Controller
{
    public function __invoke(DashboardProjectionService $dashboard): Response
    {
        $date = now()->toDateString();

        return Inertia::render('Dashboard/Index', $dashboard->day($date));
    }
}
