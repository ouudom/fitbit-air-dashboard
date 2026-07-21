<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Http\Controllers\Controller;
use App\Jobs\SyncHealthData;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

final class SyncController extends Controller
{
    public function store(Request $request): RedirectResponse
    {
        $data = $request->validate(['days' => ['nullable', 'integer', 'between:1,365'], 'full' => ['nullable', 'boolean']]);
        SyncHealthData::dispatch((int) ($data['days'] ?? config('lifestats.sync_days')), (bool) ($data['full'] ?? false));

        return back()->with('success', 'Fitbit sync queued.');
    }

    public function cron(Request $request): JsonResponse
    {
        $expected = (string) config('lifestats.cron_secret');
        if ($expected === '' || ! hash_equals('Bearer '.$expected, (string) $request->header('Authorization'))) {
            return response()->json(['error' => 'UNAUTHORIZED'], 401);
        }
        SyncHealthData::dispatch(3, true);

        return response()->json(['status' => 'queued'], 202);
    }
}
