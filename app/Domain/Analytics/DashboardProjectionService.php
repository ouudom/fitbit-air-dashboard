<?php

declare(strict_types=1);

namespace App\Domain\Analytics;

use App\Domain\Analytics\Contracts\AnalyticsRepository;

final class DashboardProjectionService
{
    public function __construct(
        private readonly AnalyticsRepository $repository,
        private readonly HealthDataService $health,
    ) {}

    /** @return array<string, mixed> */
    public function today(): array
    {
        $lastSync = $this->repository->meta('lastSync');

        return [
            'activity' => $this->health->activity(14), 'sleep' => $this->health->sleep(14),
            'vitals' => $this->health->vitals(), 'lastSync' => $lastSync === null ? null : (int) $lastSync,
        ];
    }
}
