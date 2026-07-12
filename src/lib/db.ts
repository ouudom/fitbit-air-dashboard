import 'server-only';
import { drizzle } from 'drizzle-orm/node-postgres';
import { Pool } from 'pg';
import { eq, desc, and } from 'drizzle-orm';
import { tokens,dailyMetrics,exercises,meta,healthRecords } from '../../drizzle/schema';

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
export async function getHealthRecords(dataType:string,limit=100){return db.select().from(healthRecords).where(eq(healthRecords.dataType,dataType)).orderBy(desc(healthRecords.startTime)).limit(limit)}
