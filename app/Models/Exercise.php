<?php

declare(strict_types=1);

namespace App\Models;

final class Exercise extends LegacyModel
{
    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['duration_s' => 'integer', 'calories' => 'float', 'distance_mm' => 'float', 'steps' => 'integer', 'avg_hr' => 'integer', 'raw' => 'array', 'updated_at' => 'integer'];
}
