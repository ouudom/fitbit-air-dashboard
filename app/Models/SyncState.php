<?php

declare(strict_types=1);

namespace App\Models;

final class SyncState extends LegacyModel
{
    protected $table = 'sync_state';

    protected $primaryKey = 'data_type';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['last_synced_at' => 'integer', 'record_count' => 'integer', 'updated_at' => 'integer'];
}
