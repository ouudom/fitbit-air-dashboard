<?php

return [
    'name' => 'GoogleHealth',
    'oauth' => [
        'client_id' => env('GOOGLE_CLIENT_ID', ''),
        'client_secret' => env('GOOGLE_CLIENT_SECRET', ''),
        'redirect_uri' => env('REDIRECT_URI', 'http://localhost:3000/api/auth/callback'),
        'scopes' => env('SCOPES', 'https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly'),
        'auth_url' => 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url' => 'https://oauth2.googleapis.com/token',
    ],
    'api' => [
        'health_url' => 'https://health.googleapis.com/v4',
    ],
    'sync' => [
        'days' => (int) env('SYNC_DAYS', 30),
        'raw_types' => filter_var(env('SYNC_RAW_TYPES', false), FILTER_VALIDATE_BOOL),
        'cron_secret' => env('CRON_SECRET', ''),
    ],
    'legacy' => [
        'encryption_key' => env('TOKEN_ENCRYPTION_KEY', ''),
        'token_cipher' => env('TOKEN_CIPHER', 'legacy'),
        'session_secret' => env('SESSION_SECRET', env('GOOGLE_CLIENT_SECRET', 'development-only-change-me')),
    ],
];
