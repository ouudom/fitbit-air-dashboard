<?php

declare(strict_types=1);

namespace App\Domain\Analytics;

use App\Domain\Analytics\Contracts\AnalyticsRepository;

final class InsightsService
{
    public function __construct(private readonly AnalyticsRepository $repository) {}

    /** @return list<array<string, mixed>> */
    public function journal(): array
    {
        $byDate = [];
        foreach ($this->repository->scores('recovery', 365) as $score) {
            $byDate[$score['date']] = $score['value'];
        }
        $groups = [];
        foreach ($this->repository->journal() as $entry) {
            $score = $byDate[$entry['date']] ?? null;
            if ($score === null) {
                continue;
            }
            $groups[$entry['habit']] ??= ['yes' => [], 'no' => []];
            $bucket = strtolower((string) $entry['value']) === 'yes' ? 'yes' : 'no';
            $groups[$entry['habit']][$bucket][] = (float) $score;
        }

        $insights = [];
        foreach ($groups as $habit => $values) {
            $ready = count($values['yes']) >= 5 && count($values['no']) >= 5;
            $effect = $ready ? array_sum($values['yes']) / count($values['yes']) - array_sum($values['no']) / count($values['no']) : null;
            $rounded = $effect === null ? null : floor($effect * 10 + .5) / 10;
            $insights[] = [
                'habit' => $habit, 'yes' => count($values['yes']), 'no' => count($values['no']), 'ready' => $ready,
                'effect' => $rounded, 'metric' => 'recovery',
                'note' => $ready
                    ? sprintf('Associated recovery difference: %s%s points. Correlation is not causation.', $effect >= 0 ? '+' : '', $rounded)
                    : 'Log at least 5 yes and 5 no days with Recovery scores.',
            ];
        }

        return $insights;
    }

    /** @return array{calories: float, proteinG: float, carbsG: float, fatG: float, entries: int} */
    public function nutrition(string $date): array
    {
        $summary = ['calories' => 0.0, 'proteinG' => 0.0, 'carbsG' => 0.0, 'fatG' => 0.0, 'entries' => 0];
        foreach ($this->repository->foodLogs($date) as $row) {
            foreach (['calories', 'proteinG', 'carbsG', 'fatG'] as $key) {
                $summary[$key] += (float) ($row[$key] ?? 0);
            }
            $summary['entries']++;
        }

        return $summary;
    }

    /** @return array{sessions: int, volumeKg: float} */
    public function strength(): array
    {
        $sessions = $this->repository->strengthSessions(30);
        $volume = 0.0;
        foreach ($sessions as $session) {
            foreach ($session['sets'] as $set) {
                $volume += (float) ($set['loadKg'] ?? 0) * (float) ($set['reps'] ?? 0);
            }
        }

        return ['sessions' => count($sessions), 'volumeKg' => $volume];
    }
}
