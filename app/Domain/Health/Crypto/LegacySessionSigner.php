<?php

declare(strict_types=1);

namespace App\Domain\Health\Crypto;

final class LegacySessionSigner
{
    public function create(string $userId, int $maxAgeSeconds = 2_592_000): string
    {
        $expires = time() + $maxAgeSeconds;
        $payload = "{$userId}.{$expires}";

        return $payload.'.'.$this->signature($payload);
    }

    public function verify(?string $value): ?string
    {
        if ($value === null || $value === '') {
            return null;
        }

        $parts = explode('.', $value);
        if (count($parts) < 3) {
            return null;
        }

        [$userId, $expires, $signature] = $parts;
        if ($userId === '' || ! ctype_digit($expires) || (int) $expires < time()) {
            return null;
        }

        $expected = $this->signature("{$userId}.{$expires}");

        return hash_equals($expected, $signature) ? $userId : null;
    }

    private function signature(string $payload): string
    {
        $binary = hash_hmac('sha256', $payload, (string) config('lifestats.legacy_session_secret'), true);

        return rtrim(strtr(base64_encode($binary), '+/', '-_'), '=');
    }
}
