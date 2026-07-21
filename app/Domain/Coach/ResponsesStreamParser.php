<?php

declare(strict_types=1);

namespace App\Domain\Coach;

use RuntimeException;

final class ResponsesStreamParser
{
    /** @return array<string, mixed> */
    public function parse(string $body): array
    {
        try {
            $decoded = json_decode($body, true, 512, JSON_THROW_ON_ERROR);
            if (is_array($decoded)) {
                return $decoded;
            }
        } catch (\JsonException) {
        }

        $completed = null;
        $providerError = null;
        $deltas = [];
        foreach (preg_split('/\r?\n\r?\n/', $body) ?: [] as $block) {
            $event = '';
            $data = [];
            foreach (preg_split('/\r?\n/', $block) ?: [] as $line) {
                if (str_starts_with($line, 'event:')) {
                    $event = trim(substr($line, 6));
                } elseif (str_starts_with($line, 'data:')) {
                    $data[] = ltrim(substr($line, 5));
                }
            }
            $raw = implode("\n", $data);
            if ($raw === '' || $raw === '[DONE]') {
                continue;
            }
            try {
                $parsed = json_decode($raw, true, 512, JSON_THROW_ON_ERROR);
            } catch (\JsonException) {
                continue;
            }
            $type = (string) ($parsed['type'] ?? $event);
            if ($type === 'response.completed' || $event === 'response.completed') {
                $completed = $parsed['response'] ?? $parsed;
            }
            if ($type === 'response.failed' || $type === 'error' || str_contains($event, 'error')) {
                $providerError = $parsed['error'] ?? $parsed;
            }
            if ($type === 'response.output_text.delta' && is_string($parsed['delta'] ?? null)) {
                $deltas[] = $parsed['delta'];
            }
        }
        if (is_array($completed)) {
            return $completed;
        }
        if (is_array($providerError)) {
            throw new RuntimeException((string) ($providerError['message'] ?? 'LLM provider stream failed.'));
        }
        if ($deltas !== []) {
            return ['output_text' => implode('', $deltas), 'output' => []];
        }

        throw new RuntimeException('LLM provider returned an unsupported event-stream response.');
    }
}
