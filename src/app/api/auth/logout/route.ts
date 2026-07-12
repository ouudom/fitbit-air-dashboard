import { NextResponse } from 'next/server';import { deleteTokens } from '../../../../lib/db';
export async function POST(){await deleteTokens();return NextResponse.json({ok:true})}
