import Link from 'next/link';
const links=[['/dashboard','Overview'],['/dashboard/activity','Activity'],['/dashboard/sleep','Sleep'],['/dashboard/heart','Heart'],['/dashboard/recovery','Recovery'],['/dashboard/data','Data']];
export function Nav(){return <nav>{links.map(([href,label])=><Link key={href} href={href}>{label}</Link>)}</nav>}
