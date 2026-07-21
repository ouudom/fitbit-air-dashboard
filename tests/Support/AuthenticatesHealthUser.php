<?php

declare(strict_types=1);

namespace Tests\Support;

use Illuminate\Support\Facades\DB;

trait AuthenticatesHealthUser
{
    protected function healthSession(string $userId = 'health-user-1'): array
    {
        DB::table('meta')->updateOrInsert(['key' => 'healthUserId'], ['value' => $userId]);

        return ['health_user_id' => $userId];
    }
}
