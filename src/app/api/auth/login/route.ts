import { NextResponse } from 'next/server';
import { authUrl } from '../../../../lib/oauth';
export async function GET(){const state=crypto.randomUUID();const r=NextResponse.redirect(authUrl(state));r.cookies.set('oauth_state',state,{httpOnly:true,sameSite:'lax',secure:process.env.NODE_ENV==='production',maxAge:600,path:'/'});return r}
