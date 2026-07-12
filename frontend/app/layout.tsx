import './globals.css';
import type { Metadata } from 'next';
export const metadata: Metadata={title:'Fitbit Air Dashboard',description:'Personal Fitbit activity dashboard'};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
