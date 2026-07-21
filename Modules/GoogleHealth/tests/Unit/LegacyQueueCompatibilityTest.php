<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\Tests\Unit;

use Modules\GoogleHealth\Jobs\SyncHealthData;
use Tests\TestCase;

final class LegacyQueueCompatibilityTest extends TestCase
{
    public function test_pre_module_sync_jobs_resolve_to_the_module_job(): void
    {
        $this->assertTrue(class_exists('App\\Jobs\\SyncHealthData'));
        $this->assertTrue(is_a('App\\Jobs\\SyncHealthData', SyncHealthData::class, true));
    }
}
