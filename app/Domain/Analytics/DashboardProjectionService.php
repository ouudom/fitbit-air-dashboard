<?php

declare(strict_types=1);

namespace App\Domain\Analytics;

use App\Domain\Analytics\Contracts\AnalyticsRepository;

final class DashboardProjectionService
{
    private const SCORE_TYPES = ['recovery', 'sleep', 'strain', 'stress', 'energy'];

    public function __construct(
        private readonly AnalyticsRepository $repository,
        private readonly ScoringService $scoring,
        private readonly HealthDataService $health,
        private readonly InsightsService $insights,
    ) {}

    /** @return array<string, mixed> */
    public function today(): array
    {
        $lastSync = $this->repository->meta('lastSync');

        return [
            'activity' => $this->health->activity(30), 'sleep' => $this->health->sleep(1),
            'vitals' => $this->health->vitals(), 'lastSync' => $lastSync === null ? null : (int) $lastSync,
        ];
    }

    /** @return array<string, mixed> */
    public function day(string $date): array
    {
        $scores = $this->scoring->compute($date);
        $quality = $this->repository->quality($date);
        $timeline = array_map(static fn (array $item): array => [
            'id' => $item['id'], 'date' => $item['date'], 'type' => $item['eventType'], 'title' => $item['title'],
            'startTime' => $item['startTime'], 'endTime' => $item['endTime'], 'source' => $item['source'], 'detail' => null,
        ], $this->repository->timeline($date));
        $journal = $this->repository->journal($date, $date);
        $strength = $this->repository->strengthSessions(20);
        $food = $this->repository->foodLogs($date);
        $sleep = $this->health->sleep(90);
        $vitals = $this->health->vitals();
        $exercises = $this->repository->exercises(100);

        foreach ($sleep['sessions'] as $item) {
            if ($item['date'] === $date) {
                $timeline[] = ['id' => $item['id'], 'date' => $date, 'type' => 'sleep', 'title' => 'Sleep', 'startTime' => $item['startTime'], 'endTime' => $item['endTime'], 'source' => 'google-health', 'detail' => $item['minutesAsleep'] === null ? null : $item['minutesAsleep'].' min asleep'];
            }
        }
        foreach ($exercises as $item) {
            if (isset($item['startTime']) && substr((string) $item['startTime'], 0, 10) === $date) {
                $timeline[] = ['id' => $item['id'], 'date' => $date, 'type' => 'exercise', 'title' => $item['displayName'] ?? $item['type'] ?? 'Workout', 'startTime' => $item['startTime'], 'endTime' => null, 'source' => 'google-health', 'detail' => empty($item['durationS']) ? null : round($item['durationS'] / 60).' min'];
            }
        }
        foreach ($food as $item) {
            $timeline[] = ['id' => $item['id'], 'date' => $date, 'type' => 'nutrition', 'title' => $item['name'], 'startTime' => null, 'endTime' => null, 'source' => 'food-log', 'detail' => $item['calories'] === null ? $item['meal'] : $item['meal'].' · '.round($item['calories']).' kcal'];
        }
        foreach ($journal as $item) {
            $timeline[] = ['id' => $item['id'], 'date' => $date, 'type' => 'journal', 'title' => $item['habit'], 'startTime' => $item['occurredAt'], 'endTime' => null, 'source' => 'journal', 'detail' => $item['value']];
        }
        foreach ($strength as $item) {
            if ($item['date'] === $date) {
                $timeline[] = ['id' => $item['id'], 'date' => $date, 'type' => 'strength', 'title' => $item['title'], 'startTime' => $item['startTime'], 'endTime' => null, 'source' => 'strength', 'detail' => count($item['sets']).' sets'];
            }
        }
        usort($timeline, static fn (array $a, array $b): int => strcmp((string) ($a['startTime'] ?? ''), (string) ($b['startTime'] ?? '')));

        return [
            'date' => $date, 'scores' => $scores, 'quality' => $quality, 'timeline' => $timeline, 'signals' => $vitals,
            'sleep' => current(array_filter($sleep['sessions'], static fn (array $item): bool => $item['date'] === $date)) ?: null,
            'nutrition' => $this->insights->nutrition($date), 'strength' => $this->insights->strength(),
        ];
    }

    /** @return array{metric: string, range: int, points: list<array<string, mixed>>} */
    public function trend(string $metric = 'recovery', int $range = 30): array
    {
        $range = min(90, max(7, $range));
        if (in_array($metric, self::SCORE_TYPES, true)) {
            $this->scoring->computeRange($range);
            $points = array_map(static fn (array $row): array => ['date' => $row['date'], 'value' => $row['value'], 'confidence' => $row['confidence']], array_reverse($this->repository->scores($metric, $range)));
        } else {
            $points = $this->repository->dailyMetric($metric, $range);
        }

        return ['metric' => $metric, 'range' => $range, 'points' => $points];
    }
}
