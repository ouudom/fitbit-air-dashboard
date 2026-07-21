<?php

declare(strict_types=1);

namespace App\Domain\Health\Api;

use App\Domain\Health\OAuth\GoogleOAuthClient;
use DateTimeImmutable;
use DateTimeInterface;
use Illuminate\Http\Client\Factory;
use Illuminate\Http\Client\Response;
use InvalidArgumentException;
use RuntimeException;

final readonly class GoogleHealthClient
{
    /** @var list<string> */
    public const WRITABLE_TYPES = ['body-fat', 'exercise', 'height', 'hydration-log', 'nutrition-log', 'sleep', 'weight'];

    public function __construct(private Factory $http, private GoogleOAuthClient $oauth) {}

    /** @return array<string, mixed> */
    public function identity(): array
    {
        return $this->request('GET', '/users/me/identity');
    }

    /** @return list<array<string, mixed>> */
    public function listDataPoints(string $type, ?string $filter = null, int $pageSize = 1000): array
    {
        $all = [];
        $page = null;

        do {
            $query = ['page_size' => in_array($type, ['sleep', 'exercise'], true) ? 25 : $pageSize];
            if ($filter !== null) {
                $query['filter'] = $filter;
            }
            if ($page !== null && $page !== '') {
                $query['page_token'] = $page;
            }

            $data = $this->request('GET', "/users/me/dataTypes/{$type}/dataPoints", query: $query);
            array_push($all, ...($data['dataPoints'] ?? []));
            $page = $data['nextPageToken'] ?? null;
        } while ($page);

        return $all;
    }

    /** @return list<array<string, mixed>> */
    public function dailyRollup(string $type, DateTimeInterface $start, DateTimeInterface $end): array
    {
        $all = [];
        $cursor = DateTimeImmutable::createFromInterface($start);
        $final = DateTimeImmutable::createFromInterface($end);

        while ($cursor <= $final) {
            $chunkEnd = $cursor->modify('+13 days');
            if ($chunkEnd > $final) {
                $chunkEnd = $final;
            }

            $data = $this->request('POST', "/users/me/dataTypes/{$type}/dataPoints:dailyRollUp", [
                'range' => ['start' => $this->civil($cursor, 0), 'end' => $this->civil($chunkEnd, 23, 59, 59)],
                'windowSizeDays' => 1,
            ]);
            array_push($all, ...($data['rollupDataPoints'] ?? []));
            $cursor = $chunkEnd->modify('+1 day');
        }

        return $all;
    }

    /** @param array<string, mixed> $dataPoint @return array<string, mixed> */
    public function createDataPoint(string $type, array $dataPoint): array
    {
        $this->assertWritable($type);

        return $this->request('POST', "/users/me/dataTypes/{$type}/dataPoints", $dataPoint);
    }

    /** @param array<string, mixed> $dataPoint @return array<string, mixed> */
    public function patchDataPoint(string $type, string $name, array $dataPoint, ?string $updateMask = null): array
    {
        $this->assertWritable($type);

        return $this->request('PATCH', '/'.ltrim($name, '/'), $dataPoint, $updateMask ? ['updateMask' => $updateMask] : []);
    }

    /** @param list<string> $names @return array<string, mixed> */
    public function deleteDataPoints(string $type, array $names): array
    {
        $this->assertWritable($type);

        return $this->request('POST', "/users/me/dataTypes/{$type}/dataPoints:batchDelete", ['names' => $names]);
    }

    /** @param array<string, mixed> $operation @return array<string, mixed> */
    public function waitForOperation(array $operation, int $maxAttempts = 8): array
    {
        if (empty($operation['name']) || ! empty($operation['done'])) {
            return $operation;
        }

        $current = $operation;
        for ($attempt = 0; $attempt < $maxAttempts; $attempt++) {
            usleep(min(500 * (2 ** $attempt), 4000) * 1000);
            $current = $this->request('GET', '/'.ltrim((string) $current['name'], '/'));
            if (! empty($current['done'])) {
                return $current;
            }
        }

        return $current;
    }

    /** @param array<string, mixed>|null $json @param array<string, mixed> $query @return array<string, mixed> */
    private function request(string $method, string $path, ?array $json = null, array $query = []): array
    {
        $url = rtrim((string) config('lifestats.google.health_url'), '/').$path;

        for ($attempt = 0; ; $attempt++) {
            $pending = $this->http
                ->withToken($this->oauth->accessToken())
                ->acceptJson()
                ->contentType('application/json')
                ->timeout(30);

            $options = [];
            if ($query !== []) {
                $options['query'] = $query;
            }
            if ($json !== null) {
                $options['json'] = $json;
            }

            $response = $pending->send($method, $url, $options);
            if ($this->isRetryable($response) && $attempt < 3) {
                sleep(2 ** $attempt);

                continue;
            }

            $data = $response->json();
            $data = is_array($data) ? $data : [];
            if (! $response->successful()) {
                throw new RuntimeException("Health API {$response->status()}: ".json_encode($data, JSON_UNESCAPED_SLASHES));
            }

            return $data;
        }
    }

    private function isRetryable(Response $response): bool
    {
        return $response->status() === 429 || $response->serverError();
    }

    /** @return array{date:array{year:int,month:int,day:int},time:array{hours:int,minutes:int,seconds:int,nanos:int}} */
    private function civil(DateTimeInterface $date, int $hour, int $minute = 0, int $second = 0): array
    {
        return [
            'date' => ['year' => (int) $date->format('Y'), 'month' => (int) $date->format('n'), 'day' => (int) $date->format('j')],
            'time' => ['hours' => $hour, 'minutes' => $minute, 'seconds' => $second, 'nanos' => 0],
        ];
    }

    private function assertWritable(string $type): void
    {
        if (! in_array($type, self::WRITABLE_TYPES, true)) {
            throw new InvalidArgumentException("Data type {$type} is not writable.");
        }
    }
}
