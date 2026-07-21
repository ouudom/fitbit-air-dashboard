<?php

declare(strict_types=1);

namespace App\Models;

use Illuminate\Database\Eloquent\Relations\BelongsTo;

final class CoachMessage extends LegacyModel
{
    protected $table = 'coach_messages';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['citations' => 'array', 'created_at' => 'integer'];

    public function thread(): BelongsTo
    {
        return $this->belongsTo(CoachThread::class, 'thread_id');
    }
}
