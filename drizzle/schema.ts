import { bigint, doublePrecision, integer, jsonb, pgTable, primaryKey, text } from 'drizzle-orm/pg-core';

export const tokens=pgTable('tokens',{id:integer('id').primaryKey(),accessToken:text('access_token'),refreshToken:text('refresh_token'),expiry:bigint('expiry',{mode:'number'}),scope:text('scope'),updatedAt:bigint('updated_at',{mode:'number'})});
export const dailyMetrics=pgTable('daily_metrics',{date:text('date').notNull(),metric:text('metric').notNull(),value:doublePrecision('value'),updatedAt:bigint('updated_at',{mode:'number'})},t=>[primaryKey({columns:[t.date,t.metric]})]);
export const exercises=pgTable('exercises',{id:text('id').primaryKey(),type:text('type'),displayName:text('display_name'),startTime:text('start_time'),durationS:bigint('duration_s',{mode:'number'}),calories:doublePrecision('calories'),distanceMm:doublePrecision('distance_mm'),steps:integer('steps'),avgHr:integer('avg_hr'),raw:jsonb('raw'),updatedAt:bigint('updated_at',{mode:'number'})});
export const meta=pgTable('meta',{key:text('key').primaryKey(),value:text('value')});
export const healthRecords=pgTable('health_records',{id:text('id').primaryKey(),dataType:text('data_type').notNull(),startTime:text('start_time'),endTime:text('end_time'),date:text('date'),numericValue:doublePrecision('numeric_value'),payload:jsonb('payload').notNull(),updatedAt:bigint('updated_at',{mode:'number'})});
