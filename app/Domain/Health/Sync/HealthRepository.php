<?php

declare(strict_types=1);

namespace App\Domain\Health\Sync;

use App\Models\DailyMetric;
use App\Models\Exercise;
use App\Models\HealthRecord;
use App\Models\Meta;
use App\Models\SyncState;

final class HealthRepository
{
    /** @param list<array<string, mixed>> $rows */
    public function saveDailyMetrics(array $rows): void
    {
        foreach (array_chunk($rows, 500) as $chunk) {
            DailyMetric::query()->upsert($chunk, ['date', 'metric'], ['value', 'updated_at']);
        }
    }

    /** @param list<array<string, mixed>> $rows */
    public function saveHealthRecords(array $rows): void
    {
        foreach (array_chunk($rows, 500) as $chunk) {
            $encoded = array_map(static function (array $row): array {
                $row['payload'] = json_encode($row['payload'], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);

                return $row;
            }, $chunk);
            HealthRecord::query()->upsert($encoded, ['id'], ['data_type', 'start_time', 'end_time', 'date', 'numeric_value', 'payload', 'updated_at']);
        }
    }

    /** @param list<array<string, mixed>> $rows */
    public function saveExercises(array $rows): void
    {
        foreach (array_chunk($rows, 100) as $chunk) {
            $encoded = array_map(static function (array $row): array {
                $row['raw'] = json_encode($row['raw'], JSON_THROW_ON_ERROR | JSON_UNESCAPED_SLASHES);

                return $row;
            }, $chunk);
            Exercise::query()->upsert($encoded, ['id'], ['type', 'display_name', 'start_time', 'duration_s', 'calories', 'distance_mm', 'steps', 'avg_hr', 'raw', 'updated_at']);
        }
    }

    public function setMeta(string $key, string|int $value): void
    {
        Meta::query()->upsert([['key' => $key, 'value' => (string) $value]], ['key'], ['value']);
    }

    public function setSyncState(string $dataType, string $status, int $recordCount = 0, ?string $error = null): void
    {
        $now = self::nowMs();
        SyncState::query()->upsert([[
            'data_type' => $dataType,
            'status' => $status,
            'record_count' => $recordCount,
            'error' => $error,
            'last_synced_at' => $status === 'complete' ? $now : null,
            'updated_at' => $now,
        ]], ['data_type'], ['status', 'record_count', 'error', 'last_synced_at', 'updated_at']);
    }

    private static function nowMs(): int
    {
        return (int) floor(microtime(true) * 1000);
    }
}
