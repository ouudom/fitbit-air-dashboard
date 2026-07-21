<?php

declare(strict_types=1);

namespace App\Models;

final class SyncCursor extends LegacyModel
{
    protected $table = 'sync_cursors';

    protected $primaryKey = 'data_type';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['last_successful_at' => 'integer', 'updated_at' => 'integer'];
}
