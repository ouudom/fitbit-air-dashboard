<?php

declare(strict_types=1);

namespace App\Domain\Coach\Repositories;

use App\Domain\Coach\Contracts\CoachRepository;
use Illuminate\Database\ConnectionInterface;
use Illuminate\Support\Str;

final class DatabaseCoachRepository implements CoachRepository
{
    public function __construct(private readonly ConnectionInterface $database) {}

    public function messages(string $threadId, int $limit = 30): array
    {
        return array_reverse(array_map(static function (object $row): array {
            $message = (array) $row;
            $message['threadId'] = $message['thread_id'];
            $message['createdAt'] = $message['created_at'];
            $message['citations'] = is_string($message['citations']) ? json_decode($message['citations'], true, 512, JSON_THROW_ON_ERROR) : $message['citations'];
            unset($message['thread_id'], $message['created_at']);

            return $message;
        }, $this->database->table('coach_messages')->where('thread_id', $threadId)->orderByDesc('created_at')->limit($limit)->get()->all()));
    }

    public function saveMessage(string $threadId, string $role, string $content, array $citations = []): array
    {
        $now = (int) floor(microtime(true) * 1000);
        $this->database->table('coach_threads')->upsert(
            [['id' => $threadId, 'title' => 'Health coach', 'created_at' => $now, 'updated_at' => $now]],
            ['id'], ['updated_at'],
        );
        $message = [
            'id' => (string) Str::uuid(), 'thread_id' => $threadId, 'role' => $role, 'content' => $content,
            'citations' => json_encode($citations, JSON_THROW_ON_ERROR), 'created_at' => $now,
        ];
        $this->database->table('coach_messages')->insert($message);

        return ['id' => $message['id'], 'threadId' => $threadId, 'role' => $role, 'content' => $content, 'citations' => $citations, 'createdAt' => $now];
    }
}
