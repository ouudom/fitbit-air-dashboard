<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\OAuth;

use Illuminate\Http\Client\Factory;
use RuntimeException;

final readonly class GoogleOAuthClient
{
    public function __construct(private Factory $http, private OAuthTokenStore $tokens) {}

    public function authorizationUrl(string $state): string
    {
        $query = http_build_query([
            'client_id' => config('google-health.oauth.client_id'),
            'redirect_uri' => config('google-health.oauth.redirect_uri'),
            'response_type' => 'code',
            'access_type' => 'offline',
            'prompt' => 'consent',
            'include_granted_scopes' => 'true',
            'scope' => trim((string) config('google-health.oauth.scopes')),
            'state' => $state,
        ], '', '&', PHP_QUERY_RFC3986);

        return config('google-health.oauth.auth_url').'?'.$query;
    }

    /** @return array<string, mixed> */
    public function exchangeCode(string $code): array
    {
        return $this->requestToken([
            'code' => $code,
            'client_id' => config('google-health.oauth.client_id'),
            'client_secret' => config('google-health.oauth.client_secret'),
            'redirect_uri' => config('google-health.oauth.redirect_uri'),
            'grant_type' => 'authorization_code',
        ]);
    }

    public function accessToken(): string
    {
        $token = $this->tokens->get();
        if (! $token || ! $token['access_token']) {
            throw new RuntimeException('NOT_AUTHENTICATED');
        }

        if (self::nowMs() < ($token['expiry'] ?? 0) - 60_000) {
            return $token['access_token'];
        }

        if (! $token['refresh_token']) {
            throw new RuntimeException('NOT_AUTHENTICATED');
        }

        $response = $this->requestToken([
            'refresh_token' => $token['refresh_token'],
            'client_id' => config('google-health.oauth.client_id'),
            'client_secret' => config('google-health.oauth.client_secret'),
            'grant_type' => 'refresh_token',
        ]);

        return (string) $response['access_token'];
    }

    public function authenticated(): bool
    {
        return (bool) ($this->tokens->get()['refresh_token'] ?? false);
    }

    /** @param array<string, mixed> $fields @return array<string, mixed> */
    private function requestToken(array $fields): array
    {
        $response = $this->http->asForm()->timeout(30)->post((string) config('google-health.oauth.token_url'), $fields);
        if (! $response->successful()) {
            throw new RuntimeException("Google token request failed: {$response->status()}");
        }

        $data = $response->json();
        if (! is_array($data) || empty($data['access_token'])) {
            throw new RuntimeException('Google token response did not include an access token.');
        }

        $this->tokens->save(
            (string) $data['access_token'],
            isset($data['refresh_token']) ? (string) $data['refresh_token'] : null,
            self::nowMs() + ((int) ($data['expires_in'] ?? 3600) * 1000),
            isset($data['scope']) ? (string) $data['scope'] : null,
        );

        return $data;
    }

    private static function nowMs(): int
    {
        return (int) floor(microtime(true) * 1000);
    }
}
