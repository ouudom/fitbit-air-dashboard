<?php

declare(strict_types=1);

namespace App\Models;

final class HealthRecord extends LegacyModel
{
    protected $table = 'health_records';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['numeric_value' => 'float', 'payload' => 'array', 'updated_at' => 'integer'];
}
