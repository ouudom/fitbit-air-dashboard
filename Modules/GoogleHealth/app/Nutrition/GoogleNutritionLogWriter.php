<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\Nutrition;

use App\Domain\Health\Contracts\NutritionLogWriter;
use DateTimeImmutable;
use DateTimeZone;
use Modules\GoogleHealth\Api\GoogleHealthClient;
use Modules\GoogleHealth\Operations\WriteOperationStore;
use Modules\GoogleHealth\Sync\HealthSynchronizer;
use RuntimeException;
use Throwable;

final readonly class GoogleNutritionLogWriter implements NutritionLogWriter
{
    public function __construct(
        private GoogleHealthClient $health,
        private HealthSynchronizer $synchronizer,
        private WriteOperationStore $operations,
    ) {}

    public function create(array $food): ?string
    {
        $payload = $this->payload($food);
        $operation = $this->operations->create('nutrition-log', 'create', $payload);

        try {
            $result = $this->health->waitForOperation(
                $this->health->createDataPoint('nutrition-log', $payload),
            );
            if (isset($result['error'])) {
                throw new RuntimeException(json_encode($result['error'], JSON_THROW_ON_ERROR));
            }

            $this->operations->finish($operation, 'complete', $result);
            $this->synchronizer->syncDataType('nutrition-log');

            $reference = $result['response']['name'] ?? $result['metadata']['target'] ?? null;

            return is_string($reference) && $reference !== '' ? $reference : null;
        } catch (Throwable $error) {
            $this->operations->finish($operation, 'error', null, $error->getMessage());

            throw $error;
        }
    }

    public function delete(string $remoteReference): void
    {
        $request = ['names' => [$remoteReference]];
        $operation = $this->operations->create('nutrition-log', 'delete', $request);

        try {
            $result = $this->health->waitForOperation(
                $this->health->deleteDataPoints('nutrition-log', $request['names']),
            );
            if (isset($result['error'])) {
                throw new RuntimeException(json_encode($result['error'], JSON_THROW_ON_ERROR));
            }
            $this->operations->finish($operation, 'complete', $result);
        } catch (Throwable $error) {
            $this->operations->finish($operation, 'error', null, $error->getMessage());

            throw $error;
        }
    }

    /** @param array<string, mixed> $food @return array{nutritionLog:array<string, mixed>} */
    private function payload(array $food): array
    {
        $start = new DateTimeImmutable(
            $food['date'].' 12:00:00',
            new DateTimeZone((string) config('app.timezone')),
        );
        $utc = new DateTimeZone('UTC');
        $offset = $start->getOffset().'s';
        $nutrition = [
            'interval' => [
                'startTime' => $start->setTimezone($utc)->format('Y-m-d\TH:i:s\Z'),
                'startUtcOffset' => $offset,
                'endTime' => $start->modify('+1 minute')->setTimezone($utc)->format('Y-m-d\TH:i:s\Z'),
                'endUtcOffset' => $offset,
            ],
            'foodDisplayName' => $food['name'],
            'mealType' => strtoupper($food['meal']),
            'energy' => isset($food['calories'])
                ? ['userProvidedUnit' => 'KILOCALORIE', 'kcal' => (float) $food['calories']]
                : null,
            'totalCarbohydrate' => isset($food['carbsG'])
                ? ['userProvidedUnit' => 'GRAM', 'grams' => (float) $food['carbsG']]
                : null,
            'totalFat' => isset($food['fatG'])
                ? ['userProvidedUnit' => 'GRAM', 'grams' => (float) $food['fatG']]
                : null,
            'nutrients' => isset($food['proteinG'])
                ? [[
                    'nutrient' => 'PROTEIN',
                    'quantity' => ['userProvidedUnit' => 'GRAM', 'grams' => (float) $food['proteinG']],
                ]]
                : [],
        ];

        return ['nutritionLog' => array_filter($nutrition, static fn (mixed $value): bool => $value !== null)];
    }
}
