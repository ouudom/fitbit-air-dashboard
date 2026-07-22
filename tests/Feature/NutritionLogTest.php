<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Domain\Health\Contracts\NutritionLogWriter;
use App\Models\FoodLog;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Mockery\MockInterface;
use Tests\Support\AuthenticatesHealthUser;
use Tests\Support\ConfiguresFeatureTest;
use Tests\TestCase;

final class NutritionLogTest extends TestCase
{
    use AuthenticatesHealthUser;
    use ConfiguresFeatureTest;
    use RefreshDatabase;

    public function test_food_validation_rejects_invalid_values_without_writing(): void
    {
        $this->from(route('health.nutrition'))
            ->withSession($this->healthSession())
            ->post(route('health.nutrition.store'), [
                'date' => '21-07-2026', 'meal' => '', 'name' => '', 'calories' => -1,
            ])
            ->assertRedirect(route('health.nutrition'))
            ->assertSessionHasErrors(['date', 'meal', 'name', 'calories']);

        $this->assertDatabaseCount('food_logs', 0);
        $this->assertDatabaseCount('write_operations', 0);
    }

    public function test_food_entry_uses_nutrition_port_and_persists_remote_reference(): void
    {
        $this->mock(NutritionLogWriter::class, function (MockInterface $mock): void {
            $mock->shouldReceive('create')
                ->once()
                ->withArgs(fn (array $food): bool => $food['name'] === 'Rice' && $food['proteinG'] === 5)
                ->andReturn('users/me/dataTypes/nutrition-log/dataPoints/remote-1');
        });

        $this->withSession($this->healthSession())
            ->post(route('health.nutrition.store'), [
                'date' => '2026-07-21',
                'meal' => 'lunch',
                'name' => 'Rice',
                'calories' => 250,
                'proteinG' => 5,
            ])
            ->assertSessionHasNoErrors();

        $this->assertDatabaseHas('food_logs', [
            'name' => 'Rice',
            'google_name' => 'users/me/dataTypes/nutrition-log/dataPoints/remote-1',
        ]);
    }

    public function test_local_food_entry_can_be_deleted_without_remote_call(): void
    {
        $food = FoodLog::query()->create([
            'id' => 'food-1', 'date' => '2026-07-21', 'meal' => 'lunch', 'name' => 'Rice',
            'created_at' => 1, 'updated_at' => 1,
        ]);

        $this->withSession($this->healthSession())
            ->delete(route('health.nutrition.destroy', $food))
            ->assertSessionHasNoErrors();

        $this->assertDatabaseCount('food_logs', 0);
    }

    public function test_remote_food_entry_is_deleted_through_nutrition_port(): void
    {
        $food = FoodLog::query()->create([
            'id' => 'food-remote', 'date' => '2026-07-21', 'meal' => 'lunch', 'name' => 'Rice',
            'google_name' => 'remote-1', 'created_at' => 1, 'updated_at' => 1,
        ]);
        $this->mock(NutritionLogWriter::class, function (MockInterface $mock): void {
            $mock->shouldReceive('delete')->once()->with('remote-1');
        });

        $this->withSession($this->healthSession())
            ->delete(route('health.nutrition.destroy', $food))
            ->assertSessionHasNoErrors();

        $this->assertDatabaseCount('food_logs', 0);
    }
}
