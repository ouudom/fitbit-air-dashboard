<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Analytics\Contracts\AnalyticsRepository;
use App\Domain\Analytics\ScoringService;
use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;

final class TrendsController extends Controller
{
    public function __invoke(Request $request, AnalyticsRepository $repository, ScoringService $scoring): Response
    {
        $metric = $request->string('metric', 'recovery')->toString();
        $range = max(7, min(90, $request->integer('range', 30)));
        if (in_array($metric, ['recovery', 'sleep', 'strain', 'stress', 'energy'], true)) {
            $scoring->computeRange($range);
            $points = array_reverse(array_map(static fn (array $row): array => [
                'date' => $row['date'], 'value' => $row['value'], 'confidence' => $row['confidence'],
            ], $repository->scores($metric, $range)));
        } else {
            $points = $repository->dailyMetric($metric, $range);
        }

        return Inertia::render('Dashboard/Trends', [
            'metric' => $metric,
            'range' => $range,
            'series' => ['metric' => $metric, 'range' => $range, 'points' => $points],
        ]);
    }
}
