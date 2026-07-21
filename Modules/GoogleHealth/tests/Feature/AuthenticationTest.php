<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Tests\Support\ConfiguresFeatureTest;
use Tests\TestCase;

final class AuthenticationTest extends TestCase
{
    use ConfiguresFeatureTest;
    use RefreshDatabase;

    public function test_google_redirect_stores_state_and_builds_expected_authorization_url(): void
    {
        config()->set('google-health.oauth.client_id', 'client-id');
        config()->set('google-health.oauth.redirect_uri', 'http://localhost/api/auth/callback');
        config()->set('google-health.oauth.scopes', 'scope-one scope-two');

        $response = $this->get(route('auth.google.redirect'));

        $response->assertRedirect();
        $location = (string) $response->headers->get('Location');
        parse_str((string) parse_url($location, PHP_URL_QUERY), $query);

        $this->assertSame('https', parse_url($location, PHP_URL_SCHEME));
        $this->assertSame('accounts.google.com', parse_url($location, PHP_URL_HOST));
        $this->assertSame('client-id', $query['client_id']);
        $this->assertSame('http://localhost/api/auth/callback', $query['redirect_uri']);
        $this->assertSame('scope-one scope-two', $query['scope']);
        $this->assertNotEmpty($query['state']);
        $this->assertSame($query['state'], session('oauth_state'));
    }

    public function test_callback_rejects_missing_or_mismatched_state_without_http_requests(): void
    {
        Http::fake();

        $this->withSession(['oauth_state' => 'expected'])
            ->get(route('auth.google.callback', ['state' => 'wrong', 'code' => 'code']))
            ->assertStatus(400)
            ->assertSeeText('Invalid OAuth state');

        Http::assertNothingSent();
        $this->assertFalse(session()->has('oauth_state'));
    }

    public function test_callback_exchanges_code_binds_user_and_authenticates_session(): void
    {
        config()->set('google-health.oauth.client_id', 'client-id');
        config()->set('google-health.oauth.client_secret', 'client-secret');
        config()->set('google-health.oauth.redirect_uri', 'http://localhost/api/auth/callback');

        Http::fake([
            'https://oauth2.googleapis.com/token' => Http::response([
                'access_token' => 'access-token',
                'refresh_token' => 'refresh-token',
                'expires_in' => 3600,
                'scope' => 'health',
            ]),
            'https://health.googleapis.com/v4/users/me/identity' => Http::response([
                'healthUserId' => 'health-user-1',
            ]),
        ]);

        $this->withSession(['oauth_state' => 'valid-state'])
            ->get(route('auth.google.callback', ['state' => 'valid-state', 'code' => 'auth-code']))
            ->assertRedirect(route('dashboard'))
            ->assertSessionHas('health_user_id', 'health-user-1');

        $this->assertSame('health-user-1', DB::table('meta')->where('key', 'healthUserId')->value('value'));
        $this->assertDatabaseHas('tokens', ['id' => 1, 'scope' => 'health']);
        $this->assertNotSame('access-token', DB::table('tokens')->where('id', 1)->value('access_token'));

        Http::assertSentCount(2);
    }

    public function test_callback_refuses_identity_different_from_bound_user(): void
    {
        DB::table('meta')->insert(['key' => 'healthUserId', 'value' => 'original-user']);
        Http::fake([
            'https://oauth2.googleapis.com/token' => Http::response([
                'access_token' => 'access-token', 'refresh_token' => 'refresh-token', 'expires_in' => 3600,
            ]),
            'https://health.googleapis.com/v4/users/me/identity' => Http::response([
                'healthUserId' => 'different-user',
            ]),
        ]);

        $this->withSession(['oauth_state' => 'valid-state'])
            ->get(route('auth.google.callback', ['state' => 'valid-state', 'code' => 'auth-code']))
            ->assertForbidden();

        $this->assertSame('original-user', DB::table('meta')->where('key', 'healthUserId')->value('value'));
        $this->assertDatabaseMissing('tokens', ['id' => 1]);
    }
}
