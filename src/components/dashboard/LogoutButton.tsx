'use client';
import {useState} from 'react';
export function LogoutButton(){const [busy,setBusy]=useState(false);const logout=async()=>{setBusy(true);try{await fetch('/api/auth/logout',{method:'POST'});window.location.href='/'}finally{setBusy(false)}};return <button className="logoutButton" onClick={logout} disabled={busy}>{busy?'Signing out…':'Log out'}</button>}
