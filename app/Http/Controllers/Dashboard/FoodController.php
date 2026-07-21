<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Analytics\Contracts\AnalyticsRepository;
use App\Domain\Health\Contracts\NutritionLogWriter;
use App\Http\Controllers\Controller;
use App\Models\FoodLog;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;
use Throwable;

final class FoodController extends Controller
{
    public function index(AnalyticsRepository $repository): Response
    {
        return Inertia::render('Dashboard/Food', ['logs' => $repository->foodLogs()]);
    }

    public function store(Request $request, NutritionLogWriter $nutrition): RedirectResponse
    {
        $data = $request->validate([
            'date' => ['required', 'date_format:Y-m-d'],
            'meal' => ['required', 'string', 'max:40'],
            'name' => ['required', 'string', 'max:255'],
            'calories' => ['nullable', 'numeric', 'min:0'],
            'proteinG' => ['nullable', 'numeric', 'min:0'],
            'carbsG' => ['nullable', 'numeric', 'min:0'],
            'fatG' => ['nullable', 'numeric', 'min:0'],
            'notes' => ['nullable', 'string', 'max:1000'],
        ]);

        try {
            $remoteReference = $nutrition->create($data);
            $now = self::nowMs();
            FoodLog::query()->create([
                'id' => (string) Str::uuid(), ...$this->foodColumns($data),
                'google_name' => $remoteReference,
                'created_at' => $now, 'updated_at' => $now,
            ]);

            return back()->with('success', 'Food logged.');
        } catch (Throwable $error) {
            return back()->withErrors(['food' => $error->getMessage()]);
        }
    }

    public function destroy(FoodLog $food, NutritionLogWriter $nutrition): RedirectResponse
    {
        if ($food->google_name) {
            try {
                $nutrition->delete($food->google_name);
            } catch (Throwable $error) {
                return back()->withErrors(['food' => $error->getMessage()]);
            }
        }
        $food->delete();

        return back()->with('success', 'Food removed.');
    }

    private function foodColumns(array $data): array
    {
        return [
            'date' => $data['date'], 'meal' => $data['meal'], 'name' => $data['name'],
            'calories' => $data['calories'] ?? null, 'protein_g' => $data['proteinG'] ?? null,
            'carbs_g' => $data['carbsG'] ?? null, 'fat_g' => $data['fatG'] ?? null,
            'notes' => $data['notes'] ?? null,
        ];
    }

    private static function nowMs(): int
    {
        return (int) floor(microtime(true) * 1000);
    }
}
