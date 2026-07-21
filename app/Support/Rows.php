<?php

declare(strict_types=1);

namespace App\Support;

use Illuminate\Support\Str;

final class Rows
{
    /** @return array<string, mixed> */
    public static function camel(object|array $row): array
    {
        $result = [];
        foreach ((array) $row as $key => $value) {
            if (in_array($key, ['payload', 'raw', 'inputs', 'explanation', 'citations', 'request', 'response'], true) && is_string($value)) {
                $value = json_decode($value, true);
            }
            $result[Str::camel((string) $key)] = $value;
        }

        return $result;
    }

    /** @return list<array<string, mixed>> */
    public static function many(iterable $rows): array
    {
        return array_map(self::camel(...), is_array($rows) ? $rows : iterator_to_array($rows));
    }
}
