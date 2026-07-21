<?php

declare(strict_types=1);

namespace Tests\Unit\Domain\Coach;

use App\Domain\Analytics\ScoringService;
use App\Domain\Coach\CoachService;
use App\Domain\Coach\Contracts\CoachRepository;
use App\Domain\Coach\Contracts\ResponsesProvider;
use PHPUnit\Framework\TestCase;
use Tests\Unit\Domain\Analytics\Support\MemoryAnalyticsRepository;

final class CoachServiceTest extends TestCase
{
    public function test_it_runs_tools_collects_citations_and_marks_proposed_writes(): void
    {
        $analytics = new MemoryAnalyticsRepository;
        $analytics->daily['steps'] = [
            ['date' => '2026-05-27', 'value' => 7000], ['date' => '2026-05-28', 'value' => 8000], ['date' => '2026-05-29', 'value' => 9000],
        ];
        $provider = new SequenceProvider([
            ['output' => [['type' => 'function_call', 'call_id' => 'call-1', 'name' => 'get_metric_trend', 'arguments' => '{"metric":"steps","days":30}']]],
            ['output_text' => 'Your steps increased. Set a modest goal after confirmation.', 'output' => []],
        ]);
        $messages = new MemoryCoachRepository;
        $service = new CoachService($messages, $provider, $analytics, new ScoringService($analytics), 'test-model');

        $result = $service->reply('thread-1', 'How am I doing?');

        self::assertTrue($result['requiresConfirmation']);
        self::assertSame('steps', $result['citations'][0]['metric']);
        self::assertCount(3, $result['citations']);
        self::assertSame('function_call_output', $provider->requests[1]['input'][2]['type']);
        self::assertSame('assistant', $messages->items[1]['role']);
        self::assertSame($result['citations'], $messages->items[1]['citations']);
    }
}

final class SequenceProvider implements ResponsesProvider
{
    /** @var list<array<string, mixed>> */
    public array $requests = [];

    /** @param list<array<string, mixed>> $responses */
    public function __construct(private array $responses) {}

    public function respond(array $request): array
    {
        $this->requests[] = $request;

        return array_shift($this->responses) ?? [];
    }
}

final class MemoryCoachRepository implements CoachRepository
{
    /** @var list<array<string, mixed>> */
    public array $items = [];

    public function messages(string $threadId, int $limit = 30): array
    {
        return array_slice($this->items, -$limit);
    }

    public function saveMessage(string $threadId, string $role, string $content, array $citations = []): array
    {
        $item = ['id' => (string) count($this->items), 'threadId' => $threadId, 'role' => $role, 'content' => $content, 'citations' => $citations, 'createdAt' => count($this->items)];
        $this->items[] = $item;

        return $item;
    }
}
