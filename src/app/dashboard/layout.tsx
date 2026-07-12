import Link from 'next/link';import { Nav } from '../../components/dashboard/Nav';
export default function DashboardLayout({children}:{children:React.ReactNode}){return <><div className="topbar"><Link className="brand" href="/dashboard">Fitbit Air <span>dashboard</span></Link><Nav/></div>{children}</>}
