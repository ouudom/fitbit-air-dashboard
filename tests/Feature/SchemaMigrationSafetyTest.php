<?php

declare(strict_types=1);

namespace Tests\Feature;

use Illuminate\Database\Migrations\Migration;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;
use Tests\TestCase;

final class SchemaMigrationSafetyTest extends TestCase
{
    use RefreshDatabase;

    public function test_schema_migration_preserves_existing_tables_and_rows(): void
    {
        DB::table('meta')->insert(['key' => 'healthUserId', 'value' => 'existing-user']);

        $migration = $this->lifestatsMigration();
        $migration->up();
        $migration->down();

        $this->assertTrue(Schema::hasTable('meta'));
        $this->assertSame('existing-user', DB::table('meta')->where('key', 'healthUserId')->value('value'));
    }

    public function test_schema_migration_only_recreates_a_missing_table(): void
    {
        DB::table('meta')->insert(['key' => 'sentinel', 'value' => 'keep-me']);
        Schema::drop('write_operations');

        $this->lifestatsMigration()->up();

        $this->assertTrue(Schema::hasTable('write_operations'));
        $this->assertSame('keep-me', DB::table('meta')->where('key', 'sentinel')->value('value'));
    }

    private function lifestatsMigration(): Migration
    {
        /** @var Migration $migration */
        $migration = require database_path('migrations/2026_07_21_000000_create_lifestats_schema.php');

        return $migration;
    }
}
