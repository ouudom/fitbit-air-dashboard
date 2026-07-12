import { NextRequest,NextResponse } from 'next/server';import { getDaily } from '../../../lib/db';
export async function GET(req:NextRequest){const metric=req.nextUrl.searchParams.get('metric')??'steps',days=Math.min(Number(req.nextUrl.searchParams.get('days')??30),365);return NextResponse.json(await getDaily(metric,days))}
