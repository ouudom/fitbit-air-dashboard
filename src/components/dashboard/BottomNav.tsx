import Link from 'next/link';
const items=[['/dashboard','Today','⌂'],['/dashboard/recovery','Recovery','✦'],['/dashboard/strain','Strain','◒'],['/dashboard/journal','Journal','⌁'],['/dashboard/coach','Coach','◎']];
export function BottomNav(){return <nav className="bottomNav" aria-label="Primary navigation">{items.map(([href,label,icon])=><Link key={href} href={href}><span className="navIcon">{icon}</span><span>{label}</span></Link>)}</nav>}
