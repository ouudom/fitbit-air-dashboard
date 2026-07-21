<?php

declare(strict_types=1);

namespace App\Models;

final class FoodLog extends LegacyModel
{
    protected $table = 'food_logs';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['calories' => 'float', 'protein_g' => 'float', 'carbs_g' => 'float', 'fat_g' => 'float', 'created_at' => 'integer', 'updated_at' => 'integer'];
}
