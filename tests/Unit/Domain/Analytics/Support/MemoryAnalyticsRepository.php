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

    public array $food = [];

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

    public function foodLogs(?string $date = null): array
    {
        return $this->food;
    }

    public function meta(string $key): ?string
    {
        return $this->metaValues[$key] ?? null;
    }
}
