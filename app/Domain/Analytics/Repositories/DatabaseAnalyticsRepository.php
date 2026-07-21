<?php

declare(strict_types=1);

namespace App\Domain\Analytics\Repositories;

use App\Domain\Analytics\Contracts\AnalyticsRepository;
use Illuminate\Database\ConnectionInterface;
use stdClass;

final class DatabaseAnalyticsRepository implements AnalyticsRepository
{
    public function __construct(private readonly ConnectionInterface $database) {}

    public function healthRecords(string $dataType, int $limit = 100): array
    {
        return $this->rows($this->database->table('health_records')
            ->where('data_type', $dataType)
            ->orderByRaw('date DESC NULLS LAST')
            ->orderByRaw('start_time DESC NULLS LAST')
            ->limit($limit)->get()->all());
    }

    public function dailyMetric(string $metric, int $days): array
    {
        return array_reverse($this->rows($this->database->table('daily_metrics')
            ->select(['date', 'value'])->where('metric', $metric)
            ->orderByDesc('date')->limit($days)->get()->all()));
    }

    public function exercises(int $limit): array
    {
        return $this->rows($this->database->table('exercises')->orderByDesc('start_time')->limit($limit)->get()->all());
    }

    public function healthCoverage(): array
    {
        return $this->rows($this->database->table('health_records')
            ->selectRaw('data_type, count(*)::int AS count, max(coalesce(date, start_time)) AS latest')
            ->groupBy('data_type')->orderBy('data_type')->get()->all());
    }

    public function syncStates(): array
    {
        return $this->rows($this->database->table('sync_state')->orderBy('data_type')->get()->all());
    }

    public function foodLogs(?string $date = null): array
    {
        $query = $this->database->table('food_logs');
        if ($date !== null) {
            $query->where('date', $date);
        }

        return $this->rows($query->orderByDesc('date')->orderByDesc('created_at')->get()->all());
    }

    public function journal(?string $from = null, ?string $to = null): array
    {
        $query = $this->database->table('journal_entries');
        if ($from !== null && $to !== null) {
            $query->whereBetween('date', [$from, $to]);
        }

        return $this->rows($query->orderByDesc('date')->orderByDesc('occurred_at')->get()->all());
    }

    public function strengthSessions(int $limit = 50): array
    {
        $sessions = $this->rows($this->database->table('strength_sessions')
            ->orderByDesc('date')->orderByDesc('start_time')->limit($limit)->get()->all());
        $sets = $this->rows($this->database->table('strength_sets')->get()->all());

        foreach ($sessions as &$session) {
            $session['sets'] = array_values(array_filter($sets, fn (array $set): bool => $set['sessionId'] === $session['id']));
        }

        return $sessions;
    }

    public function scores(string $type, int $days): array
    {
        return $this->rows($this->database->table('daily_scores')->where('score_type', $type)
            ->orderByDesc('date')->limit($days)->get()->all());
    }

    public function quality(string $date): array
    {
        return $this->rows($this->database->table('data_quality')->where('date', $date)->orderBy('data_type')->get()->all());
    }

    public function timeline(string $date): array
    {
        return $this->rows($this->database->table('timeline_events')->where('date', $date)->orderBy('start_time')->get()->all());
    }

    public function meta(string $key): ?string
    {
        $value = $this->database->table('meta')->where('key', $key)->value('value');

        return $value === null ? null : (string) $value;
    }

    public function saveScores(array $scores): void
    {
        foreach ($scores as $score) {
            $row = $this->snake($score, ['inputs', 'explanation']);
            $this->database->table('daily_scores')->upsert(
                [$row], ['date', 'score_type', 'model_version'],
                ['value', 'confidence', 'state', 'inputs', 'explanation', 'updated_at'],
            );
        }
    }

    public function saveQuality(array $quality): void
    {
        $this->database->table('data_quality')->upsert(
            [$this->snake($quality)], ['date', 'data_type'], ['status', 'coverage', 'reason', 'updated_at'],
        );
    }

    /** @param list<stdClass|array<string, mixed>> $rows
     * @return list<array<string, mixed>>
     */
    private function rows(array $rows): array
    {
        return array_map(function (stdClass|array $row): array {
            $values = (array) $row;
            $normalized = [];
            foreach ($values as $key => $value) {
                $name = preg_replace_callback('/_([a-z])/', static fn (array $m): string => strtoupper($m[1]), (string) $key);
                if (in_array($key, ['payload', 'raw', 'inputs', 'explanation', 'citations'], true) && is_string($value)) {
                    $value = json_decode($value, true, 512, JSON_THROW_ON_ERROR);
                }
                $normalized[$name] = $value;
            }

            return $normalized;
        }, $rows);
    }

    /** @param array<string, mixed> $values
     * @param  list<string>  $jsonKeys
     * @return array<string, mixed>
     */
    private function snake(array $values, array $jsonKeys = []): array
    {
        $row = [];
        foreach ($values as $key => $value) {
            $name = strtolower((string) preg_replace('/(?<!^)[A-Z]/', '_$0', $key));
            $row[$name] = in_array($key, $jsonKeys, true) ? json_encode($value, JSON_THROW_ON_ERROR) : $value;
        }

        return $row;
    }
}
