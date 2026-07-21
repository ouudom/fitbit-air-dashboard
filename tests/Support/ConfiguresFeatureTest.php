<?php

declare(strict_types=1);

namespace Tests\Support;

trait ConfiguresFeatureTest
{
    protected function setUp(): void
    {
        parent::setUp();

        config()->set('app.key', 'base64:'.base64_encode(str_repeat('l', 32)));
    }
}
