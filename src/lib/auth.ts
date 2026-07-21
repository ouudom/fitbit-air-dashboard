import 'server-only';
import {cookies} from 'next/headers';
import {verifySessionValue} from './crypto';
import {getMeta} from './db';

export const sessionCookie='fitbit_air_session';
export async function currentUser(){const value=(await cookies()).get(sessionCookie)?.value,user=verifySessionValue(value);if(!user)return null;const bound=await getMeta('healthUserId');return bound===user?user:null}
export async function requireUser(){const user=await currentUser();if(!user)throw new Error('NOT_AUTHENTICATED');return user}
