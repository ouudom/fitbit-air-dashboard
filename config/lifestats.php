<?php

declare(strict_types=1);

return [
    'google' => [
        'client_id' => env('GOOGLE_CLIENT_ID', ''),
        'client_secret' => env('GOOGLE_CLIENT_SECRET', ''),
        'redirect_uri' => env('REDIRECT_URI', 'http://localhost:3000/api/auth/callback'),
        'scopes' => env('SCOPES', 'https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly'),
        'auth_url' => 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url' => 'https://oauth2.googleapis.com/token',
        'health_url' => 'https://health.googleapis.com/v4',
    ],
    'sync_days' => (int) env('SYNC_DAYS', 30),
    'sync_raw_types' => filter_var(env('SYNC_RAW_TYPES', false), FILTER_VALIDATE_BOOL),
    'legacy_encryption_key' => env('TOKEN_ENCRYPTION_KEY', ''),
    // Keep tokens readable by the previous runtime throughout the rollback window.
    'token_cipher' => env('TOKEN_CIPHER', 'legacy'),
    'legacy_session_secret' => env('SESSION_SECRET', env('GOOGLE_CLIENT_SECRET', 'development-only-change-me')),
    'cron_secret' => env('CRON_SECRET', ''),
    'llm' => [
        'api_key' => env('LLM_API_KEY', env('OPENAI_API_KEY', '')),
        'model' => env('LLM_MODEL', env('OPENAI_MODEL', 'gpt-5.4-mini')),
        'base_url' => rtrim((string) env('LLM_BASE_URL', 'https://api.openai.com/v1'), '/'),
    ],
];
