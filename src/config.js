import 'dotenv/config';
const required=n=>process.env[n]||'';
export const config={clientId:required('GOOGLE_CLIENT_ID'),clientSecret:required('GOOGLE_CLIENT_SECRET'),port:+(process.env.PORT||3000),redirectUri:process.env.REDIRECT_URI||'http://localhost:3000/oauth/callback',scopes:(process.env.SCOPES||'https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly').trim(),syncDays:+(process.env.SYNC_DAYS||30)};
export const endpoints={authBase:'https://accounts.google.com/o/oauth2/v2/auth',token:'https://oauth2.googleapis.com/token',healthBase:'https://health.googleapis.com/v4'};
