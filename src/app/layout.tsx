import './globals.css';import './dashboard/ux.css';import type { Metadata } from 'next';
export const metadata:Metadata={title:'LifeStats',description:'Private, evidence-aware Fitbit wellness dashboard.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
