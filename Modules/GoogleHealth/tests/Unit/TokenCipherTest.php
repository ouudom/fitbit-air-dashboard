<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\Tests\Unit;

use Illuminate\Encryption\Encrypter;
use Modules\GoogleHealth\Crypto\TokenCipher;
use Tests\TestCase;

final class TokenCipherTest extends TestCase
{
    public function test_it_decrypts_node_compatible_legacy_aes_gcm_tokens(): void
    {
        config()->set('google-health.legacy.encryption_key', 'legacy-secret');
        $plain = 'google-access-token';
        $iv = hex2bin('000102030405060708090a0b');
        $tag = '';
        $body = openssl_encrypt($plain, 'aes-256-gcm', hash('sha256', 'legacy-secret', true), OPENSSL_RAW_DATA, $iv, $tag);
        $encoded = rtrim(strtr(base64_encode($iv.$tag.$body), '+/', '-_'), '=');
        $cipher = new TokenCipher(new Encrypter(random_bytes(32), 'AES-256-CBC'));

        $this->assertSame($plain, $cipher->decrypt('enc:v1:'.$encoded));
        $this->assertFalse($cipher->needsMigration('enc:v1:'.$encoded));
    }

    public function test_it_round_trips_legacy_tokens_for_rollback_compatibility(): void
    {
        config()->set('google-health.legacy.encryption_key', 'legacy-secret');
        config()->set('google-health.legacy.token_cipher', 'legacy');
        $cipher = new TokenCipher(new Encrypter(random_bytes(32), 'AES-256-CBC'));
        $encrypted = $cipher->encrypt('refresh-token');

        $this->assertNotSame('refresh-token', $encrypted);
        $this->assertStringStartsWith('enc:v1:', $encrypted);
        $this->assertSame('refresh-token', $cipher->decrypt($encrypted));
        $this->assertFalse($cipher->needsMigration($encrypted));
    }

    public function test_it_accepts_plaintext_for_one_time_migration(): void
    {
        $cipher = new TokenCipher(new Encrypter(random_bytes(32), 'AES-256-CBC'));

        $this->assertSame('old-plaintext', $cipher->decrypt('old-plaintext'));
        $this->assertTrue($cipher->needsMigration('old-plaintext'));
    }
}
