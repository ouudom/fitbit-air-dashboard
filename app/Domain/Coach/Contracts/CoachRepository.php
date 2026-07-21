<?php

declare(strict_types=1);

namespace App\Domain\Coach\Contracts;

interface CoachRepository
{
    /** @return list<array<string, mixed>> */
    public function messages(string $threadId, int $limit = 30): array;

    /** @param list<array<string, mixed>> $citations */
    public function saveMessage(string $threadId, string $role, string $content, array $citations = []): array;
}
