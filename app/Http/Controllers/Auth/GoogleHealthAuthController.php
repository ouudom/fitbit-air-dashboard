<?php

declare(strict_types=1);

namespace App\Http\Controllers\Auth;

use App\Domain\Health\Api\GoogleHealthClient;
use App\Domain\Health\OAuth\GoogleOAuthClient;
use App\Domain\Health\OAuth\OAuthTokenStore;
use App\Http\Controllers\Controller;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Inertia\Inertia;
use Inertia\Response;
use Symfony\Component\HttpFoundation\Response as SymfonyResponse;
use Throwable;

final class GoogleHealthAuthController extends Controller
{
    public function show(GoogleOAuthClient $oauth): Response|RedirectResponse
    {
        if (session()->has('health_user_id')) {
            return redirect()->route('dashboard');
        }

        return Inertia::render('Auth/Login', [
            'connectUrl' => route('auth.google.redirect'),
            'configured' => config('lifestats.google.client_id') !== '',
        ]);
    }

    public function redirect(GoogleOAuthClient $oauth): RedirectResponse
    {
        $state = (string) Str::uuid();
        session(['oauth_state' => $state]);

        return redirect()->away($oauth->authorizationUrl($state));
    }

    public function callback(
        Request $request,
        GoogleOAuthClient $oauth,
        GoogleHealthClient $health,
        OAuthTokenStore $tokens,
    ): SymfonyResponse {
        $state = $request->string('state')->toString();
        $expected = (string) $request->session()->pull('oauth_state', '');
        if ($state === '' || $expected === '' || ! hash_equals($expected, $state) || ! $request->filled('code')) {
            return response('Invalid OAuth state', 400);
        }

        try {
            $oauth->exchangeCode($request->string('code')->toString());
            $identity = $health->identity();
            $userId = (string) ($identity['healthUserId'] ?? '');
            if ($userId === '') {
                throw new \RuntimeException('Google Health identity missing.');
            }

            $bound = DB::table('meta')->where('key', 'healthUserId')->value('value');
            if (is_string($bound) && $bound !== '' && $bound !== $userId) {
                $tokens->delete();

                return response('This installation is bound to another Google Health user.', 403);
            }

            DB::table('meta')->upsert([['key' => 'healthUserId', 'value' => $userId]], ['key'], ['value']);
            $request->session()->regenerate();
            $request->session()->put('health_user_id', $userId);

            return redirect()->route('dashboard')->with('success', 'Google Health connected.');
        } catch (Throwable $error) {
            report($error);

            return response($error->getMessage(), 502);
        }
    }

    public function logout(Request $request, OAuthTokenStore $tokens): RedirectResponse
    {
        $tokens->delete();
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return redirect()->route('login');
    }
}
