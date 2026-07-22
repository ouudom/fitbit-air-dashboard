import { Head, Link } from '@inertiajs/react';
import { BarChart, Empty, MetricCard, PageHeader, Section } from '../../components/ui';
import type { VitalPoint } from '../../types';

export default function Heart({ vitals = {} }: { vitals: Record<string, VitalPoint[]> }) {
    const latest = (type: string) => vitals[type]?.[0]?.value ?? '—';
    const chart = (type: string) => vitals[type]?.slice(0, 30).reverse().map(point => ({
        label: point.date?.slice(5) ?? '—',
        value: point.value,
    })) ?? [];

    return <><Head title="Heart & vitals"/><main>
        <PageHeader eyebrow="Health" title="Heart & vitals" subtitle="Trends from Google Health sensors and derived metrics." action={<Link className="button" href="/health/nutrition">Nutrition</Link>}/>
        <section className="metricGrid">
            <MetricCard label="Resting heart rate" value={latest('daily-resting-heart-rate')} unit="bpm" detail="Latest"/>
            <MetricCard label="HRV" value={latest('daily-heart-rate-variability')} unit="ms" detail="Latest"/>
            <MetricCard label="SpO₂" value={latest('daily-oxygen-saturation')} unit="%" detail="Latest"/>
            <MetricCard label="Breathing rate" value={latest('daily-respiratory-rate')} unit="/min" detail="Latest"/>
        </section>
        <Section title="Resting heart rate"><BarChart data={chart('daily-resting-heart-rate')} color="#d56d6d" unit="bpm"/></Section>
        <Section title="Heart-rate variability"><BarChart data={chart('daily-heart-rate-variability')} color="#8c79b8" unit="ms"/></Section>
        <Section title="Oxygen saturation"><BarChart data={chart('daily-oxygen-saturation')} color="#4d9a9a" unit="%"/></Section>
        <Section title="Raw heart-rate samples" description="Available after a full raw sync.">{vitals['heart-rate']?.length ? <table><thead><tr><th>Time</th><th>BPM</th><th>Source</th></tr></thead><tbody>{vitals['heart-rate'].slice(0, 30).map(reading => <tr key={reading.id}><td>{reading.time ? new Date(reading.time).toLocaleString() : '—'}</td><td>{reading.value ?? '—'}</td><td>{reading.source}</td></tr>)}</tbody></table> : <Empty>No raw heart-rate samples.</Empty>}</Section>
    </main></>;
}
