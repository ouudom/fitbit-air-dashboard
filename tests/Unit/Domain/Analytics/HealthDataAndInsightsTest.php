<?php

declare(strict_types=1);

namespace Tests\Unit\Domain\Analytics;

use App\Domain\Analytics\HealthDataService;
use App\Domain\Analytics\InsightsService;
use PHPUnit\Framework\TestCase;
use Tests\Unit\Domain\Analytics\Support\MemoryAnalyticsRepository;

final class HealthDataAndInsightsTest extends TestCase
{
    public function test_it_projects_sleep_payload_and_stage_totals(): void
    {
        $repository = new MemoryAnalyticsRepository;
        $repository->records['sleep'][] = [
            'id' => 'sleep-1', 'date' => null, 'startTime' => null, 'endTime' => null, 'numericValue' => null,
            'payload' => ['name' => 'sleep', 'sleep' => [
                'interval' => ['startTime' => '2026-05-29T22:00:00Z', 'endTime' => '2026-05-30T06:00:00Z'],
                'summary' => ['minutesAsleep' => 430, 'minutesAwake' => 30, 'minutesInSleepPeriod' => 480,
                    'stagesSummary' => [['type' => 'DEEP', 'minutes' => 70], ['type' => 'DEEP', 'minutes' => 10], ['type' => 'REM', 'minutes' => 90]]],
            ]],
        ];

        $sleep = (new HealthDataService($repository))->sleep();

        self::assertSame('2026-05-29', $sleep['latest']['date']);
        self::assertSame(430.0, $sleep['latest']['minutesAsleep']);
        self::assertSame(80.0, $sleep['latest']['stages']['deep']);
        self::assertSame([['date' => '2026-05-29', 'value' => 430.0]], $sleep['trend']);
    }

    public function test_it_computes_journal_nutrition_and_strength_summaries(): void
    {
        $repository = new MemoryAnalyticsRepository;
        foreach (range(1, 5) as $day) {
            $repository->journals[] = ['date' => "2026-05-0$day", 'habit' => 'alcohol', 'value' => 'yes'];
            $repository->journals[] = ['date' => "2026-05-1$day", 'habit' => 'alcohol', 'value' => 'no'];
            $repository->storedScores[] = ['date' => "2026-05-0$day", 'value' => 70];
            $repository->storedScores[] = ['date' => "2026-05-1$day", 'value' => 80];
        }
        $repository->food = [['calories' => 500, 'proteinG' => 30, 'carbsG' => null, 'fatG' => 10], ['calories' => 250, 'proteinG' => 15, 'carbsG' => 20, 'fatG' => null]];
        $repository->strength = [['sets' => [['loadKg' => 50, 'reps' => 5], ['loadKg' => 60, 'reps' => 3]]]];
        $service = new InsightsService($repository);

        self::assertSame(-10.0, $service->journal()[0]['effect']);
        self::assertStringContainsString('Correlation is not causation.', $service->journal()[0]['note']);
        self::assertSame(['calories' => 750.0, 'proteinG' => 45.0, 'carbsG' => 20.0, 'fatG' => 10.0, 'entries' => 2], $service->nutrition('2026-05-29'));
        self::assertSame(['sessions' => 1, 'volumeKg' => 430.0], $service->strength());
    }
}
