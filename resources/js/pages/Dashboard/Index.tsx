import { Head, Link, router } from '@inertiajs/react';
import { useState } from 'react';
import { BarChart, Button, Empty, ErrorState, MetricCard, Section } from '../../components/ui';
import type { Exercise, Metric, PageProps, SleepSession, VitalPoint } from '../../types';

type Props = PageProps<{
    activity: { metrics: Record<string, Metric[]>; exercises: Exercise[] };
    sleep: { sessions: SleepSession[]; latest: SleepSession | null; trend: Metric[] };
    vitals: Record<string, VitalPoint[]>;
    lastSync: number | null;
}>;

const latestMetric = (rows: Metric[] = []) => rows.at(-1)?.value ?? null;

export default function Index({ activity, sleep, vitals, lastSync, errors }: Props) {
    const [syncing, setSyncing] = useState(false);
    const metrics = activity?.metrics ?? {};
    const exercises = activity?.exercises ?? [];
    const sync = () => router.post('/dashboard/sync', { days: 30, full: true }, {
        preserveScroll: true,
        onStart: () => setSyncing(true),
        onFinish: () => setSyncing(false),
    });
    const syncedAt = lastSync ? new Date(lastSync < 10_000_000_000 ? lastSync * 1000 : lastSync).toLocaleString() : 'Never synced';

    return <><Head title="Today"/><main className="todayPage">
        <div className="todayIntro"><div><p className="eyebrow">Google Health</p><h1>Today</h1><p className="subtitle">Latest activity, sleep, workouts, and health signals from source data.</p></div><Button onClick={sync} disabled={syncing}>{syncing ? 'Syncing…' : 'Sync Google Health'}</Button></div>
        <ErrorState message={errors?.sync}/>
        <section className="metricGrid">
            <MetricCard label="Steps" value={latestMetric(metrics.steps)?.toLocaleString() ?? '—'} detail="Latest day"/>
            <MetricCard label="Active Zone Minutes" value={latestMetric(metrics['active-zone-minutes']) ?? '—'} detail="Latest day"/>
            <MetricCard label="Sleep" value={sleep?.latest?.minutesAsleep ? Math.round(sleep.latest.minutesAsleep / 60 * 10) / 10 : '—'} unit={sleep?.latest?.minutesAsleep ? 'h' : undefined} detail={sleep?.latest?.date ?? 'No session'}/>
            <MetricCard label="Resting heart rate" value={vitals?.['daily-resting-heart-rate']?.[0]?.value ?? '—'} unit="bpm" detail="Latest reading"/>
        </section>
        <Section title="Steps" description="Last 14 synced days." action={<Link href="/fitness">Open Fitness</Link>}><BarChart data={(metrics.steps ?? []).map(point => ({ label: point.date.slice(5), value: point.value }))}/></Section>
        <Section title="Recent workouts" description={`${exercises.length} synced sessions`} action={<Link href="/fitness">View all</Link>}>{exercises.length ? <div className="activityList">{exercises.slice(0, 5).map(exercise => <div className="activityRow" key={exercise.id}><span className="activityDot">●</span><div><strong>{exercise.displayName || exercise.type || 'Workout'}</strong><small>{exercise.startTime ? new Date(exercise.startTime).toLocaleString() : 'Time unavailable'}</small></div><b>{exercise.durationS ? `${Math.round(exercise.durationS / 60)} min` : ''}</b></div>)}</div> : <Empty>No workouts synced.</Empty>}</Section>
        <Section title="Source status" description="Local views are projections. Google Health remains source of truth."><div className="state">Last sync: {syncedAt}</div></Section>
    </main></>;
}
