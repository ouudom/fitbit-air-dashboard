<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Analytics\HealthDataService;
use App\Domain\Analytics\ScoringService;
use App\Http\Controllers\Controller;
use Inertia\Inertia;
use Inertia\Response;

final class WellnessController extends Controller
{
    public function recovery(ScoringService $scoring): Response
    {
        $scores = $scoring->compute();

        return Inertia::render('Dashboard/Recovery', ['score' => $this->score($scores, 'recovery')]);
    }

    public function sleep(HealthDataService $health): Response
    {
        $sleep = $health->sleep(90);
        $vitals = $health->vitals();

        return Inertia::render('Dashboard/Sleep', [...$sleep, 'respiratory' => $vitals['daily-respiratory-rate'] ?? []]);
    }

    public function strain(ScoringService $scoring): Response
    {
        $scores = $scoring->compute();

        return Inertia::render('Dashboard/Strain', [
            'scores' => array_values(array_filter($scores, static fn (array $score): bool => in_array($score['type'], ['strain', 'stress', 'energy'], true))),
        ]);
    }

    /** @param list<array<string, mixed>> $scores */
    private function score(array $scores, string $type): ?array
    {
        foreach ($scores as $score) {
            if ($score['type'] === $type) {
                return $score;
            }
        }

        return null;
    }
}
