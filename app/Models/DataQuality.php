<?php

declare(strict_types=1);

namespace App\Models;

final class DataQuality extends LegacyModel
{
    protected $table = 'data_quality';

    public $incrementing = false;

    protected $primaryKey = null;

    protected $casts = ['coverage' => 'float', 'updated_at' => 'integer'];
}
