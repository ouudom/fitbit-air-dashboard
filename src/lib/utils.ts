export const apiBase=()=>process.env.NEXT_PUBLIC_APP_URL??'';
export const km=(mm:number)=>(mm/1_000_000).toFixed(2)+' km';
export const average=(rows:{value:number|null}[])=>{const values=rows.map(x=>x.value).filter((x):x is number=>typeof x==='number');return values.length?Math.round(values.reduce((a,b)=>a+b,0)/values.length):0};
