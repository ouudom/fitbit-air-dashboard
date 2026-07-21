<?php

declare(strict_types=1);

namespace Tests\Feature;

use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\Support\AuthenticatesHealthUser;
use Tests\Support\ConfiguresFeatureTest;
use Tests\TestCase;

final class DashboardAccessTest extends TestCase
{
    use AuthenticatesHealthUser;
    use ConfiguresFeatureTest;
    use RefreshDatabase;

    public function test_guest_is_redirected_from_dashboard_to_login(): void
    {
        $this->get(route('dashboard'))->assertRedirect(route('login'));
    }

    public function test_json_guest_receives_structured_unauthenticated_response(): void
    {
        $this->getJson(route('dashboard'))
            ->assertUnauthorized()
            ->assertExactJson(['error' => 'NOT_AUTHENTICATED']);
    }

    public function test_connected_user_can_open_dashboard(): void
    {
        $this->withSession($this->healthSession())
            ->get(route('dashboard'))
            ->assertOk()
            ->assertInertia(fn ($page) => $page->component('Dashboard/Index'));
    }

    public function test_session_for_a_different_bound_health_user_is_rejected(): void
    {
        $this->healthSession('bound-user');

        $this->withSession(['health_user_id' => 'stale-user'])
            ->get(route('dashboard'))
            ->assertRedirect(route('login'));
    }
}
