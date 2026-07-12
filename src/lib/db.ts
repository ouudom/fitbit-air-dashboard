import 'server-only';
import { drizzle } from 'drizzle-orm/node-postgres';
import { Pool } from 'pg';
import { eq, desc, sql } from 'drizzle-orm';
import { tokens,dailyMetrics,exercises,meta,healthRecords,syncState } from '../../drizzle/schema';

const globalForDb=globalThis as unknown as {pool?:Pool};
const pool=globalForDb.pool??new Pool({connectionString:process.env.DATABASE_URL});
if(process.env.NODE_ENV!=='production')globalForDb.pool=pool;
export const db=drizzle(pool);
export async function getTokens(){return (await db.select().from(tokens).where(eq(tokens.id,1)).limit(1))[0]}
export async function saveTokens(v:{accessToken:string;refreshToken?:string|null;expiry:number;scope?:string|null}){const old=await getTokens();await db.insert(tokens).values({id:1,accessToken:v.accessToken,refreshToken:v.refreshToken??old?.refreshToken??null,expiry:v.expiry,scope:v.scope??null,updatedAt:Date.now()}).onConflictDoUpdate({target:tokens.id,set:{accessToken:v.accessToken,refreshToken:v.refreshToken??old?.refreshToken??null,expiry:v.expiry,scope:v.scope??null,updatedAt:Date.now()}})}
export async function deleteTokens(){await db.delete(tokens).where(eq(tokens.id,1))}
export async function getDaily(metric:string,days:number){return (await db.select({date:dailyMetrics.date,value:dailyMetrics.value}).from(dailyMetrics).where(eq(dailyMetrics.metric,metric)).orderBy(desc(dailyMetrics.date)).limit(days)).reverse()}
export async function saveDaily(date:string,metric:string,value:number){await db.insert(dailyMetrics).values({date,metric,value,updatedAt:Date.now()}).onConflictDoUpdate({target:[dailyMetrics.date,dailyMetrics.metric],set:{value,updatedAt:Date.now()}})}
export async function getExercises(limit:number){return db.select().from(exercises).orderBy(desc(exercises.startTime)).limit(limit)}
export async function saveExercise(v:typeof exercises.$inferInsert){await db.insert(exercises).values(v).onConflictDoUpdate({target:exercises.id,set:v})}
export async function getMeta(key:string){return (await db.select().from(meta).where(eq(meta.key,key)).limit(1))[0]?.value??null}
export async function setMeta(key:string,value:string|number){await db.insert(meta).values({key,value:String(value)}).onConflictDoUpdate({target:meta.key,set:{value:String(value)}})}
export async function saveHealthRecord(v:typeof healthRecords.$inferInsert){await db.insert(healthRecords).values(v).onConflictDoUpdate({target:healthRecords.id,set:{dataType:v.dataType,startTime:v.startTime,endTime:v.endTime,date:v.date,numericValue:v.numericValue,payload:v.payload,updatedAt:v.updatedAt}})}
export async function saveHealthRecords(values:(typeof healthRecords.$inferInsert)[]){for(let i=0;i<values.length;i+=500){const chunk=values.slice(i,i+500);if(!chunk.length)continue;await db.insert(healthRecords).values(chunk).onConflictDoUpdate({target:healthRecords.id,set:{dataType:sql`excluded.data_type`,startTime:sql`excluded.start_time`,endTime:sql`excluded.end_time`,date:sql`excluded.date`,numericValue:sql`excluded.numeric_value`,payload:sql`excluded.payload`,updatedAt:sql`excluded.updated_at`}})}}
export async function saveDailyMetrics(values:{date:string;metric:string;value:number;updatedAt:number}[]){for(let i=0;i<values.length;i+=500){const chunk=values.slice(i,i+500);if(!chunk.length)continue;await db.insert(dailyMetrics).values(chunk).onConflictDoUpdate({target:[dailyMetrics.date,dailyMetrics.metric],set:{value:sql`excluded.value`,updatedAt:sql`excluded.updated_at`}})}}
export async function saveExercises(values:(typeof exercises.$inferInsert)[]){for(let i=0;i<values.length;i+=100){const chunk=values.slice(i,i+100);if(!chunk.length)continue;await db.insert(exercises).values(chunk).onConflictDoUpdate({target:exercises.id,set:{type:sql`excluded.type`,displayName:sql`excluded.display_name`,startTime:sql`excluded.start_time`,durationS:sql`excluded.duration_s`,calories:sql`excluded.calories`,distanceMm:sql`excluded.distance_mm`,steps:sql`excluded.steps`,avgHr:sql`excluded.avg_hr`,raw:sql`excluded.raw`,updatedAt:sql`excluded.updated_at`}})}}
export async function setSyncState(dataType:string,status:string,recordCount=0,error:string|null=null){await db.insert(syncState).values({dataType,status,recordCount,error,lastSyncedAt:status==='complete'?Date.now():null,updatedAt:Date.now()}).onConflictDoUpdate({target:syncState.dataType,set:{status,recordCount,error,lastSyncedAt:status==='complete'?Date.now():null,updatedAt:Date.now()}})}
export async function getSyncStates(){return db.select().from(syncState).orderBy(syncState.dataType)}
export async function getHealthRecords(dataType:string,limit=100){return db.select().from(healthRecords).where(eq(healthRecords.dataType,dataType)).orderBy(sql`date DESC NULLS LAST`,sql`start_time DESC NULLS LAST`).limit(limit)}
export async function getHealthCoverage(){return db.select({dataType:healthRecords.dataType,count:sql<number>`count(*)::int`,latest:sql<string>`max(coalesce(date,start_time))`}).from(healthRecords).groupBy(healthRecords.dataType).orderBy(healthRecords.dataType)}
