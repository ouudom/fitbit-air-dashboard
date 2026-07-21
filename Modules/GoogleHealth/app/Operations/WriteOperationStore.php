<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\Operations;

use Illuminate\Support\Str;
use Modules\GoogleHealth\Models\WriteOperation;

final class WriteOperationStore
{
    /** @param array<string, mixed> $request */
    public function create(string $dataType, string $method, array $request): string
    {
        $id = (string) Str::uuid();
        $now = self::nowMs();
        WriteOperation::query()->create([
            'id' => $id,
            'data_type' => $dataType,
            'method' => $method,
            'status' => 'pending',
            'request' => $request,
            'created_at' => $now,
            'updated_at' => $now,
        ]);

        return $id;
    }

    /** @param array<string, mixed>|null $response */
    public function finish(string $id, string $status, ?array $response = null, ?string $error = null): void
    {
        WriteOperation::query()->whereKey($id)->update([
            'status' => $status,
            'response' => $response,
            'error' => $error,
            'updated_at' => self::nowMs(),
        ]);
    }

    private static function nowMs(): int
    {
        return (int) floor(microtime(true) * 1000);
    }
}
