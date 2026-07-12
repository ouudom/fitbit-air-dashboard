import { NextRequest,NextResponse } from 'next/server';import { getExercises } from '../../../lib/db';
export async function GET(req:NextRequest){const limit=Math.min(Number(req.nextUrl.searchParams.get('limit')??25),200);return NextResponse.json(await getExercises(limit))}
