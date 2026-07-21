<?php

declare(strict_types=1);

namespace Tests\Unit\Domain\Analytics\Support;

use App\Domain\Analytics\Contracts\AnalyticsRepository;

final class MemoryAnalyticsRepository implements AnalyticsRepository
{
    /** @var array<string, list<array<string, mixed>>> */
    public array $records = [];

    /** @var array<string, list<array{date: string, value: float|null}>> */
    public array $daily = [];

    /** @var list<array<string, mixed>> */
    public array $savedScores = [];

    /** @var list<array<string, mixed>> */
    public array $quality = [];

    public array $food = [];

    public array $journals = [];

    public array $strength = [];

    public array $storedScores = [];

    public array $qualityRows = [];

    public array $timelineRows = [];

    public array $metaValues = [];

    public function healthRecords(string $dataType, int $limit = 100): array
    {
        return array_slice($this->records[$dataType] ?? [], 0, $limit);
    }

    public function dailyMetric(string $metric, int $days): array
    {
        return array_slice($this->daily[$metric] ?? [], -$days);
    }

    public function exercises(int $limit): array
    {
        return [];
    }

    public function healthCoverage(): array
    {
        return [];
    }

    public function syncStates(): array
    {
        return [];
    }

    public function foodLogs(?string $date = null): array
    {
        return $this->food;
    }

    public function journal(?string $from = null, ?string $to = null): array
    {
        return $this->journals;
    }

    public function strengthSessions(int $limit = 50): array
    {
        return array_slice($this->strength, 0, $limit);
    }

    public function scores(string $type, int $days): array
    {
        return array_slice($this->storedScores, 0, $days);
    }

    public function quality(string $date): array
    {
        return $this->qualityRows;
    }

    public function timeline(string $date): array
    {
        return $this->timelineRows;
    }

    public function meta(string $key): ?string
    {
        return $this->metaValues[$key] ?? null;
    }

    public function saveScores(array $scores): void
    {
        $this->savedScores = $scores;
    }

    public function saveQuality(array $quality): void
    {
        $this->quality[] = $quality;
    }
}
