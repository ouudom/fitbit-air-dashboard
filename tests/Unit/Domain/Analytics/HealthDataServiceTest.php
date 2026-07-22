<?php

declare(strict_types=1);

namespace Tests\Unit\Domain\Analytics;

use App\Domain\Analytics\HealthDataService;
use PHPUnit\Framework\TestCase;
use Tests\Unit\Domain\Analytics\Support\MemoryAnalyticsRepository;

/** @covers \App\Domain\Analytics\HealthDataService */
final class HealthDataServiceTest extends TestCase
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
}
