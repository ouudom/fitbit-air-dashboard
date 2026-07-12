export function Loading(){return <div className="state">Loading data…</div>}
export function Empty({message='No data available yet.'}){return <div className="state">{message}</div>}
export function ErrorState({message}:{message:string}){return <div className="state error">Could not load this section: {message}</div>}
