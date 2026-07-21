<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\Jobs;

use App\Domain\Analytics\ScoringService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldBeUnique;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\Middleware\WithoutOverlapping;
use Illuminate\Queue\SerializesModels;
use Modules\GoogleHealth\Sync\HealthSynchronizer;

final class SyncHealthData implements ShouldBeUnique, ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 3;

    public int $timeout = 1800;

    public int $uniqueFor = 1800;

    public function __construct(public readonly ?int $days = null, public readonly ?bool $full = null) {}

    /** @return list<WithoutOverlapping> */
    public function middleware(): array
    {
        return [(new WithoutOverlapping('health-sync'))->expireAfter(1800)];
    }

    public function handle(HealthSynchronizer $synchronizer, ScoringService $scoring): void
    {
        $result = $synchronizer->run($this->days, $this->full);
        $result['scoreDays'] = $scoring->computeRange(min((int) $result['days'], 90));
    }
}
