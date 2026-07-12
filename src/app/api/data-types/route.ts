import {NextResponse} from 'next/server';import {getDataExplorer} from '../../../lib/health-data';
export async function GET(){return NextResponse.json(await getDataExplorer())}
