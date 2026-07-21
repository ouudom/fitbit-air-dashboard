<?php

declare(strict_types=1);

namespace App\Models;

final class DailyMetric extends LegacyModel
{
    protected $table = 'daily_metrics';

    public $incrementing = false;

    protected $primaryKey = null;

    protected $casts = ['value' => 'float', 'updated_at' => 'integer'];
}
