<?php

declare(strict_types=1);

namespace Tests\Unit\Domain\Analytics;

use App\Domain\Analytics\ScoringService;
use PHPUnit\Framework\TestCase;
use Tests\Unit\Domain\Analytics\Support\MemoryAnalyticsRepository;

final class ScoringServiceTest extends TestCase
{
    public function test_it_preserves_wellness_v1_calibration_and_persistence_shape(): void
    {
        $repository = new MemoryAnalyticsRepository;
        foreach (range(1, 28) as $day) {
            $date = sprintf('2026-05-%02d', $day);
            $repository->records['daily-heart-rate-variability'][] = $this->record("hrv-$day", $date, 50);
            $repository->records['daily-resting-heart-rate'][] = $this->record("rhr-$day", $date, 60);
            $repository->records['daily-respiratory-rate'][] = $this->record("resp-$day", $date, 15);
            $repository->daily['steps'][] = ['date' => $date, 'value' => 10000.0];
        }
        $repository->records['daily-heart-rate-variability'][] = $this->record('hrv-now', '2026-05-29', 55);
        $repository->records['daily-resting-heart-rate'][] = $this->record('rhr-now', '2026-05-29', 58);
        $repository->records['daily-respiratory-rate'][] = $this->record('resp-now', '2026-05-29', 15);
        $repository->daily['steps'][] = ['date' => '2026-05-29', 'value' => 12000.0];

        $scores = (new ScoringService($repository))->compute('2026-05-29');
        $recovery = $scores[0];

        self::assertSame(ScoringService::SCORE_VERSION, $recovery['modelVersion']);
        self::assertSame('ready', $recovery['state']);
        self::assertSame('medium', $recovery['confidence']);
        self::assertSame(82, $recovery['value']);
        self::assertSame('positive', $recovery['contributions'][0]['status']);
        self::assertCount(5, $repository->savedScores);
        self::assertSame('wellness-v1.0.0', $repository->savedScores[0]['modelVersion']);
        self::assertSame(['recovery', 'sleep', 'activity'], array_column($repository->quality, 'dataType'));
    }

    /** @return array<string, mixed> */
    private function record(string $id, string $date, float $value): array
    {
        return ['id' => $id, 'date' => $date, 'startTime' => null, 'numericValue' => $value, 'payload' => []];
    }
}
