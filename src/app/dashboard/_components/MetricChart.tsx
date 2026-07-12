'use client';
import type { Metric } from '../../../types';
export function MetricChart({data,color}:{data:Metric[];color:string}){const max=Math.max(...data.map(x=>x.value??0),1);return <div className="chart">{data.map(x=><div className="bar" key={x.date}><div className="barValue" style={{height:`${Math.max(3,(x.value??0)/max*100)}%`,background:color}}/><small>{x.date.slice(5)}</small></div>)}</div>}
