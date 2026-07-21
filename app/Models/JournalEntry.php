<?php

declare(strict_types=1);

namespace App\Models;

final class JournalEntry extends LegacyModel
{
    protected $table = 'journal_entries';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['created_at' => 'integer', 'updated_at' => 'integer'];
}
