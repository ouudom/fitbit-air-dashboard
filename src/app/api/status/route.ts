import { NextResponse } from 'next/server';import { config } from '../../../lib/config';import { authenticated } from '../../../lib/oauth';import { getMeta } from '../../../lib/db';
export async function GET(){const last=await getMeta('lastSync');return NextResponse.json({authenticated:await authenticated(),lastSync:last?Number(last):null,syncDays:config.syncDays})}
