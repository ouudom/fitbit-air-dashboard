import { BottomNav } from '../../components/dashboard/BottomNav';import { Topbar } from '../../components/dashboard/Topbar';
export default function DashboardLayout({children}:{children:React.ReactNode}){return <><Topbar/>{children}<BottomNav/></>}
