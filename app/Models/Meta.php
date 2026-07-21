<?php

declare(strict_types=1);

namespace App\Models;

final class Meta extends LegacyModel
{
    protected $table = 'meta';

    protected $primaryKey = 'key';

    public $incrementing = false;

    protected $keyType = 'string';
}
