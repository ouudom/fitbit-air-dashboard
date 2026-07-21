import { NextResponse } from 'next/server';import { deleteTokens } from '../../../../lib/db';import {sessionCookie} from '../../../../lib/auth';
export async function POST(){await deleteTokens();const response=NextResponse.json({ok:true});response.cookies.delete(sessionCookie);return response}
