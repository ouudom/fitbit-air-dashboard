<?php

declare(strict_types=1);

namespace App\Domain\Analytics\Contracts;

interface AnalyticsRepository
{
    /** @return list<array<string, mixed>> */
    public function healthRecords(string $dataType, int $limit = 100): array;

    /** @return list<array{date: string, value: float|null}> */
    public function dailyMetric(string $metric, int $days): array;

    /** @return list<array<string, mixed>> */
    public function exercises(int $limit): array;

    /** @return list<array<string, mixed>> */
    public function foodLogs(?string $date = null): array;

    public function meta(string $key): ?string;
}
