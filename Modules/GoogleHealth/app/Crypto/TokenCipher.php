<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\Crypto;

use Illuminate\Contracts\Encryption\DecryptException;
use Illuminate\Contracts\Encryption\Encrypter;
use RuntimeException;

final readonly class TokenCipher
{
    public function __construct(private Encrypter $encrypter) {}

    public function encrypt(?string $value): ?string
    {
        if ($value === null || $value === '') {
            return $value;
        }

        return config('google-health.legacy.token_cipher', 'legacy') === 'legacy'
            ? $this->encryptLegacy($value)
            : $this->encrypter->encryptString($value);
    }

    public function decrypt(?string $value): ?string
    {
        if ($value === null || $value === '') {
            return $value;
        }

        if (str_starts_with($value, 'enc:v1:')) {
            return $this->decryptLegacy($value);
        }

        try {
            return $this->encrypter->decryptString($value);
        } catch (DecryptException) {
            // Pre-migration databases may contain plaintext tokens.
            return $value;
        }
    }

    public function needsMigration(?string $value): bool
    {
        if ($value === null || $value === '') {
            return false;
        }

        if (str_starts_with($value, 'enc:v1:')) {
            return config('google-health.legacy.token_cipher', 'legacy') !== 'legacy';
        }

        try {
            $this->encrypter->decryptString($value);

            return false;
        } catch (DecryptException) {
            return true;
        }
    }

    private function decryptLegacy(string $value): string
    {
        $encoded = substr($value, 7);
        $encoded .= str_repeat('=', (4 - strlen($encoded) % 4) % 4);
        $raw = base64_decode(strtr($encoded, '-_', '+/'), true);

        if ($raw === false || strlen($raw) < 29) {
            throw new RuntimeException('Invalid legacy token payload.');
        }

        $secret = (string) (config('google-health.legacy.encryption_key') ?: config('google-health.legacy.session_secret'));
        $key = hash('sha256', $secret, true);
        $plain = openssl_decrypt(
            substr($raw, 28),
            'aes-256-gcm',
            $key,
            OPENSSL_RAW_DATA,
            substr($raw, 0, 12),
            substr($raw, 12, 16),
        );

        if ($plain === false) {
            throw new RuntimeException('Unable to decrypt legacy token. Check TOKEN_ENCRYPTION_KEY.');
        }

        return $plain;
    }

    private function encryptLegacy(string $value): string
    {
        $secret = (string) (config('google-health.legacy.encryption_key') ?: config('google-health.legacy.session_secret'));
        $iv = random_bytes(12);
        $tag = '';
        $body = openssl_encrypt($value, 'aes-256-gcm', hash('sha256', $secret, true), OPENSSL_RAW_DATA, $iv, $tag);
        if ($body === false) {
            throw new RuntimeException('Unable to encrypt token.');
        }

        return 'enc:v1:'.rtrim(strtr(base64_encode($iv.$tag.$body), '+/', '-_'), '=');
    }
}
