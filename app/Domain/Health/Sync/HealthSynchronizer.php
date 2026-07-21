<?php

declare(strict_types=1);

namespace App\Domain\Health\Sync;

use App\Domain\Health\Api\GoogleHealthClient;
use DateTimeImmutable;
use DateTimeInterface;
use Illuminate\Support\Str;
use InvalidArgumentException;
use Throwable;

final readonly class HealthSynchronizer
{
    /** @var list<string> */
    public const ROLLUP_METRICS = ['steps', 'distance', 'active-zone-minutes', 'active-minutes', 'total-calories', 'active-energy-burned', 'altitude', 'calories-in-heart-rate-zone', 'floors', 'run-vo2-max', 'sedentary-period', 'swim-lengths-data', 'time-in-heart-rate-zone'];

    /** @var list<string> */
    public const RECORD_TYPES = ['activity-level', 'blood-glucose', 'body-fat', 'core-body-temperature', 'daily-heart-rate-variability', 'daily-heart-rate-zones', 'daily-oxygen-saturation', 'daily-respiratory-rate', 'daily-resting-heart-rate', 'daily-sleep-temperature-derivations', 'daily-vo2-max', 'electrocardiogram', 'heart-rate', 'heart-rate-variability', 'height', 'hydration-log', 'irregular-rhythm-notification', 'nutrition-log', 'oxygen-saturation', 'respiratory-rate-sleep-summary', 'run-vo2-max', 'sleep', 'vo2-max', 'weight', 'food', 'food-measurement-unit'];

    private const INTERVAL_TYPES = ['activity-level', 'active-energy-burned', 'active-minutes', 'active-zone-minutes', 'altitude', 'calories-in-heart-rate-zone', 'distance', 'floors', 'sedentary-period', 'steps', 'swim-lengths-data', 'time-in-heart-rate-zone'];

    private const SAMPLE_TYPES = ['blood-glucose', 'body-fat', 'core-body-temperature', 'heart-rate', 'heart-rate-variability', 'height', 'nutrition-log', 'oxygen-saturation', 'respiratory-rate-sleep-summary', 'weight', 'food'];

    private const UNFILTERABLE_TYPES = ['food', 'food-measurement-unit', 'hydration-log', 'nutrition-log'];

    private const HIGH_VOLUME_TYPES = ['activity-level', 'heart-rate', 'food', 'food-measurement-unit', 'hydration-log', 'nutrition-log'];

    public function __construct(
        private GoogleHealthClient $client,
        private HealthRepository $repository,
        private HealthPayloadMapper $mapper,
    ) {}

    /** @return array{days:int,metrics:array<string,int>,records:array<string,int>,exercises:int,errors:list<string>,startedAt:int,finishedAt:int} */
    public function run(?int $days = null, ?bool $full = null): array
    {
        $days ??= (int) config('lifestats.sync_days', 30);
        $full ??= (bool) config('lifestats.sync_raw_types', false);
        $end = new DateTimeImmutable;
        $start = $end->modify('-'.max(0, $days - 1).' days');
        $result = ['days' => $days, 'metrics' => [], 'records' => [], 'exercises' => 0, 'errors' => [], 'startedAt' => self::nowMs(), 'finishedAt' => 0];

        try {
            $identity = $this->client->identity();
            if (! empty($identity['healthUserId'])) {
                $this->repository->setMeta('healthUserId', (string) $identity['healthUserId']);
            }
        } catch (Throwable $error) {
            $result['errors'][] = 'identity: '.$error->getMessage();
        }

        foreach (self::ROLLUP_METRICS as $metric) {
            $this->syncMetric($metric, $start, $end, $result);
        }

        $types = $full ? self::RECORD_TYPES : array_values(array_diff(self::RECORD_TYPES, self::HIGH_VOLUME_TYPES));
        foreach (array_diff(self::RECORD_TYPES, $types) as $type) {
            $result['records'][$type] = 0;
            $this->repository->setSyncState($type, 'skipped', 0, 'Skipped in normal sync; use full sync for raw/high-volume records.');
        }
        foreach ($types as $type) {
            $this->syncRecordType($type, $start, $end, $result);
        }

        $this->syncExercises($start, $end, $result);
        $this->repository->setMeta('lastSync', self::nowMs());
        $result['finishedAt'] = self::nowMs();

        return $result;
    }

    public function syncDataType(string $type, int $days = 7): int
    {
        if (! in_array($type, self::RECORD_TYPES, true) && $type !== 'exercise') {
            throw new InvalidArgumentException("Unsupported data type: {$type}");
        }

        $end = new DateTimeImmutable;
        $start = $end->modify('-'.max(0, $days - 1).' days');
        $rows = $this->recordRows($type, $start, $end);
        $this->repository->saveHealthRecords($rows);
        $this->repository->setSyncState($type, 'complete', count($rows));

        return count($rows);
    }

    /** @param array<string, mixed> $result */
    private function syncMetric(string $metric, DateTimeInterface $start, DateTimeInterface $end, array &$result): void
    {
        $this->repository->setSyncState($metric, 'running');
        try {
            $rows = [];
            foreach ($this->client->dailyRollup($metric, $start, $end) as $point) {
                $date = data_get($point, 'civilStartTime.date');
                $camel = lcfirst(str_replace(' ', '', ucwords(str_replace('-', ' ', $metric))));
                $candidate = $point[$camel] ?? $point[$metric] ?? $this->firstNestedValueExceptDate($point);
                $value = $this->mapper->number($candidate);
                if (is_array($date) && isset($date['year'], $date['month'], $date['day']) && $value !== null) {
                    $rows[] = ['date' => sprintf('%04d-%02d-%02d', $date['year'], $date['month'], $date['day']), 'metric' => $metric, 'value' => $value, 'updated_at' => self::nowMs()];
                }
            }
            $this->repository->saveDailyMetrics($rows);
            $result['metrics'][$metric] = count($rows);
            $this->repository->setSyncState($metric, 'complete', count($rows));
        } catch (Throwable $error) {
            $result['metrics'][$metric] = 0;
            $result['errors'][] = "{$metric}: {$error->getMessage()}";
            $this->repository->setSyncState($metric, 'error', 0, $error->getMessage());
        }
    }

    /** @param array<string, mixed> $result */
    private function syncRecordType(string $type, DateTimeInterface $start, DateTimeInterface $end, array &$result): void
    {
        $this->repository->setSyncState($type, 'running');
        try {
            $rows = $this->recordRows($type, $start, $end);
            $this->repository->saveHealthRecords($rows);
            $result['records'][$type] = count($rows);
            $this->repository->setSyncState($type, 'complete', count($rows));
        } catch (Throwable $error) {
            $result['records'][$type] = 0;
            $result['errors'][] = "{$type}: {$error->getMessage()}";
            $this->repository->setSyncState($type, 'error', 0, $error->getMessage());
        }
    }

    /** @return list<array<string, mixed>> */
    private function recordRows(string $type, DateTimeInterface $start, DateTimeInterface $end): array
    {
        $rows = [];
        foreach ($this->client->listDataPoints($type, $this->filterFor($type, $start, $end)) as $point) {
            $rows[] = [
                'id' => $this->mapper->idOf($type, $point),
                'data_type' => $type,
                'start_time' => $this->mapper->timeOf($point),
                'end_time' => data_get($point, 'endTime') ?? data_get($point, 'interval.endTime'),
                'date' => $this->mapper->dateOf($point),
                'numeric_value' => $this->mapper->numericOf($point),
                'payload' => $point,
                'updated_at' => self::nowMs(),
            ];
        }

        return $rows;
    }

    /** @param array<string, mixed> $result */
    private function syncExercises(DateTimeInterface $start, DateTimeInterface $end, array &$result): void
    {
        $this->repository->setSyncState('exercise', 'running');
        try {
            $rows = [];
            foreach ($this->client->listDataPoints('exercise', $this->filterFor('exercise', $start, $end)) as $point) {
                $exercise = $point['exercise'] ?? [];
                $metrics = $exercise['metricsSummary'] ?? [];
                $name = isset($point['name']) ? basename((string) $point['name']) : '';
                $rows[] = [
                    'id' => $name !== '' ? $name : (string) Str::uuid(),
                    'type' => $exercise['exerciseType'] ?? null,
                    'display_name' => $exercise['displayName'] ?? null,
                    'start_time' => data_get($exercise, 'interval.startTime'),
                    'duration_s' => $this->mapper->durationSeconds($exercise['activeDuration'] ?? null),
                    'calories' => $this->mapper->number($metrics['caloriesKcal'] ?? null),
                    'distance_mm' => $this->mapper->number($metrics['distanceMillimiters'] ?? $metrics['distanceMillimeters'] ?? null),
                    'steps' => $this->integer($this->mapper->number($metrics['steps'] ?? null)),
                    'avg_hr' => $this->integer($this->mapper->number($metrics['averageHeartRateBeatsPerMinute'] ?? null)),
                    'raw' => $point,
                    'updated_at' => self::nowMs(),
                ];
            }
            $this->repository->saveExercises($rows);
            $result['exercises'] = count($rows);
            $this->repository->setSyncState('exercise', 'complete', count($rows));
        } catch (Throwable $error) {
            $result['errors'][] = 'exercise: '.$error->getMessage();
            $this->repository->setSyncState('exercise', 'error', 0, $error->getMessage());
        }
    }

    private function filterFor(string $type, DateTimeInterface $start, DateTimeInterface $end): ?string
    {
        $from = $start->format('Y-m-d');
        $to = DateTimeImmutable::createFromInterface($end)->modify('+1 day')->format('Y-m-d');
        $name = str_replace('-', '_', $type);
        if (in_array($type, self::UNFILTERABLE_TYPES, true)) {
            return null;
        }
        if (str_starts_with($type, 'daily-')) {
            return "{$name}.date >= \"{$from}\" AND {$name}.date < \"{$to}\"";
        }
        if (in_array($type, self::SAMPLE_TYPES, true)) {
            return "{$name}.sample_time.civil_time >= \"{$from}\" AND {$name}.sample_time.civil_time < \"{$to}\"";
        }
        if ($type === 'electrocardiogram') {
            return "electrocardiogram.interval.start_time >= \"{$from}T00:00:00Z\"";
        }
        if ($type === 'sleep') {
            return "sleep.interval.civil_end_time >= \"{$from}\" AND sleep.interval.civil_end_time < \"{$to}\"";
        }
        if ($type === 'exercise' || in_array($type, self::INTERVAL_TYPES, true)) {
            return "{$name}.interval.civil_start_time >= \"{$from}\" AND {$name}.interval.civil_start_time < \"{$to}\"";
        }

        return null;
    }

    /** @param array<string, mixed> $point */
    private function firstNestedValueExceptDate(array $point): mixed
    {
        foreach ($point as $value) {
            if (is_array($value) && ! array_key_exists('date', $value)) {
                return $value;
            }
        }

        return null;
    }

    private function integer(?float $value): ?int
    {
        return $value === null ? null : (int) $value;
    }

    private static function nowMs(): int
    {
        return (int) floor(microtime(true) * 1000);
    }
}
