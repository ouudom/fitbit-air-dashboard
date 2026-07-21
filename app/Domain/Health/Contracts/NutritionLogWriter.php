<?php

declare(strict_types=1);

namespace App\Domain\Health\Contracts;

interface NutritionLogWriter
{
    /**
     * @param array{
     *     date:string,
     *     meal:string,
     *     name:string,
     *     calories?:float|int|string|null,
     *     proteinG?:float|int|string|null,
     *     carbsG?:float|int|string|null,
     *     fatG?:float|int|string|null,
     *     notes?:string|null
     * } $food
     */
    public function create(array $food): ?string;

    public function delete(string $remoteReference): void;
}
