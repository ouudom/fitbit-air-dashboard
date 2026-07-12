import 'dotenv/config';
import pg from 'pg';
import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const { Pool } = pg;
export const pool = new Pool({ connectionString: process.env.DATABASE_URL });
const migrations = join(dirname(fileURLToPath(import.meta.url)), '..', 'db', 'migrations');

export async function initDb() {
  const sql = await readFile(join(migrations, '001_initial.sql'), 'utf8');
  await pool.query(sql);
}
export async function saveTokens(x) {
  const old = await getTokens();
  await pool.query(`INSERT INTO tokens(id,access_token,refresh_token,expiry,scope,updated_at)
    VALUES(1,$1,$2,$3,$4,$5) ON CONFLICT(id) DO UPDATE SET access_token=$1,
    refresh_token=COALESCE($2,tokens.refresh_token),expiry=$3,scope=$4,updated_at=$5`,
    [x.access_token, x.refresh_token || old?.refresh_token || null, x.expiry, x.scope || null, Date.now()]);
}
export async function getTokens() { return (await pool.query('SELECT * FROM tokens WHERE id=1')).rows[0]; }
export async function clearTokens() { await pool.query('DELETE FROM tokens WHERE id=1'); }
export async function saveDailyMetric(date, metric, value) { await pool.query(`INSERT INTO daily_metrics(date,metric,value,updated_at)
  VALUES($1,$2,$3,$4) ON CONFLICT(date,metric) DO UPDATE SET value=$3,updated_at=$4`, [date, metric, value, Date.now()]); }
export async function getDailyMetric(metric, days) { const r=await pool.query('SELECT date,value FROM daily_metrics WHERE metric=$1 ORDER BY date DESC LIMIT $2',[metric,days]); return r.rows.reverse(); }
export async function saveExercise(e) { await pool.query(`INSERT INTO exercises(id,type,display_name,start_time,duration_s,calories,distance_mm,steps,avg_hr,raw,updated_at)
  VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) ON CONFLICT(id) DO UPDATE SET type=$2,display_name=$3,start_time=$4,duration_s=$5,calories=$6,distance_mm=$7,steps=$8,avg_hr=$9,raw=$10,updated_at=$11`,
  [e.id,e.type,e.display_name,e.start_time,e.duration_s,e.calories,e.distance_mm,e.steps,e.avg_hr,e.raw,Date.now()]); }
export async function getExercises(limit=25) { return (await pool.query('SELECT * FROM exercises ORDER BY start_time DESC LIMIT $1',[limit])).rows; }
export async function setMeta(key,value) { await pool.query(`INSERT INTO meta(key,value) VALUES($1,$2) ON CONFLICT(key) DO UPDATE SET value=$2`,[key,String(value)]); }
export async function getMeta(key) { return (await pool.query('SELECT value FROM meta WHERE key=$1',[key])).rows[0]?.value || null; }
