import 'server-only';
import { accessToken } from './oauth';
import { endpoints } from './config';
async function request(path:string,init:RequestInit={}){const r=await fetch(`${endpoints.health}${path}`,{...init,headers:{Authorization:`Bearer ${await accessToken()}`,Accept:'application/json','Content-Type':'application/json',...(init.headers??{})},cache:'no-store'});if(r.status===429){await new Promise(x=>setTimeout(x,2000));return request(path,init)}const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(`Health API ${r.status}: ${JSON.stringify(d)}`);return d}
export const identity=()=>request('/users/me/identity');
export async function listDataPoints(type:string,filter?:string){const all:any[]=[];let page='';do{const qs=new URLSearchParams({page_size:'1000'});if(filter)qs.set('filter',filter);if(page)qs.set('page_token',page);const d=await request(`/users/me/dataTypes/${type}/dataPoints?${qs}`);all.push(...(d.dataPoints??[]));page=d.nextPageToken??''}while(page);return all}
const civil=(d:Date,h:number,m=0,s=0)=>({date:{year:d.getFullYear(),month:d.getMonth()+1,day:d.getDate()},time:{hours:h,minutes:m,seconds:s,nanos:0}});
export async function dailyRollup(type:string,start:Date,end:Date){const d=await request(`/users/me/dataTypes/${type}/dataPoints:dailyRollUp`,{method:'POST',body:JSON.stringify({range:{start:civil(start,0),end:civil(end,23,59,59)},windowSizeDays:1})});return d.rollupDataPoints??[]}
