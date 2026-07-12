import Link from 'next/link';
export default function Login(){return <main className="center card"><h1>Connect Fitbit</h1><p>Authorize access through your Google test account.</p><Link className="button primary" href="/api/auth/login">Continue with Google</Link></main>}
