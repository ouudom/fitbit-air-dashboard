<?php

declare(strict_types=1);

namespace Tests\Unit\Domain\Coach;

use App\Domain\Coach\ResponsesStreamParser;
use PHPUnit\Framework\TestCase;
use RuntimeException;

final class ResponsesStreamParserTest extends TestCase
{
    public function test_it_parses_json_responses(): void
    {
        self::assertSame(['output_text' => 'hello'], (new ResponsesStreamParser)->parse('{"output_text":"hello"}'));
    }

    public function test_it_prefers_completed_sse_response_over_deltas(): void
    {
        $body = "event: response.output_text.delta\ndata: {\"type\":\"response.output_text.delta\",\"delta\":\"partial\"}\n\n"
            ."event: response.completed\ndata: {\"type\":\"response.completed\",\"response\":{\"output_text\":\"complete\",\"output\":[]}}\n\n";

        self::assertSame('complete', (new ResponsesStreamParser)->parse($body)['output_text']);
    }

    public function test_it_surfaces_provider_stream_errors(): void
    {
        $this->expectException(RuntimeException::class);
        $this->expectExceptionMessage('provider broke');

        (new ResponsesStreamParser)->parse("event: error\ndata: {\"error\":{\"message\":\"provider broke\"}}\n\n");
    }
}
