import { Link } from '@inertiajs/react';
import { useState, type ButtonHTMLAttributes, type CSSProperties, type ReactNode } from 'react';
import type { DailyScore, SleepSession } from '../types';

export function Button({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) { return <button className={`button ${className}`} {...props}/>; }
export function PageHeader({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle: string; action?: ReactNode }) { return <header className="pageHeader"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="subtitle">{subtitle}</p></div>{action}</header>; }
export function Section({ title, description, children, action }: { title: string; description?: string; children: ReactNode; action?: ReactNode }) { return <section className="card"><div className="sectionHead"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>{children}</section>; }
export function MetricCard({ label, value, unit, detail }: { label: string; value: ReactNode; unit?: string; detail?: string }) { return <div className="metricCard"><small>{label}</small><strong>{value}{unit && <em>{unit}</em>}</strong>{detail && <span>{detail}</span>}</div>; }
export function Empty({ children = 'No data available yet.' }: { children?: ReactNode }) { return <div className="state">{children}</div>; }
export function ErrorState({ message }: { message?: string }) { return message ? <div className="state error" role="alert">{message}</div> : null; }

export function BarChart({ data, color = '#4c8d75', unit = '' }: { data: { label: string; value: number | null }[]; color?: string; unit?: string }) {
    const [active, setActive] = useState(Math.max(data.length - 1, 0));
    if (!data.length) return <Empty>No chart data.</Empty>;
    const max = Math.max(...data.map(x => x.value ?? 0), 1), selected = data[Math.min(active, data.length - 1)];
    return <div className="interactiveChart"><div className="chart" role="img" aria-label="Interactive bar chart">{data.map((x,i) => <button type="button" className={`bar ${i===active?'selected':''}`} key={`${x.label}-${i}`} onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} onClick={() => setActive(i)} aria-label={`${x.label}: ${x.value ?? 'no data'}${unit}`}><span className="barValue" style={{height:`${Math.max(3,(x.value??0)/max*100)}%`,background:color}}/><small>{x.label}</small></button>)}</div><div className="chartDetail"><strong>{selected.value == null ? 'No data' : selected.value.toLocaleString()}{selected.value != null && unit ? ` ${unit}` : ''}</strong><span>{selected.label}</span></div></div>;
}

const scoreColors: Record<string,string> = { recovery:'#3f9272', sleep:'#7164a4', strain:'#df8359', stress:'#d55d64', energy:'#4b8eac' };
export function ScoreCard({ score, href }: { score: DailyScore; href?: string }) {
    const style = {'--score-color':scoreColors[score.type] ?? '#327b63'} as CSSProperties;
    const body = <div className="scoreCard" style={style}><div className="scoreDial" style={{...style,'--score-progress':`${(score.value??0)*3.6}deg`} as CSSProperties}><strong>{score.value ?? '—'}</strong></div><div><span>{score.type}</span><b>{score.state==='ready' ? score.summary : score.state==='calibrating' ? 'Calibrating personal baseline' : 'More source data needed'}</b><small>{score.confidence} confidence · {score.modelVersion}</small></div></div>;
    return href ? <Link className="scoreLink" href={href}>{body}</Link> : body;
}
export function Contributions({ score }: { score: DailyScore }) { return <div className="contributionList">{score.contributions.map(x => <div key={x.key}><span className={`impact ${x.status}`}>{x.status==='positive'?'↑':x.status==='negative'?'↓':'•'}</span><div><strong>{x.label}</strong><small>{x.value==null?'Missing':`${Math.round(x.value*10)/10} ${x.unit}`} · baseline {x.baseline==null?'calibrating':Math.round(x.baseline*10)/10}</small></div><b>{x.impact>0?'+':''}{x.impact}</b></div>)}</div>; }
export function SleepStageChart({ session }: { session: SleepSession | null }) { if (!session) return <Empty>No sleep session.</Empty>; const stages = ['awake','light','deep','rem'] as const; const total=Math.max(stages.reduce((sum,key)=>sum+session.stages[key],0),1); return <div className="stageChart"><div className="stageBar">{stages.map(stage=><div key={stage} className={`stage ${stage}`} style={{width:`${session.stages[stage]/total*100}%`}} title={`${stage}: ${session.stages[stage]} min`}/>)}</div><div className="stageLegend">{stages.map(stage=><span key={stage}><i className={`legendDot ${stage}`}/>{stage} <b>{session.stages[stage]}m</b></span>)}</div></div>; }
