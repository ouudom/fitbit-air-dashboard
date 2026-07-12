import Link from 'next/link';
const items=[['/dashboard','Today','⌂'],['/dashboard/activity','Fitness','◒'],['/dashboard/sleep','Sleep','◌'],['/dashboard/heart','Health','♡']];
export function BottomNav(){return <nav className="bottomNav" aria-label="Primary navigation">{items.map(([href,label,icon])=><Link key={href} href={href}><span className="navIcon">{icon}</span><span>{label}</span></Link>)}</nav>}
