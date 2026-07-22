<?php

namespace App\Providers;

use App\Domain\Analytics\Contracts\AnalyticsRepository;
use App\Domain\Analytics\Repositories\DatabaseAnalyticsRepository;
use App\Domain\Health\Contracts\NutritionLogWriter;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        $this->app->bind(AnalyticsRepository::class, DatabaseAnalyticsRepository::class);
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        if ($this->app->bound(NutritionLogWriter::class)) {
            return;
        }

        $command = $_SERVER['argv'][1] ?? '';
        if ($this->app->runningInConsole() && str_starts_with($command, 'module:')) {
            return;
        }

        throw new \LogicException(
            'Required health integration is disabled. Enable GoogleHealth in modules_statuses.json.',
        );
    }
}
