<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\OAuth;

use Modules\GoogleHealth\Crypto\TokenCipher;
use Modules\GoogleHealth\Models\Token;

final readonly class OAuthTokenStore
{
    public function __construct(private TokenCipher $cipher) {}

    /** @return array{access_token:?string,refresh_token:?string,expiry:?int,scope:?string}|null */
    public function get(): ?array
    {
        $row = Token::query()->find(1);
        if (! $row) {
            return null;
        }

        $access = $this->cipher->decrypt($row->access_token);
        $refresh = $this->cipher->decrypt($row->refresh_token);

        if ($this->cipher->needsMigration($row->access_token) || $this->cipher->needsMigration($row->refresh_token)) {
            Token::query()->whereKey(1)->update([
                'access_token' => $this->cipher->encrypt($access),
                'refresh_token' => $this->cipher->encrypt($refresh),
                'updated_at' => self::nowMs(),
            ]);
        }

        return [
            'access_token' => $access,
            'refresh_token' => $refresh,
            'expiry' => $row->expiry === null ? null : (int) $row->expiry,
            'scope' => $row->scope,
        ];
    }

    public function save(string $accessToken, ?string $refreshToken, int $expiry, ?string $scope): void
    {
        $oldRefresh = $refreshToken === null ? ($this->get()['refresh_token'] ?? null) : $refreshToken;
        Token::query()->upsert([[
            'id' => 1,
            'access_token' => $this->cipher->encrypt($accessToken),
            'refresh_token' => $this->cipher->encrypt($oldRefresh),
            'expiry' => $expiry,
            'scope' => $scope,
            'updated_at' => self::nowMs(),
        ]], ['id'], ['access_token', 'refresh_token', 'expiry', 'scope', 'updated_at']);
    }

    public function delete(): void
    {
        Token::query()->whereKey(1)->delete();
    }

    private static function nowMs(): int
    {
        return (int) floor(microtime(true) * 1000);
    }
}
