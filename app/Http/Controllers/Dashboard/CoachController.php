<?php

declare(strict_types=1);

namespace App\Http\Controllers\Dashboard;

use App\Domain\Coach\CoachService;
use App\Domain\Coach\Contracts\CoachRepository;
use App\Http\Controllers\Controller;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Inertia\Inertia;
use Inertia\Response;
use Throwable;

final class CoachController extends Controller
{
    public function index(CoachRepository $messages): Response
    {
        return Inertia::render('Dashboard/Coach', ['messages' => $messages->messages('default', 50)]);
    }

    public function store(Request $request, CoachService $coach): RedirectResponse
    {
        $data = $request->validate([
            'threadId' => ['nullable', 'string', 'max:100'],
            'message' => ['required', 'string', 'max:4000'],
        ]);
        try {
            $coach->reply($data['threadId'] ?? 'default', trim($data['message']));

            return back();
        } catch (Throwable $error) {
            report($error);

            return back()->withErrors(['message' => $error->getMessage()]);
        }
    }
}
