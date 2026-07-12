import 'server-only';
import { config } from './config';
import { dailyRollup, identity, listDataPoints } from './health';
import { saveDaily, saveExercise, saveHealthRecord, setMeta } from './db';

const rollupMetrics=['steps','distance','active-zone-minutes','active-minutes','total-calories','active-energy-burned','altitude','calories-in-heart-rate-zone','floors','run-vo2-max','sedentary-period','swim-lengths-data','time-in-heart-rate-zone','total-calories'];
const recordTypes=['activity-level','blood-glucose','body-fat','core-body-temperature','daily-heart-rate-variability','daily-heart-rate-zones','daily-oxygen-saturation','daily-respiratory-rate','daily-resting-heart-rate','daily-sleep-temperature-derivations','daily-vo2-max','electrocardiogram','heart-rate','heart-rate-variability','height','hydration-log','irregular-rhythm-notification','nutrition-log','oxygen-saturation','respiratory-rate-sleep-summary','run-vo2-max','sleep','vo2-max','weight','food','food-measurement-unit'];

const number=(v:any):number|null=>{if(v==null)return null;if(typeof v==='object'){for(const k of ['countSum','sum','total','average','avg','value','bpm','beatsPerMinute','percentage','millimeters','millis'])if(v[k]!=null)return number(v[k])}const n=Number(v);return Number.isFinite(n)?n:null};
const dateOf=(p:any)=>{const d=p?.civilStartTime?.date??p?.startTime?.civilTime?.date??p?.interval?.civilStartTime?.date;return d?`${d.year}-${String(d.month).padStart(2,'0')}-${String(d.day).padStart(2,'0')}`:null};
const timeOf=(p:any)=>p?.startTime??p?.interval?.startTime??p?.sample?.startTime??p?.session?.startTime??null;
const numericOf=(p:any)=>{for(const key of ['value','count','average','mean','bpm','beatsPerMinute','percentage','millimeters','millis']){const v=number(p?.[key]);if(v!=null)return v}for(const v of Object.values(p??{})){const n=number(v);if(n!=null)return n}return null};
const idOf=(type:string,p:any)=>`${type}:${p?.name??p?.id??crypto.randomUUID()}`;

export async function runSync(days=config.syncDays){
  const end=new Date(),start=new Date(end);start.setDate(end.getDate()-days+1);
  const result:any={days,metrics:{},records:{},exercises:0,errors:[]};
  try{const id=await identity();if(id.healthUserId)await setMeta('healthUserId',id.healthUserId)}catch(e){result.errors.push(`identity: ${(e as Error).message}`)}

  for(const metric of rollupMetrics)try{let count=0;for(const p of await dailyRollup(metric,start,end)){const date=dateOf(p),key=metric.replace(/-([a-z])/g,(_,c)=>c.toUpperCase()),value=number(p[key]??p[metric]??Object.values(p).find((v:any)=>v&&typeof v==='object'&&!v.date));if(date&&value!=null){await saveDaily(date,metric,value);count++}}result.metrics[metric]=count}catch(e){result.metrics[metric]=0;result.errors.push(`${metric}: ${(e as Error).message}`)}

  for(const type of recordTypes)try{let count=0;for(const p of await listDataPoints(type)){const startTime=timeOf(p),endTime=p?.endTime??p?.interval?.endTime??null;await saveHealthRecord({id:idOf(type,p),dataType:type,startTime,endTime,date:dateOf(p),numericValue:numericOf(p),payload:p,updatedAt:Date.now()});count++}result.records[type]=count}catch(e){result.records[type]=0;result.errors.push(`${type}: ${(e as Error).message}`)}

  try{const filter=`exercise.interval.civil_start_time >= "${start.toISOString().slice(0,10)}T00:00:00"`;for(const p of await listDataPoints('exercise',filter)){const x=p.exercise??{},m=x.metricsSummary??{};await saveExercise({id:p.name?.split('/').pop()??crypto.randomUUID(),type:x.exerciseType,displayName:x.displayName,startTime:x.interval?.startTime,durationS:number(x.activeDuration),calories:number(m.caloriesKcal),distanceMm:number(m.distanceMillimiters??m.distanceMillimeters),steps:number(m.steps),avgHr:number(m.averageHeartRateBeatsPerMinute),raw:p,updatedAt:Date.now()});result.exercises++}}catch(e){result.errors.push(`exercise: ${(e as Error).message}`)}
  await setMeta('lastSync',Date.now());return result;
}
