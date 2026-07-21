import { Head, Link } from '@inertiajs/react';

export default function Login() { return <><Head title="Connect Fitbit"/><main className="authPage"><section className="authCard"><div className="brandMark large">✦</div><p className="eyebrow">Personal wellness</p><h1>Connect Fitbit</h1><p>Your health history, scores, and habits in one private dashboard.</p><Link className="button primary" href="/auth/fitbit/redirect">Continue with Fitbit</Link><small>Read-only health access. Revoke anytime.</small></section></main></>; }
