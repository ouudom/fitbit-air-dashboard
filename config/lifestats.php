<?php

declare(strict_types=1);

return [
    'llm' => [
        'api_key' => env('LLM_API_KEY', env('OPENAI_API_KEY', '')),
        'model' => env('LLM_MODEL', env('OPENAI_MODEL', 'gpt-5.4-mini')),
        'base_url' => rtrim((string) env('LLM_BASE_URL', 'https://api.openai.com/v1'), '/'),
    ],
];
