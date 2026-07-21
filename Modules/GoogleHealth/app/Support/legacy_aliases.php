<?php

declare(strict_types=1);
use Modules\GoogleHealth\Jobs\SyncHealthData;

// Allow queued jobs serialized before the modular cutover to finish safely.
if (! class_exists('App\\Jobs\\SyncHealthData', false)) {
    class_alias(SyncHealthData::class, 'App\\Jobs\\SyncHealthData');
}
