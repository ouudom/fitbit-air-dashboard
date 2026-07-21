<?php

namespace Modules\GoogleHealth\Providers;

use App\Domain\Health\Contracts\NutritionLogWriter;
use Illuminate\Console\Scheduling\Schedule;
use Modules\GoogleHealth\Api\GoogleHealthClient;
use Modules\GoogleHealth\Crypto\LegacySessionSigner;
use Modules\GoogleHealth\Crypto\TokenCipher;
use Modules\GoogleHealth\Http\Middleware\EnsureHealthConnected;
use Modules\GoogleHealth\Jobs\SyncHealthData;
use Modules\GoogleHealth\Nutrition\GoogleNutritionLogWriter;
use Modules\GoogleHealth\OAuth\GoogleOAuthClient;
use Modules\GoogleHealth\OAuth\OAuthTokenStore;
use Modules\GoogleHealth\Operations\WriteOperationStore;
use Modules\GoogleHealth\Sync\HealthPayloadMapper;
use Modules\GoogleHealth\Sync\HealthRepository;
use Modules\GoogleHealth\Sync\HealthSynchronizer;
use Nwidart\Modules\Support\ModuleServiceProvider;

class GoogleHealthServiceProvider extends ModuleServiceProvider
{
    /**
     * The name of the module.
     */
    protected string $name = 'GoogleHealth';

    /**
     * The lowercase version of the module name.
     */
    protected string $nameLower = 'google-health';

    /**
     * Command classes to register.
     *
     * @var string[]
     */
    // protected array $commands = [];

    /**
     * Provider classes to register.
     *
     * @var string[]
     */
    protected array $providers = [
        RouteServiceProvider::class,
    ];

    public function register(): void
    {
        parent::register();

        $this->app->singleton(LegacySessionSigner::class);
        $this->app->singleton(HealthPayloadMapper::class);
        $this->app->scoped(TokenCipher::class);
        $this->app->scoped(OAuthTokenStore::class);
        $this->app->scoped(GoogleOAuthClient::class);
        $this->app->scoped(GoogleHealthClient::class);
        $this->app->scoped(HealthRepository::class);
        $this->app->scoped(HealthSynchronizer::class);
        $this->app->scoped(WriteOperationStore::class);
        $this->app->scoped(GoogleNutritionLogWriter::class);
        $this->app->bind(NutritionLogWriter::class, GoogleNutritionLogWriter::class);
    }

    public function boot(): void
    {
        parent::boot();

        $this->app['router']->aliasMiddleware('health.connected', EnsureHealthConnected::class);
    }

    protected function configureSchedules(Schedule $schedule): void
    {
        $schedule->job(new SyncHealthData(3, true))
            ->hourly()
            ->name('health-sync')
            ->withoutOverlapping(30)
            ->onOneServer();
    }
}
