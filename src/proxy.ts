import { NextResponse } from 'next/server';import type { NextRequest } from 'next/server';import {verifySessionValue} from './lib/crypto';
const sessionCookie='fitbit_air_session';
const publicApi=['/api/auth/login','/api/auth/callback','/api/cron/sync'];
export function proxy(req:NextRequest){const path=req.nextUrl.pathname;if(publicApi.some(p=>path.startsWith(p)))return NextResponse.next();const user=verifySessionValue(req.cookies.get(sessionCookie)?.value);if(user){if(path.startsWith('/api/')&&!['GET','HEAD','OPTIONS'].includes(req.method)){const origin=req.headers.get('origin');if(origin&&origin!==req.nextUrl.origin)return NextResponse.json({error:'INVALID_ORIGIN'},{status:403})}return NextResponse.next()}if(path.startsWith('/api/'))return NextResponse.json({error:'NOT_AUTHENTICATED'},{status:401});return NextResponse.redirect(new URL('/',req.url))}
export const config={matcher:['/dashboard/:path*','/api/:path*']};
