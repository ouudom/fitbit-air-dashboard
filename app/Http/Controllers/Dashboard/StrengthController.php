<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Analytics\Contracts\AnalyticsRepository;
use App\Http\Controllers\Controller;
use App\Models\StrengthSession;
use App\Models\StrengthSet;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;

final class StrengthController extends Controller
{
    public function index(AnalyticsRepository $repository): Response
    {
        return Inertia::render('Dashboard/Strength', ['sessions' => $repository->strengthSessions(100)]);
    }

    public function store(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'date' => ['required', 'date_format:Y-m-d'], 'title' => ['required', 'string', 'max:255'],
            'startTime' => ['nullable', 'date'], 'durationS' => ['nullable', 'integer', 'min:0'],
            'notes' => ['nullable', 'string', 'max:1000'], 'sets' => ['required', 'array', 'min:1', 'max:100'],
            'sets.*.exercise' => ['required', 'string', 'max:255'], 'sets.*.reps' => ['nullable', 'integer', 'min:0'],
            'sets.*.loadKg' => ['nullable', 'numeric', 'min:0'], 'sets.*.rpe' => ['nullable', 'numeric', 'between:0,10'],
        ]);
        DB::transaction(function () use ($data): void {
            $now = (int) floor(microtime(true) * 1000);
            $id = (string) Str::uuid();
            StrengthSession::query()->create([
                'id' => $id, 'date' => $data['date'], 'title' => trim($data['title']),
                'start_time' => $data['startTime'] ?? null, 'duration_s' => $data['durationS'] ?? null,
                'notes' => $data['notes'] ?? null, 'created_at' => $now, 'updated_at' => $now,
            ]);
            foreach ($data['sets'] as $index => $set) {
                StrengthSet::query()->create([
                    'id' => (string) Str::uuid(), 'session_id' => $id, 'exercise' => trim($set['exercise']),
                    'set_index' => $index + 1, 'reps' => $set['reps'] ?? null,
                    'load_kg' => $set['loadKg'] ?? null, 'rpe' => $set['rpe'] ?? null, 'created_at' => $now,
                ]);
            }
        });

        return back()->with('success', 'Strength session saved.');
    }

    public function destroy(StrengthSession $strength): RedirectResponse
    {
        DB::transaction(function () use ($strength): void {
            StrengthSet::query()->where('session_id', $strength->getKey())->delete();
            $strength->delete();
        });

        return back()->with('success', 'Strength session removed.');
    }
}
