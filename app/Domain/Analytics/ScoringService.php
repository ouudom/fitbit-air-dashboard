<?php

declare(strict_types=1);

namespace App\Domain\Analytics;

use App\Domain\Analytics\Contracts\AnalyticsRepository;
use DateTimeImmutable;
use DateTimeZone;

final class ScoringService
{
    public const SCORE_VERSION = 'wellness-v1.0.0';

    public function __construct(private readonly AnalyticsRepository $repository) {}

    /** @return list<array<string, mixed>> */
    public function compute(?string $date = null): array
    {
        $date ??= gmdate('Y-m-d');
        $hrv = $this->signal('daily-heart-rate-variability', $date);
        $rhr = $this->signal('daily-resting-heart-rate', $date);
        $resp = $this->signal('daily-respiratory-rate', $date);
        $spo2 = $this->signal('daily-oxygen-saturation', $date);
        $temp = $this->signal('daily-sleep-temperature-derivations', $date);
        $sleep = $this->sleepSignals($date);
        $steps = $this->activitySignal('steps', $date);
        $azm = $this->activitySignal('active-zone-minutes', $date);
        $activeEnergy = $this->activitySignal('active-energy-burned', $date);

        $recoveryInputs = [
            ['hrv', 'HRV', $hrv, true, 'ms'],
            ['rhr', 'Resting heart rate', $rhr, false, 'bpm'],
            ['resp', 'Respiratory rate', $resp, false, '/min'],
            ['spo2', 'Blood oxygen', $spo2, true, '%'],
            ['temp', 'Temperature deviation', $temp, false, '°'],
        ];
        $recoveryValue = 50.0;
        $recoveryContributions = [];
        foreach ($recoveryInputs as [$key, $label, $signal, $higher, $unit]) {
            $robust = $this->robust($signal['today'], $signal['history'], $higher);
            $weight = in_array($key, ['hrv', 'rhr'], true) ? 1.5 : 1.0;
            if ($signal['today'] !== null) {
                $recoveryValue += $robust['z'] * 8 * $weight;
            }
            $recoveryContributions[] = $this->contribution($key, $label, $signal['today'], $robust['base'], $robust['z'] * $weight, $unit);
        }
        $recoveryPresent = count(array_filter($recoveryInputs, static fn (array $input): bool => $input[2]['today'] !== null));

        $sleepToday = $sleep['today'];
        $sleepMinutes = $sleepToday['minutes'] ?? null;
        $sleepHistory = array_values(array_filter(array_column($sleep['history'], 'minutes'), static fn (mixed $x): bool => $x !== null));
        $sleepBase = $this->median($sleepHistory);
        $durationScore = $sleepMinutes === null ? null : $this->clamp(100 - abs(480 - $sleepMinutes) / 3.5);
        $efficiency = $sleepMinutes !== null && ! empty($sleepToday['period']) ? $this->clamp($sleepMinutes / $sleepToday['period'] * 100) : null;
        $continuity = ($sleepToday['awake'] ?? null) !== null && ! empty($sleepToday['period']) ? $this->clamp(100 - $sleepToday['awake'] / $sleepToday['period'] * 100) : null;
        $sleepValue = $this->mean(array_values(array_filter([$durationScore, $efficiency, $continuity], static fn (mixed $x): bool => $x !== null)));

        $strainSteps = $this->robust($steps['today'], $steps['history']);
        $strainAzm = $this->robust($azm['today'], $azm['history']);
        $strainEnergy = $this->robust($activeEnergy['today'], $activeEnergy['history']);
        $strainPresent = count(array_filter([$steps['today'], $azm['today'], $activeEnergy['today']], static fn (mixed $x): bool => $x !== null));
        $strainValue = $strainPresent > 0 ? $this->clamp(45 + $strainSteps['z'] * 8 + $strainAzm['z'] * 13 + $strainEnergy['z'] * 9) : null;

        $stressPresent = count(array_filter([$rhr['today'], $hrv['today'], $steps['today']], static fn (mixed $x): bool => $x !== null));
        $stressValue = $stressPresent >= 2 ? $this->clamp(
            50 - $this->robust($hrv['today'], $hrv['history'])['z'] * 12
            + $this->robust($rhr['today'], $rhr['history'])['z'] * 12
            + max(0, $this->robust($steps['today'], $steps['history'])['z']) * 4,
        ) : null;
        $energyValue = $recoveryPresent >= 2 ? $this->clamp(
            ($this->clamp($recoveryValue) + ($sleepValue ?? 50) + (100 - ($strainValue ?? 50)) + (100 - ($stressValue ?? 50))) / 4,
        ) : null;

        $history = max(count($hrv['history']), count($rhr['history']), count($sleepHistory), count($steps['history']));
        $scores = [
            $this->score($date, 'recovery', $this->clamp($recoveryValue), $recoveryPresent, 5, $history, $recoveryContributions, 'Readiness from overnight signals versus your personal baseline.'),
            $this->score($date, 'sleep', $sleepValue, count(array_filter([$sleepMinutes, $efficiency, $continuity], static fn (mixed $x): bool => $x !== null)), 3, $history, [
                $this->contribution('duration', 'Sleep duration', $sleepMinutes, $sleepBase, $durationScore === null ? 0 : ($durationScore - 50) / 20, 'min'),
                $this->contribution('efficiency', 'Sleep efficiency', $efficiency, 85, $efficiency === null ? 0 : ($efficiency - 85) / 8, '%'),
                $this->contribution('continuity', 'Sleep continuity', $continuity, 90, $continuity === null ? 0 : ($continuity - 90) / 8, '%'),
            ], 'Sleep sufficiency, efficiency, and continuity.'),
            $this->score($date, 'strain', $strainValue, $strainPresent, 3, $history, [
                $this->contribution('steps', 'Steps', $steps['today'], $strainSteps['base'], $strainSteps['z'], 'steps'),
                $this->contribution('azm', 'Zone minutes', $azm['today'], $strainAzm['base'], $strainAzm['z'], 'min'),
                $this->contribution('energy', 'Active energy', $activeEnergy['today'], $strainEnergy['base'], $strainEnergy['z'], 'kcal'),
            ], 'Daily exertion relative to your normal activity.'),
            $this->score($date, 'stress', $stressValue, $stressPresent, 3, $history, [
                $this->contribution('hrv', 'HRV', $hrv['today'], $this->median($hrv['history']), $this->robust($hrv['today'], $hrv['history'])['z'], 'ms'),
                $this->contribution('rhr', 'Resting heart rate', $rhr['today'], $this->median($rhr['history']), -$this->robust($rhr['today'], $rhr['history'], false)['z'], 'bpm'),
                $this->contribution('movement', 'Movement', $steps['today'], $this->median($steps['history']), $this->robust($steps['today'], $steps['history'])['z'], 'steps'),
            ], 'Physiological load estimate; not a measure of mental health.'),
            $this->score($date, 'energy', $energyValue, count(array_filter([$recoveryPresent >= 2, $sleepValue !== null, $strainValue !== null, $stressValue !== null])), 4, $history, [], 'Recovery and sleep recharge; strain and physiological stress drain.'),
        ];

        $now = (int) floor(microtime(true) * 1000);
        $this->repository->saveScores(array_map(static fn (array $score): array => [
            'date' => $score['date'], 'scoreType' => $score['type'], 'modelVersion' => $score['modelVersion'],
            'value' => $score['value'], 'confidence' => $score['confidence'], 'state' => $score['state'],
            'inputs' => $score['contributions'], 'explanation' => ['summary' => $score['summary']], 'updatedAt' => $now,
        ], $scores));
        foreach ([['recovery', $recoveryPresent, 5], ['sleep', $sleepToday === null ? 0 : 1, 1], ['activity', $strainPresent, 3]] as [$type, $present, $total]) {
            $this->repository->saveQuality([
                'date' => $date, 'dataType' => $type,
                'status' => $present === $total ? 'good' : ($present > 0 ? 'partial' : 'missing'),
                'coverage' => $present / $total,
                'reason' => $present === $total ? null : 'Some source signals are unavailable.', 'updatedAt' => $now,
            ]);
        }

        return $scores;
    }

    public function computeRange(int $days = 30, ?DateTimeImmutable $now = null): int
    {
        $days = min(90, max(1, $days));
        $now ??= new DateTimeImmutable('now', new DateTimeZone('UTC'));
        for ($offset = $days - 1; $offset >= 0; $offset--) {
            $this->compute($now->modify("-$offset days")->format('Y-m-d'));
        }

        return $days;
    }

    /** @return array{today: float|null, history: list<float>} */
    private function signal(string $type, string $date): array
    {
        $points = [];
        foreach ($this->repository->healthRecords($type, 120) as $row) {
            $pointDate = $row['date'] ?? (isset($row['startTime']) ? substr((string) $row['startTime'], 0, 10) : '');
            $value = $this->recordValue($row);
            if ($pointDate !== '' && $value !== null) {
                $points[] = ['date' => $pointDate, 'value' => $value];
            }
        }
        $today = null;
        $history = [];
        $from = $this->dateMinus($date, 60);
        foreach ($points as $point) {
            if ($point['date'] === $date && $today === null) {
                $today = $point['value'];
            } elseif ($point['date'] < $date && $point['date'] >= $from) {
                $history[] = $point['value'];
            }
        }

        return compact('today', 'history');
    }

    /** @return array{today: array<string, mixed>|null, history: list<array<string, mixed>>} */
    private function sleepSignals(string $date): array
    {
        $sessions = [];
        foreach ($this->repository->healthRecords('sleep', 120) as $row) {
            $payload = $this->inner($row['payload'] ?? []);
            $summary = is_array($payload['summary'] ?? null) ? $payload['summary'] : [];
            $interval = is_array($payload['interval'] ?? null) ? $payload['interval'] : [];
            $start = $interval['startTime'] ?? $row['startTime'] ?? null;
            $sessionDate = $row['date'] ?? ($start === null ? '' : substr((string) $start, 0, 10));
            if ($sessionDate !== '') {
                $sessions[] = ['date' => $sessionDate, 'minutes' => $this->number($summary['minutesAsleep'] ?? null), 'period' => $this->number($summary['minutesInSleepPeriod'] ?? null), 'awake' => $this->number($summary['minutesAwake'] ?? null), 'start' => $start];
            }
        }
        $today = null;
        $history = [];
        $from = $this->dateMinus($date, 60);
        foreach ($sessions as $session) {
            if ($session['date'] === $date && $today === null) {
                $today = $session;
            } elseif ($session['date'] < $date && $session['date'] >= $from && $session['minutes'] !== null) {
                $history[] = $session;
            }
        }

        return compact('today', 'history');
    }

    /** @return array{today: float|null, history: list<float>} */
    private function activitySignal(string $metric, string $date): array
    {
        $today = null;
        $history = [];
        $from = $this->dateMinus($date, 60);
        foreach ($this->repository->dailyMetric($metric, 90) as $row) {
            if ($row['date'] === $date) {
                $today ??= $this->number($row['value']);
            } elseif ($row['date'] < $date && $row['date'] >= $from && $row['value'] !== null) {
                $history[] = (float) $row['value'];
            }
        }

        return compact('today', 'history');
    }

    /** @param array<string, mixed> $row */
    private function recordValue(array $row): ?float
    {
        if (($row['numericValue'] ?? null) !== null) {
            return $this->number($row['numericValue']);
        }
        $payload = $this->inner($row['payload'] ?? []);
        foreach (['averageHeartRateVariabilityMilliseconds', 'dailyAverageHeartRateVariabilityMilliseconds', 'breathsPerMinute', 'beatsPerMinute', 'percentage', 'value', 'average', 'variation'] as $key) {
            if (array_key_exists($key, $payload) && $payload[$key] !== null) {
                return $this->number($payload[$key]);
            }
        }

        return null;
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

    /** @param list<float|int> $values
     * @return array{base: float|null, z: float}
     */
    private function robust(?float $value, array $values, bool $higher = true): array
    {
        $base = $this->median($values);
        if ($value === null || $base === null) {
            return ['base' => $base, 'z' => 0.0];
        }
        $mad = $this->median(array_map(static fn (float|int $x): float => abs($x - $base), $values)) ?? 0;
        $scale = max($mad * 1.4826, abs($base) * 0.05, 1);
        $z = $this->clamp(($value - $base) / $scale, -2.5, 2.5) * ($higher ? 1 : -1);

        return ['base' => $base, 'z' => $z];
    }

    /** @param list<float|int> $values */
    private function median(array $values): ?float
    {
        if ($values === []) {
            return null;
        }
        sort($values, SORT_NUMERIC);
        $middle = intdiv(count($values), 2);

        return count($values) % 2 ? (float) $values[$middle] : ((float) $values[$middle - 1] + (float) $values[$middle]) / 2;
    }

    /** @param list<float|int> $values */
    private function mean(array $values): ?float
    {
        return $values === [] ? null : array_sum($values) / count($values);
    }

    /** @return array<string, mixed> */
    private function contribution(string $key, string $label, ?float $value, ?float $baseline, float $impact, string $unit): array
    {
        return ['key' => $key, 'label' => $label, 'value' => $value, 'baseline' => $baseline, 'impact' => (int) $this->javascriptRound($impact), 'unit' => $unit,
            'status' => $value === null ? 'missing' : ($impact > .25 ? 'positive' : ($impact < -.25 ? 'negative' : 'neutral'))];
    }

    /** @param list<array<string, mixed>> $contributions
     * @return array<string, mixed>
     */
    private function score(string $date, string $type, ?float $value, int $present, int $total, int $history, array $contributions, string $summary): array
    {
        $state = $present < (int) ceil($total * .5) ? 'insufficient' : ($history >= 21 ? 'ready' : 'calibrating');
        $confidence = $present === $total && $history >= 28 ? 'high' : ($present >= (int) ceil($total * .6) && $history >= 14 ? 'medium' : 'low');

        return ['date' => $date, 'type' => $type, 'value' => $state === 'ready' && $value !== null ? (int) $this->javascriptRound($value) : null,
            'confidence' => $confidence, 'state' => $state, 'modelVersion' => self::SCORE_VERSION, 'contributions' => $contributions, 'summary' => $summary];
    }

    private function number(mixed $value): ?float
    {
        return is_numeric($value) && is_finite((float) $value) ? (float) $value : null;
    }

    private function clamp(float $number, float $min = 0, float $max = 100): float
    {
        return max($min, min($max, $number));
    }

    private function javascriptRound(float $number): float
    {
        return floor($number + .5);
    }

    private function dateMinus(string $date, int $days): string
    {
        return (new DateTimeImmutable($date.' 12:00:00', new DateTimeZone('UTC')))->modify("-$days days")->format('Y-m-d');
    }
}
