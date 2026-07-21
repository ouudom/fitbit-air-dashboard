<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\Models;

use App\Models\LegacyModel;

final class WriteOperation extends LegacyModel
{
    protected $table = 'write_operations';

    public $incrementing = false;

    protected $keyType = 'string';

    protected $casts = ['request' => 'array', 'response' => 'array', 'created_at' => 'integer', 'updated_at' => 'integer'];
}
