<?php

declare(strict_types=1);

namespace Tests\Feature;

use App\Domain\Health\Contracts\NutritionLogWriter;
use App\Models\FoodLog;
use App\Models\JournalEntry;
use App\Models\StrengthSession;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Mockery\MockInterface;
use Tests\Support\AuthenticatesHealthUser;
use Tests\Support\ConfiguresFeatureTest;
use Tests\TestCase;

final class HealthLogCrudTest extends TestCase
{
    use AuthenticatesHealthUser;
    use ConfiguresFeatureTest;
    use RefreshDatabase;

    public function test_food_validation_rejects_invalid_values_without_writing(): void
    {
        $this->from(route('dashboard.food'))
            ->withSession($this->healthSession())
            ->post(route('dashboard.food.store'), [
                'date' => '21-07-2026', 'meal' => '', 'name' => '', 'calories' => -1,
            ])
            ->assertRedirect(route('dashboard.food'))
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
            ->post(route('dashboard.food.store'), [
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

    public function test_journal_entry_can_be_created_and_deleted(): void
    {
        $session = $this->healthSession();
        $this->withSession($session)->post(route('dashboard.journal.store'), [
            'date' => '2026-07-21', 'habit' => '  Meditation  ', 'value' => 'yes', 'notes' => 'Calm',
        ])->assertSessionHasNoErrors();

        $entry = JournalEntry::query()->sole();
        $this->assertSame('Meditation', $entry->habit);

        $this->withSession($session)
            ->delete(route('dashboard.journal.destroy', $entry))
            ->assertSessionHasNoErrors();
        $this->assertDatabaseCount('journal_entries', 0);
    }

    public function test_journal_validation_requires_date_habit_and_value(): void
    {
        $this->withSession($this->healthSession())
            ->post(route('dashboard.journal.store'), ['date' => 'invalid'])
            ->assertSessionHasErrors(['date', 'habit', 'value']);

        $this->assertDatabaseCount('journal_entries', 0);
    }

    public function test_strength_session_and_sets_are_created_and_deleted_together(): void
    {
        $session = $this->healthSession();
        $this->withSession($session)->post(route('dashboard.strength.store'), [
            'date' => '2026-07-21',
            'title' => ' Full Body ',
            'durationS' => 2400,
            'sets' => [
                ['exercise' => ' Squat ', 'reps' => 5, 'loadKg' => 80, 'rpe' => 8],
                ['exercise' => 'Bench', 'reps' => 8, 'loadKg' => 50, 'rpe' => 7.5],
            ],
        ])->assertSessionHasNoErrors();

        $strength = StrengthSession::query()->sole();
        $this->assertSame('Full Body', $strength->title);
        $this->assertSame(2, $strength->sets()->count());
        $this->assertSame([1, 2], $strength->sets()->orderBy('set_index')->pluck('set_index')->all());

        $this->withSession($session)
            ->delete(route('dashboard.strength.destroy', $strength))
            ->assertSessionHasNoErrors();
        $this->assertDatabaseCount('strength_sessions', 0);
        $this->assertDatabaseCount('strength_sets', 0);
    }

    public function test_strength_validation_requires_at_least_one_valid_set(): void
    {
        $this->withSession($this->healthSession())
            ->post(route('dashboard.strength.store'), [
                'date' => '2026-07-21', 'title' => 'Session', 'sets' => [],
            ])
            ->assertSessionHasErrors(['sets']);

        $this->assertDatabaseCount('strength_sessions', 0);
    }

    public function test_local_food_entry_can_be_deleted_without_remote_call(): void
    {
        $food = FoodLog::query()->create([
            'id' => 'food-1', 'date' => '2026-07-21', 'meal' => 'lunch', 'name' => 'Rice',
            'created_at' => 1, 'updated_at' => 1,
        ]);

        $this->withSession($this->healthSession())
            ->delete(route('dashboard.food.destroy', $food))
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
            ->delete(route('dashboard.food.destroy', $food))
            ->assertSessionHasNoErrors();

        $this->assertDatabaseCount('food_logs', 0);
    }
}
