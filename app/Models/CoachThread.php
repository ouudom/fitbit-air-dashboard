<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Relations\HasMany;

final class CoachThread extends LegacyModel
{
    protected $table = 'coach_threads';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['created_at' => 'integer', 'updated_at' => 'integer'];

    public function messages(): HasMany
    {
        return $this->hasMany(CoachMessage::class, 'thread_id');
    }
}
