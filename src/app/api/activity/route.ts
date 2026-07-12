import {NextRequest,NextResponse} from 'next/server';import {getActivityData} from '../../../lib/health-data';
export async function GET(req:NextRequest){const days=Math.min(Number(req.nextUrl.searchParams.get('days')??90),365);return NextResponse.json(await getActivityData(days))}
