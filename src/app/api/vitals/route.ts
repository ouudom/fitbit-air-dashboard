import {NextResponse} from 'next/server';import {getVitals} from '../../../lib/health-data';
export async function GET(){return NextResponse.json(await getVitals())}
