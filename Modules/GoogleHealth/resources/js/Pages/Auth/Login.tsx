import { Head, Link } from '@inertiajs/react';

type Props = {
    connectUrl: string;
    configured: boolean;
};

export default function Login({ connectUrl, configured }: Props) {
    return <><Head title="Connect Google Health"/><main className="authPage"><section className="authCard"><div className="brandMark large">✦</div><p className="eyebrow">Personal wellness</p><h1>Connect Google Health</h1><p>Your health history, scores, and habits in one private dashboard.</p>{configured ? <Link className="button primary" href={connectUrl}>Continue with Google Health</Link> : <p>Google Health credentials are not configured.</p>}<small>Private health access. Revoke anytime.</small></section></main></>;
}
