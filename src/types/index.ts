export type Metric={date:string;value:number|null};
export type Exercise={id:string;startTime:string|null;displayName:string|null;type:string|null;durationS:number|null;calories:number|null;distanceMm:number|null;avgHr:number|null};
export type HealthRecord={id:string;dataType:string;startTime:string|null;endTime:string|null;date:string|null;numericValue:number|null;payload:Record<string,unknown>};
