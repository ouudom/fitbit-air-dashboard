<?php

declare(strict_types=1);

namespace App\Models;

final class TimelineEvent extends LegacyModel
{
    protected $table = 'timeline_events';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['payload' => 'array', 'updated_at' => 'integer'];
}
