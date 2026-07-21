<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Relations\HasMany;

final class StrengthSession extends LegacyModel
{
    protected $table = 'strength_sessions';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['duration_s' => 'integer', 'created_at' => 'integer', 'updated_at' => 'integer'];

    public function sets(): HasMany
    {
        return $this->hasMany(StrengthSet::class, 'session_id');
    }
}
