import { Link, router, usePage } from '@inertiajs/react';
import type { PropsWithChildren } from 'react';
import type { PageProps } from '../types';

const primary = [['/dashboard','Today','⌂'],['/fitness','Fitness','●'],['/sleep','Sleep','◒'],['/health','Health','♥']];
const active = (url: string, href: string) => href === '/dashboard' ? url === href : url.startsWith(href);

export default function DashboardLayout({ children }: PropsWithChildren) {
    const { url, props } = usePage<PageProps>();
    const initial = props.auth?.user?.name?.trim().charAt(0).toUpperCase() || 'L';
    return <>
        <header className="appTopbar">
            <Link href="/dashboard" className="brand"><span className="brandMark">✦</span><span>LifeStats</span></Link>
            <nav className="desktopNav" aria-label="Section navigation">{primary.map(([href,label]) => <Link key={href} href={href} className={active(url,href) ? 'active' : ''}>{label}</Link>)}</nav>
            <div className="topbarActions"><span className="profileDot" aria-label="Signed-in user">{initial}</span><button className="logoutButton" onClick={() => router.post('/logout')} type="button">Log out</button></div>
        </header>
        {props.flash?.success && <div className="flash success" role="status">{props.flash.success}</div>}
        {props.flash?.error && <div className="flash error" role="alert">{props.flash.error}</div>}
        {children}
        <nav className="bottomNav" aria-label="Primary navigation">{primary.map(([href,label,icon]) => <Link key={href} href={href} className={active(url,href) ? 'active' : ''}><span className="navIcon" aria-hidden="true">{icon}</span><span>{label}</span></Link>)}</nav>
    </>;
}
