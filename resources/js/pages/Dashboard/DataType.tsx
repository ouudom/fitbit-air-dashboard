import { Head, Link } from '@inertiajs/react';
import { Empty, PageHeader, Section } from '../../components/ui';

type RecordRow = {
    id: string;
    date?: string | null;
    startTime?: string | null;
    numericValue?: number | null;
    payload?: unknown;
};

export default function DataType({ type, records = [] }: { type: string; records: RecordRow[] }) {
    return <>
        <Head title={type} />
        <main>
            <PageHeader eyebrow="Raw health data" title={type.replaceAll('-', ' ')} subtitle={`${records.length} most recent stored records.`} />
            <p><Link className="textLink" href="/dashboard/data">← All data</Link></p>
            <Section title="Records">
                {records.length ? <div className="tableWrap"><table>
                    <thead><tr><th>Date</th><th>Value</th><th>Identifier</th><th>Payload</th></tr></thead>
                    <tbody>{records.map(record => <tr key={record.id}>
                        <td>{record.date ?? record.startTime ?? '—'}</td>
                        <td>{record.numericValue ?? '—'}</td>
                        <td><code>{record.id}</code></td>
                        <td><details><summary>Inspect</summary><pre>{JSON.stringify(record.payload, null, 2)}</pre></details></td>
                    </tr>)}</tbody>
                </table></div> : <Empty>No records stored for this type.</Empty>}
            </Section>
        </main>
    </>;
}
