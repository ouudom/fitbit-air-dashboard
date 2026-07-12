import { NextRequest,NextResponse } from 'next/server';import { getHealthRecords } from '../../../../lib/db';
export async function GET(req:NextRequest,{params}:{params:Promise<{type:string}>}){const {type}=await params;const limit=Math.min(Number(req.nextUrl.searchParams.get('limit')??100),500);return NextResponse.json(await getHealthRecords(type,limit))}
