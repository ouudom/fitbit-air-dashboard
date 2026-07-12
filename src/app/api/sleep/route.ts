import {NextRequest,NextResponse} from 'next/server';import {getSleepData} from '../../../lib/health-data';
export async function GET(req:NextRequest){const limit=Math.min(Number(req.nextUrl.searchParams.get('limit')??90),365);return NextResponse.json(await getSleepData(limit))}
