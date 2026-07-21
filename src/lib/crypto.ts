import 'server-only';
import {createCipheriv,createDecipheriv,createHash,createHmac,timingSafeEqual,randomBytes} from 'node:crypto';
import {config} from './config';

const secret=()=>config.encryptionKey||config.sessionSecret;
const key=()=>createHash('sha256').update(secret()).digest();

export function encryptSecret(value:string|null|undefined){
  if(!value||value.startsWith('enc:v1:'))return value??null;
  const iv=randomBytes(12),cipher=createCipheriv('aes-256-gcm',key(),iv),body=Buffer.concat([cipher.update(value,'utf8'),cipher.final()]),tag=cipher.getAuthTag();
  return `enc:v1:${Buffer.concat([iv,tag,body]).toString('base64url')}`;
}
export function decryptSecret(value:string|null|undefined){
  if(!value||!value.startsWith('enc:v1:'))return value??null;
  const raw=Buffer.from(value.slice(7),'base64url'),iv=raw.subarray(0,12),tag=raw.subarray(12,28),body=raw.subarray(28),decipher=createDecipheriv('aes-256-gcm',key(),iv);decipher.setAuthTag(tag);
  return Buffer.concat([decipher.update(body),decipher.final()]).toString('utf8');
}
export function createSessionValue(userId:string,maxAgeS=60*60*24*30){const expires=Math.floor(Date.now()/1000)+maxAgeS,payload=`${userId}.${expires}`,signature=createHmac('sha256',config.sessionSecret).update(payload).digest('base64url');return `${payload}.${signature}`}
export function verifySessionValue(value:string|undefined){if(!value)return null;const [userId,expires,signature]=value.split('.');if(!userId||!expires||!signature||Number(expires)<Date.now()/1000)return null;const expected=createHmac('sha256',config.sessionSecret).update(`${userId}.${expires}`).digest('base64url');const a=Buffer.from(signature),b=Buffer.from(expected);return a.length===b.length&&timingSafeEqual(a,b)?userId:null}
