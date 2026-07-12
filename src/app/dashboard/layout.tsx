import Link from 'next/link';import { Nav } from '../../components/dashboard/Nav';import { LogoutButton } from '../../components/dashboard/LogoutButton';
export default function DashboardLayout({children}:{children:React.ReactNode}){return <><div className="topbar"><Link className="brand" href="/dashboard">Fitbit Air <span>dashboard</span></Link><Nav/><LogoutButton/></div>{children}</>}
