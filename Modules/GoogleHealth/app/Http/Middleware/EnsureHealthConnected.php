<?php

declare(strict_types=1);

namespace Modules\GoogleHealth\Http\Middleware;

use Closure;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Symfony\Component\HttpFoundation\Response;

final class EnsureHealthConnected
{
    public function handle(Request $request, Closure $next): Response
    {
        $sessionUser = $request->session()->get('health_user_id');
        $bound = DB::table('meta')->where('key', 'healthUserId')->value('value');
        if (is_string($sessionUser) && $sessionUser !== '' && is_string($bound) && hash_equals($bound, $sessionUser)) {
            return $next($request);
        }
        $request->session()->forget('health_user_id');

        if ($this->restoreLegacySession($request)) {
            return $next($request);
        }

        if ($request->expectsJson()) {
            return response()->json(['error' => 'NOT_AUTHENTICATED'], 401);
        }

        return new RedirectResponse(route('login'));
    }

    private function restoreLegacySession(Request $request): bool
    {
        $cookie = $request->cookie('fitbit_air_session');
        if (! is_string($cookie) || $cookie === '') {
            return false;
        }

        $parts = explode('.', $cookie);
        if (count($parts) !== 3 || ! ctype_digit($parts[1]) || (int) $parts[1] < time()) {
            return false;
        }

        [$userId, $expires, $signature] = $parts;
        $expected = rtrim(strtr(base64_encode(hash_hmac(
            'sha256',
            "{$userId}.{$expires}",
            (string) config('google-health.legacy.session_secret'),
            true,
        )), '+/', '-_'), '=');

        $bound = DB::table('meta')->where('key', 'healthUserId')->value('value');
        if (! hash_equals($expected, $signature) || ! is_string($bound) || $bound !== $userId) {
            return false;
        }

        $request->session()->put('health_user_id', $userId);

        return true;
    }
}
