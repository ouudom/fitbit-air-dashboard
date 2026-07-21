<?php

declare(strict_types=1);

namespace App\Domain\Coach;

use App\Domain\Coach\Contracts\ResponsesProvider;
use Illuminate\Http\Client\Factory;
use RuntimeException;
use Throwable;

final class HttpResponsesProvider implements ResponsesProvider
{
    public function __construct(
        private readonly Factory $http,
        private readonly ResponsesStreamParser $parser,
        private readonly string $baseUrl,
        private readonly string $apiKey,
    ) {}

    public function respond(array $request): array
    {
        if ($this->apiKey === '') {
            throw new RuntimeException('LLM_API_KEY is not configured.');
        }

        $response = $this->http->withToken($this->apiKey)
            ->withHeaders(['Accept' => 'application/json, text/event-stream'])
            ->post(rtrim($this->baseUrl, '/').'/responses', $request);
        try {
            $parsed = $this->parser->parse($response->body());
        } catch (Throwable $error) {
            throw new RuntimeException("LLM provider {$response->status()}: {$error->getMessage()}", previous: $error);
        }
        if (! $response->successful()) {
            throw new RuntimeException("LLM provider {$response->status()}: ".($parsed['error']['message'] ?? 'request failed'));
        }

        return $parsed;
    }
}
