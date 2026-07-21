<?php

namespace App\Providers;

use App\Domain\Analytics\Contracts\AnalyticsRepository;
use App\Domain\Analytics\Repositories\DatabaseAnalyticsRepository;
use App\Domain\Analytics\ScoringService;
use App\Domain\Coach\CoachService;
use App\Domain\Coach\Contracts\CoachRepository;
use App\Domain\Coach\Contracts\ResponsesProvider;
use App\Domain\Coach\HttpResponsesProvider;
use App\Domain\Coach\Repositories\DatabaseCoachRepository;
use App\Domain\Coach\ResponsesStreamParser;
use Illuminate\Http\Client\Factory as HttpFactory;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        $this->app->bind(AnalyticsRepository::class, DatabaseAnalyticsRepository::class);
        $this->app->bind(CoachRepository::class, DatabaseCoachRepository::class);
        $this->app->bind(ResponsesProvider::class, fn ($app): ResponsesProvider => new HttpResponsesProvider(
            $app->make(HttpFactory::class),
            $app->make(ResponsesStreamParser::class),
            (string) config('lifestats.llm.base_url'),
            (string) config('lifestats.llm.api_key'),
        ));
        $this->app->bind(CoachService::class, fn ($app): CoachService => new CoachService(
            $app->make(CoachRepository::class),
            $app->make(ResponsesProvider::class),
            $app->make(AnalyticsRepository::class),
            $app->make(ScoringService::class),
            (string) config('lifestats.llm.model'),
        ));
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        //
    }
}
