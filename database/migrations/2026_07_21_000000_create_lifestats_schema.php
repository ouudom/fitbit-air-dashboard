<?php

declare(strict_types=1);

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        $this->create('tokens', function (Blueprint $table): void {
            $table->integer('id')->primary();
            $table->text('access_token')->nullable();
            $table->text('refresh_token')->nullable();
            $table->bigInteger('expiry')->nullable();
            $table->text('scope')->nullable();
            $table->bigInteger('updated_at')->nullable();
        });
        $this->create('daily_metrics', function (Blueprint $table): void {
            $table->text('date');
            $table->text('metric');
            $table->double('value')->nullable();
            $table->bigInteger('updated_at')->nullable();
            $table->primary(['date', 'metric']);
        });
        $this->create('exercises', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('type')->nullable();
            $table->text('display_name')->nullable();
            $table->text('start_time')->nullable();
            $table->bigInteger('duration_s')->nullable();
            $table->double('calories')->nullable();
            $table->double('distance_mm')->nullable();
            $table->integer('steps')->nullable();
            $table->integer('avg_hr')->nullable();
            $table->jsonb('raw')->nullable();
            $table->bigInteger('updated_at')->nullable();
        });
        $this->create('meta', function (Blueprint $table): void {
            $table->text('key')->primary();
            $table->text('value')->nullable();
        });
        $this->create('health_records', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('data_type');
            $table->text('start_time')->nullable();
            $table->text('end_time')->nullable();
            $table->text('date')->nullable();
            $table->double('numeric_value')->nullable();
            $table->jsonb('payload');
            $table->bigInteger('updated_at')->nullable();
            $table->index(['data_type', 'date']);
        });
        $this->create('sync_state', function (Blueprint $table): void {
            $table->text('data_type')->primary();
            $table->bigInteger('last_synced_at')->nullable();
            $table->text('status');
            $table->integer('record_count')->default(0);
            $table->text('error')->nullable();
            $table->bigInteger('updated_at')->nullable();
        });
        $this->create('food_logs', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('date');
            $table->text('meal');
            $table->text('name');
            $table->double('calories')->nullable();
            $table->double('protein_g')->nullable();
            $table->double('carbs_g')->nullable();
            $table->double('fat_g')->nullable();
            $table->text('notes')->nullable();
            $table->text('google_name')->nullable();
            $table->bigInteger('created_at')->nullable();
            $table->bigInteger('updated_at')->nullable();
            $table->index('date');
        });
        $this->create('daily_scores', function (Blueprint $table): void {
            $table->text('date');
            $table->text('score_type');
            $table->text('model_version');
            $table->double('value')->nullable();
            $table->text('confidence');
            $table->text('state');
            $table->jsonb('inputs');
            $table->jsonb('explanation');
            $table->bigInteger('updated_at');
            $table->primary(['date', 'score_type', 'model_version']);
        });
        $this->create('data_quality', function (Blueprint $table): void {
            $table->text('date');
            $table->text('data_type');
            $table->text('status');
            $table->double('coverage')->nullable();
            $table->text('reason')->nullable();
            $table->bigInteger('updated_at');
            $table->primary(['date', 'data_type']);
        });
        $this->create('timeline_events', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('date')->index();
            $table->text('event_type');
            $table->text('title');
            $table->text('start_time')->nullable();
            $table->text('end_time')->nullable();
            $table->text('source');
            $table->text('source_id')->nullable();
            $table->jsonb('payload');
            $table->bigInteger('updated_at');
        });
        $this->create('journal_entries', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('date')->index();
            $table->text('occurred_at')->nullable();
            $table->text('habit');
            $table->text('value');
            $table->text('notes')->nullable();
            $table->bigInteger('created_at');
            $table->bigInteger('updated_at');
        });
        $this->create('strength_sessions', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('date')->index();
            $table->text('title');
            $table->text('start_time')->nullable();
            $table->integer('duration_s')->nullable();
            $table->text('notes')->nullable();
            $table->bigInteger('created_at');
            $table->bigInteger('updated_at');
        });
        $this->create('strength_sets', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('session_id')->index();
            $table->text('exercise');
            $table->integer('set_index');
            $table->integer('reps')->nullable();
            $table->double('load_kg')->nullable();
            $table->double('rpe')->nullable();
            $table->bigInteger('created_at');
        });
        $this->create('goals', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('goal_type');
            $table->text('title');
            $table->double('target')->nullable();
            $table->text('unit')->nullable();
            $table->boolean('active')->default(true);
            $table->bigInteger('created_at');
            $table->bigInteger('updated_at');
        });
        $this->create('coach_threads', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('title');
            $table->bigInteger('created_at');
            $table->bigInteger('updated_at');
        });
        $this->create('coach_messages', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('thread_id')->index();
            $table->text('role');
            $table->text('content');
            $table->jsonb('citations');
            $table->bigInteger('created_at');
        });
        $this->create('sync_cursors', function (Blueprint $table): void {
            $table->text('data_type')->primary();
            $table->text('cursor')->nullable();
            $table->bigInteger('last_successful_at')->nullable();
            $table->bigInteger('updated_at');
        });
        $this->create('write_operations', function (Blueprint $table): void {
            $table->text('id')->primary();
            $table->text('data_type');
            $table->text('method');
            $table->text('status');
            $table->jsonb('request');
            $table->jsonb('response')->nullable();
            $table->text('error')->nullable();
            $table->bigInteger('created_at');
            $table->bigInteger('updated_at');
        });
    }

    public function down(): void
    {
        // Existing LifeStats data is deliberately never dropped by rollback.
    }

    private function create(string $table, callable $definition): void
    {
        if (! Schema::hasTable($table)) {
            Schema::create($table, $definition);
        }
    }
};
