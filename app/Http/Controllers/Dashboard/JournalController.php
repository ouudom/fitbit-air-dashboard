<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Analytics\Contracts\AnalyticsRepository;
use App\Domain\Analytics\InsightsService;
use App\Http\Controllers\Controller;
use App\Models\JournalEntry;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;

final class JournalController extends Controller
{
    public function index(AnalyticsRepository $repository, InsightsService $insights): Response
    {
        return Inertia::render('Dashboard/Journal', ['entries' => $repository->journal(), 'insights' => $insights->journal()]);
    }

    public function store(Request $request): RedirectResponse
    {
        $data = $request->validate([
            'date' => ['required', 'date_format:Y-m-d'], 'habit' => ['required', 'string', 'max:255'],
            'value' => ['required', 'string', 'max:100'], 'notes' => ['nullable', 'string', 'max:1000'],
            'occurredAt' => ['nullable', 'date'],
        ]);
        $now = (int) floor(microtime(true) * 1000);
        JournalEntry::query()->create([
            'id' => (string) Str::uuid(), 'date' => $data['date'], 'occurred_at' => $data['occurredAt'] ?? null,
            'habit' => trim($data['habit']), 'value' => trim($data['value']), 'notes' => $data['notes'] ?? null,
            'created_at' => $now, 'updated_at' => $now,
        ]);

        return back()->with('success', 'Journal entry saved.');
    }

    public function destroy(JournalEntry $journal): RedirectResponse
    {
        $journal->delete();

        return back()->with('success', 'Journal entry removed.');
    }
}
