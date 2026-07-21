import { Head, Link, router } from '@inertiajs/react';
import { useState } from 'react';
import { Button, Empty, ErrorState, ScoreCard, Section } from '../../components/ui';
import type { DailyScore, DataQuality, PageProps, TimelineEvent } from '../../types';

type Props = PageProps<{ date:string; scores:DailyScore[]; quality:DataQuality[]; timeline:TimelineEvent[]; nutrition:{calories:number;proteinG:number;entries:number}; strength:{sessions:number;volumeKg:number} }>;
export default function Index({date,scores=[],quality=[],timeline=[],nutrition={calories:0,proteinG:0,entries:0},strength={sessions:0,volumeKg:0},errors}:Props){
    const [syncing,setSyncing]=useState(false);
    const sync=()=>router.post('/dashboard/sync',{days:30,full:true},{preserveScroll:true,onStart:()=>setSyncing(true),onFinish:()=>setSyncing(false)});
    const coverage=Math.round(quality.reduce((sum,x)=>sum+x.coverage,0)/Math.max(1,quality.length)*100);
    return <><Head title="Today"/><main className="todayPage">
        <div className="todayIntro"><div><p className="eyebrow">Personal health · {date}</p><h1>Today</h1><p className="subtitle">Signals, effort, recovery, and habits. Explained from source data.</p></div><Button onClick={sync} disabled={syncing}>{syncing?'Syncing…':'Sync Fitbit'}</Button></div>
        <ErrorState message={errors?.sync}/>
        <div className="scoreGrid">{scores.map(score=><ScoreCard key={score.type} score={score} href={score.type==='recovery'?'/dashboard/recovery':score.type==='sleep'?'/dashboard/sleep':'/dashboard/strain'}/>)}</div>
        <section className="metricGrid"><Metric label="Nutrition" value={Math.round(nutrition.calories)} unit="kcal" detail={`${nutrition.entries} entries today`}/><Metric label="Protein" value={Math.round(nutrition.proteinG)} unit="g" detail="Logged today"/><Metric label="Strength" value={strength.sessions} detail="Recent sessions"/><Metric label="Data quality" value={coverage} unit="%" detail="Available inputs"/></section>
        <Section title="Timeline" description="Sleep, workouts, meals, strength, and journal events.">{timeline.length?<div className="timeline">{timeline.map(event=><div className="timelineRow" key={`${event.source}:${event.id}`}><span>{event.startTime?new Date(event.startTime).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}):'•'}</span><div><strong>{event.title}</strong><small>{event.type}{event.detail?` · ${event.detail}`:''}</small></div></div>)}</div>:<Empty>No events yet. Sync Fitbit or add a journal entry.</Empty>}</Section>
        <section className="quickActions"><Quick href="/dashboard/journal" icon="＋" title="Journal" detail="Log a daily habit"/><Quick href="/dashboard/strength" icon="↗" title="Strength" detail="Record sets and load"/><Quick href="/dashboard/coach" icon="✦" title="Ask Coach" detail="Grounded in your data"/></section>
    </main></>;
}
function Metric({label,value,unit,detail}:{label:string;value:number;unit?:string;detail:string}){return <div className="metricCard"><span>{label}</span><strong>{value}{unit&&<small> {unit}</small>}</strong><span>{detail}</span></div>}
function Quick({href,icon,title,detail}:{href:string;icon:string;title:string;detail:string}){return <Link href={href}><span>{icon}</span><strong>{title}</strong><small>{detail}</small></Link>}
