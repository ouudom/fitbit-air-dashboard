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

    /** @return list<array{dataType: string, count: int, latest: string|null}> */
    public function healthCoverage(): array;

    /** @return list<array<string, mixed>> */
    public function syncStates(): array;

    /** @return list<array<string, mixed>> */
    public function foodLogs(?string $date = null): array;

    /** @return list<array<string, mixed>> */
    public function journal(?string $from = null, ?string $to = null): array;

    /** @return list<array<string, mixed>> */
    public function strengthSessions(int $limit = 50): array;

    /** @return list<array<string, mixed>> */
    public function scores(string $type, int $days): array;

    /** @return list<array<string, mixed>> */
    public function quality(string $date): array;

    /** @return list<array<string, mixed>> */
    public function timeline(string $date): array;

    public function meta(string $key): ?string;

    /** @param list<array<string, mixed>> $scores */
    public function saveScores(array $scores): void;

    /** @param array<string, mixed> $quality */
    public function saveQuality(array $quality): void;
}
