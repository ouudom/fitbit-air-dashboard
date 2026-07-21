<?php

declare(strict_types=1);

namespace App\Domain\Health\Sync;

final class HealthPayloadMapper
{
    /** @param array<string, mixed> $point */
    public function dateOf(array $point): ?string
    {
        $payload = $this->payloadOf($point);
        $date = data_get($payload, 'civilStartTime.date')
            ?? data_get($payload, 'interval.civilStartTime.date')
            ?? data_get($payload, 'sampleTime.civilTime.date')
            ?? data_get($payload, 'date');

        if (is_array($date) && isset($date['year'], $date['month'], $date['day'])) {
            return sprintf('%04d-%02d-%02d', $date['year'], $date['month'], $date['day']);
        }

        $time = $this->timeOf($point);

        return $time === null ? null : substr($time, 0, 10);
    }

    /** @param array<string, mixed> $point */
    public function timeOf(array $point): ?string
    {
        $payload = $this->payloadOf($point);
        $value = data_get($payload, 'interval.startTime')
            ?? data_get($payload, 'sampleTime.physicalTime')
            ?? data_get($payload, 'startTime')
            ?? data_get($payload, 'session.startTime');

        return is_string($value) ? $value : null;
    }

    /** @param array<string, mixed> $point */
    public function numericOf(array $point): ?float
    {
        $payload = $this->payloadOf($point);
        foreach (['value', 'count', 'average', 'mean', 'bpm', 'beatsPerMinute', 'breathsPerMinute', 'percentage', 'millimeters', 'millis', 'averageHeartRateVariabilityMilliseconds', 'dailyAverageHeartRateVariabilityMilliseconds'] as $key) {
            $number = $this->number($payload[$key] ?? null);
            if ($number !== null) {
                return $number;
            }
        }

        return null;
    }

    /** @param array<string, mixed> $point */
    public function idOf(string $type, array $point): string
    {
        $name = $point['name'] ?? null;
        if (is_string($name) && ! str_ends_with($name, '/')) {
            return "{$type}:{$name}";
        }

        $fallback = substr((string) json_encode($point, JSON_UNESCAPED_SLASHES), 0, 200);

        return "{$type}:".($name ?? '').':'.($this->timeOf($point) ?? $this->dateOf($point) ?? $fallback);
    }

    public function durationSeconds(mixed $value): ?int
    {
        if ($value === null) {
            return null;
        }
        if (is_int($value) || is_float($value)) {
            return (int) round($value);
        }

        return preg_match('/([\d.]+)s/', (string) $value, $matches) ? (int) round((float) $matches[1]) : null;
    }

    public function number(mixed $value): ?float
    {
        if ($value === null) {
            return null;
        }
        if (is_array($value)) {
            foreach (['countSum', 'sum', 'total', 'average', 'avg', 'value', 'bpm', 'beatsPerMinute', 'percentage', 'millimeters', 'millis'] as $key) {
                if (array_key_exists($key, $value)) {
                    return $this->number($value[$key]);
                }
            }
        }
        if (is_numeric($value)) {
            $number = (float) $value;

            return is_finite($number) ? $number : null;
        }

        return null;
    }

    /** @param array<string, mixed> $point @return array<string, mixed> */
    private function payloadOf(array $point): array
    {
        foreach ($point as $key => $value) {
            if (! in_array($key, ['name', 'dataSource'], true) && is_array($value) && $value !== []) {
                return $value;
            }
        }

        return $point;
    }
}
