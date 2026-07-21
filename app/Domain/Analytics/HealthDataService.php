<?php

declare(strict_types=1);

namespace App\Domain\Analytics;

use App\Domain\Analytics\Contracts\AnalyticsRepository;

final class HealthDataService
{
    public function __construct(private readonly AnalyticsRepository $repository) {}

    /** @return array{sessions: list<array<string, mixed>>, latest: array<string, mixed>|null, trend: list<array{date: mixed, value: mixed}>} */
    public function sleep(int $limit = 90): array
    {
        $sessions = array_map(fn (array $row): array => $this->sleepSession($row), $this->repository->healthRecords('sleep', $limit));

        return [
            'sessions' => $sessions,
            'latest' => $sessions[0] ?? null,
            'trend' => array_map(static fn (array $session): array => ['date' => $session['date'], 'value' => $session['minutesAsleep']], array_reverse($sessions)),
        ];
    }

    /** @return array<string, list<array<string, mixed>>> */
    public function vitals(): array
    {
        $result = [];
        foreach ([
            ['daily-resting-heart-rate', 'bpm'], ['daily-heart-rate-variability', 'ms'],
            ['daily-oxygen-saturation', '%'], ['daily-respiratory-rate', '/min'],
            ['daily-sleep-temperature-derivations', 'variation'], ['daily-vo2-max', 'VO₂'],
        ] as [$type, $unit]) {
            $result[$type] = array_map(fn (array $row): array => $this->vitalPoint($row, $unit), $this->repository->healthRecords($type, 90));
        }
        foreach ([['heart-rate', 'bpm', 500], ['heart-rate-variability', 'ms', 90]] as [$type, $unit, $limit]) {
            $rows = array_filter($this->repository->healthRecords($type, $limit), static fn (array $row): bool => ! empty($row['startTime']) || ! empty($row['date']));
            $result[$type] = array_map(fn (array $row): array => $this->vitalPoint($row, $unit), array_values($rows));
        }

        return $result;
    }

    /** @return array{metrics: array<string, list<array{date: string, value: float|null}>>, exercises: list<array<string, mixed>>} */
    public function activity(int $days = 90): array
    {
        $metrics = [];
        foreach (['steps', 'active-zone-minutes', 'active-minutes', 'total-calories', 'active-energy-burned', 'distance', 'floors'] as $metric) {
            $metrics[$metric] = $this->repository->dailyMetric($metric, $days);
        }

        return ['metrics' => $metrics, 'exercises' => $this->repository->exercises(100)];
    }

    /** @return array{coverage: list<array<string, mixed>>, syncStates: list<array<string, mixed>>} */
    public function explorer(): array
    {
        return ['coverage' => $this->repository->healthCoverage(), 'syncStates' => $this->repository->syncStates()];
    }

    /** @param array<string, mixed> $row
     * @return array<string, mixed>
     */
    private function sleepSession(array $row): array
    {
        $payload = $this->inner($row['payload'] ?? []);
        $summary = is_array($payload['summary'] ?? null) ? $payload['summary'] : [];
        $interval = is_array($payload['interval'] ?? null) ? $payload['interval'] : [];
        $stages = ['awake' => 0.0, 'light' => 0.0, 'deep' => 0.0, 'rem' => 0.0];
        foreach (($summary['stagesSummary'] ?? []) as $stage) {
            $key = strtolower((string) ($stage['type'] ?? ''));
            if (array_key_exists($key, $stages)) {
                $stages[$key] += $this->number($stage['minutes'] ?? null) ?? 0;
            }
        }
        $start = $interval['startTime'] ?? $row['startTime'] ?? null;
        $end = $interval['endTime'] ?? $row['endTime'] ?? null;

        return [
            'id' => $row['id'], 'date' => $row['date'] ?? ($start === null ? null : substr((string) $start, 0, 10)),
            'startTime' => $start, 'endTime' => $end,
            'minutesAsleep' => $this->number($summary['minutesAsleep'] ?? null),
            'minutesAwake' => $this->number($summary['minutesAwake'] ?? null),
            'minutesInSleepPeriod' => $this->number($summary['minutesInSleepPeriod'] ?? null),
            'minutesToFallAsleep' => $this->number($summary['minutesToFallAsleep'] ?? null),
            'minutesAfterWakeUp' => $this->number($summary['minutesAfterWakeUp'] ?? null), 'stages' => $stages,
        ];
    }

    /** @param array<string, mixed> $row
     * @return array<string, mixed>
     */
    private function vitalPoint(array $row, string $unit): array
    {
        $payload = $this->inner($row['payload'] ?? []);
        $value = $row['numericValue'] ?? null;
        if ($value === null) {
            foreach (['averageHeartRateVariabilityMilliseconds', 'dailyAverageHeartRateVariabilityMilliseconds', 'breathsPerMinute', 'beatsPerMinute', 'percentage', 'value', 'average'] as $key) {
                if (array_key_exists($key, $payload) && $payload[$key] !== null) {
                    $value = $payload[$key];
                    break;
                }
            }
        }

        return [
            'id' => $row['id'], 'date' => $row['date'] ?? (! empty($row['startTime']) ? substr((string) $row['startTime'], 0, 10) : null),
            'time' => $row['startTime'] ?? null, 'value' => $this->number($value), 'unit' => $unit,
            'source' => $payload['dataSource']['platform'] ?? 'FITBIT',
        ];
    }

    /** @param array<string, mixed> $payload
     * @return array<string, mixed>
     */
    private function inner(array $payload): array
    {
        foreach ($payload as $key => $value) {
            if (! in_array($key, ['name', 'dataSource'], true) && is_array($value)) {
                return $value;
            }
        }

        return $payload;
    }

    private function number(mixed $value): ?float
    {
        return is_numeric($value) && is_finite((float) $value) ? (float) $value : null;
    }
}
