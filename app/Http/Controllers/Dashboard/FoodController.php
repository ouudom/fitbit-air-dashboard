<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Analytics\Contracts\AnalyticsRepository;
use App\Domain\Health\Api\GoogleHealthClient;
use App\Domain\Health\Sync\HealthSynchronizer;
use App\Http\Controllers\Controller;
use App\Models\FoodLog;
use App\Models\WriteOperation;
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

    public function store(Request $request, GoogleHealthClient $health, HealthSynchronizer $synchronizer): RedirectResponse
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

        $start = new \DateTimeImmutable($data['date'].' 12:00:00', new \DateTimeZone((string) config('app.timezone')));
        $utc = new \DateTimeZone('UTC');
        $offset = $start->getOffset().'s';
        $payload = ['nutritionLog' => [
            'interval' => [
                'startTime' => $start->setTimezone($utc)->format('Y-m-d\TH:i:s\Z'),
                'startUtcOffset' => $offset,
                'endTime' => $start->modify('+1 minute')->setTimezone($utc)->format('Y-m-d\TH:i:s\Z'),
                'endUtcOffset' => $offset,
            ],
            'foodDisplayName' => $data['name'],
            'mealType' => strtoupper($data['meal']),
            'energy' => isset($data['calories']) ? ['userProvidedUnit' => 'KILOCALORIE', 'kcal' => (float) $data['calories']] : null,
            'totalCarbohydrate' => isset($data['carbsG']) ? ['userProvidedUnit' => 'GRAM', 'grams' => (float) $data['carbsG']] : null,
            'totalFat' => isset($data['fatG']) ? ['userProvidedUnit' => 'GRAM', 'grams' => (float) $data['fatG']] : null,
            'nutrients' => isset($data['proteinG']) ? [['nutrient' => 'PROTEIN', 'quantity' => ['userProvidedUnit' => 'GRAM', 'grams' => (float) $data['proteinG']]]] : [],
        ]];
        $payload['nutritionLog'] = array_filter($payload['nutritionLog'], static fn (mixed $value): bool => $value !== null);
        $operation = $this->operation('nutrition-log', 'create', $payload);

        try {
            $result = $health->waitForOperation($health->createDataPoint('nutrition-log', $payload));
            if (isset($result['error'])) {
                throw new \RuntimeException(json_encode($result['error'], JSON_THROW_ON_ERROR));
            }
            $this->finish($operation, 'complete', $result);
            $synchronizer->syncDataType('nutrition-log');
            $now = self::nowMs();
            FoodLog::query()->create([
                'id' => (string) Str::uuid(), ...$this->foodColumns($data),
                'google_name' => $result['response']['name'] ?? $result['metadata']['target'] ?? null,
                'created_at' => $now, 'updated_at' => $now,
            ]);

            return back()->with('success', 'Food logged.');
        } catch (Throwable $error) {
            $this->finish($operation, 'error', null, $error->getMessage());

            return back()->withErrors(['food' => $error->getMessage()]);
        }
    }

    public function destroy(FoodLog $food, GoogleHealthClient $health): RedirectResponse
    {
        if ($food->google_name) {
            $request = ['names' => [$food->google_name]];
            $operation = $this->operation('nutrition-log', 'delete', $request);
            try {
                $result = $health->waitForOperation($health->deleteDataPoints('nutrition-log', $request['names']));
                $this->finish($operation, 'complete', $result);
            } catch (Throwable $error) {
                $this->finish($operation, 'error', null, $error->getMessage());

                return back()->withErrors(['food' => $error->getMessage()]);
            }
        }
        $food->delete();

        return back()->with('success', 'Food removed.');
    }

    private function operation(string $type, string $method, array $request): WriteOperation
    {
        $now = self::nowMs();

        return WriteOperation::query()->create([
            'id' => (string) Str::uuid(), 'data_type' => $type, 'method' => $method,
            'status' => 'pending', 'request' => $request, 'created_at' => $now, 'updated_at' => $now,
        ]);
    }

    private function finish(WriteOperation $operation, string $status, ?array $response, ?string $error = null): void
    {
        $operation->update(['status' => $status, 'response' => $response, 'error' => $error, 'updated_at' => self::nowMs()]);
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
