<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Relations\BelongsTo;

final class StrengthSet extends LegacyModel
{
    protected $table = 'strength_sets';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['set_index' => 'integer', 'reps' => 'integer', 'load_kg' => 'float', 'rpe' => 'float', 'created_at' => 'integer'];

    public function session(): BelongsTo
    {
        return $this->belongsTo(StrengthSession::class, 'session_id');
    }
}
