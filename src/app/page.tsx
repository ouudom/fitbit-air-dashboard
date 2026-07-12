import Link from 'next/link';
export default function Home(){return <main className="center"><h1>Fitbit Air <span>dashboard</span></h1><p>Personal activity dashboard powered by Fitbit and Google Health API.</p><Link className="button primary" href="/api/auth/login">Connect Fitbit</Link></main>}
