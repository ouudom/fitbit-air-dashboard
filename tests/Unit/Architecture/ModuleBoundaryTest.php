<?php

declare(strict_types=1);

namespace Tests\Unit\Architecture;

use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

final class ModuleBoundaryTest extends TestCase
{
    #[DataProvider('corePhpFiles')]
    public function test_core_does_not_import_google_health_implementations(string $file): void
    {
        $contents = file_get_contents($file);

        $this->assertIsString($contents);
        $this->assertStringNotContainsString('Modules\\GoogleHealth\\', $contents, $file);
    }

    /** @return iterable<string, array{string}> */
    public static function corePhpFiles(): iterable
    {
        $iterator = new \RecursiveIteratorIterator(
            new \RecursiveDirectoryIterator(dirname(__DIR__, 3).'/app'),
        );

        foreach ($iterator as $file) {
            if ($file->isFile() && $file->getExtension() === 'php') {
                yield $file->getPathname() => [$file->getPathname()];
            }
        }
    }
}
