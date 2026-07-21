<?php

declare(strict_types=1);

namespace App\Models;

final class Goal extends LegacyModel
{
    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['target' => 'float', 'active' => 'boolean', 'created_at' => 'integer', 'updated_at' => 'integer'];
}
