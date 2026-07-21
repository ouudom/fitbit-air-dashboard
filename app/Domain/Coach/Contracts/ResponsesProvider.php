<?php

declare(strict_types=1);

namespace App\Domain\Coach\Contracts;

interface ResponsesProvider
{
    /** @param array<string, mixed> $request
     * @return array<string, mixed>
     */
    public function respond(array $request): array;
}
