<?php

declare(strict_types=1);

namespace App\Models;

final class DailyScore extends LegacyModel
{
    protected $table = 'daily_scores';

    public $incrementing = false;

    protected $primaryKey = null;

    protected $casts = ['value' => 'float', 'inputs' => 'array', 'explanation' => 'array', 'updated_at' => 'integer'];
}
