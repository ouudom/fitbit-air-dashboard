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

    public function foodLogs(?string $date = null): array
    {
        $query = $this->database->table('food_logs');
        if ($date !== null) {
            $query->where('date', $date);
        }

        return $this->rows($query->orderByDesc('date')->orderByDesc('created_at')->get()->all());
    }

    public function meta(string $key): ?string
    {
        $value = $this->database->table('meta')->where('key', $key)->value('value');

        return $value === null ? null : (string) $value;
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
}
