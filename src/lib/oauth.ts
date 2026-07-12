import 'server-only';
import { config,endpoints } from './config';
import { getTokens,saveTokens } from './db';
export function authUrl(state:string){const p=new URLSearchParams({client_id:config.clientId,redirect_uri:config.redirectUri,response_type:'code',access_type:'offline',prompt:'consent',include_granted_scopes:'true',scope:config.scopes,state});return `${endpoints.auth}?${p}`}
async function token(body:Record<string,string>){const r=await fetch(endpoints.token,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(body)});const d=await r.json();if(!r.ok)throw Error(`Google token request failed: ${r.status}`);await saveTokens({accessToken:d.access_token,refreshToken:d.refresh_token,expiry:Date.now()+(d.expires_in??3600)*1000,scope:d.scope});return d}
export function exchangeCode(code:string){return token({code,client_id:config.clientId,client_secret:config.clientSecret,redirect_uri:config.redirectUri,grant_type:'authorization_code'})}
export async function accessToken(){const t=await getTokens();if(!t?.accessToken)throw Error('NOT_AUTHENTICATED');if(Date.now()<(t.expiry??0)-60000)return t.accessToken;if(!t.refreshToken)throw Error('NOT_AUTHENTICATED');return (await token({refresh_token:t.refreshToken,client_id:config.clientId,client_secret:config.clientSecret,grant_type:'refresh_token'})).access_token}
export async function authenticated(){return Boolean((await getTokens())?.refreshToken)}
