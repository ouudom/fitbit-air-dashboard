<?php

declare(strict_types=1);

namespace App\Models;

final class Token extends LegacyModel
{
    protected $table = 'tokens';

    protected $casts = ['id' => 'integer', 'expiry' => 'integer', 'updated_at' => 'integer'];
}
