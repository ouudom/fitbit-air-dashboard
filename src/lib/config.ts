import 'server-only';
export const config={clientId:process.env.GOOGLE_CLIENT_ID??'',clientSecret:process.env.GOOGLE_CLIENT_SECRET??'',redirectUri:process.env.REDIRECT_URI??'http://localhost:3000/api/auth/callback',scopes:(process.env.SCOPES??'https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly').trim(),syncDays:Number(process.env.SYNC_DAYS??30)};
export const endpoints={auth:'https://accounts.google.com/o/oauth2/v2/auth',token:'https://oauth2.googleapis.com/token',health:'https://health.googleapis.com/v4'};
