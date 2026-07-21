<?php

declare(strict_types=1);

namespace Tests\Unit\Domain\Health;

use App\Domain\Health\Crypto\LegacySessionSigner;
use Tests\TestCase;

final class LegacySessionSignerTest extends TestCase
{
    public function test_it_creates_and_verifies_node_compatible_session_values(): void
    {
        config()->set('lifestats.legacy_session_secret', 'session-secret');
        $signer = new LegacySessionSigner;
        $value = $signer->create('health-user', 60);

        [$user, $expires, $signature] = explode('.', $value);
        $expected = rtrim(strtr(base64_encode(hash_hmac('sha256', "{$user}.{$expires}", 'session-secret', true)), '+/', '-_'), '=');

        $this->assertSame($expected, $signature);
        $this->assertSame('health-user', $signer->verify($value));
        $this->assertNull($signer->verify($value.'tampered'));
    }

    public function test_it_rejects_expired_or_malformed_values(): void
    {
        config()->set('lifestats.legacy_session_secret', 'session-secret');
        $signer = new LegacySessionSigner;

        $this->assertNull($signer->verify($signer->create('health-user', -1)));
        $this->assertNull($signer->verify('invalid'));
        $this->assertNull($signer->verify(null));
    }
}
