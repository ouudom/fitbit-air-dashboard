export type Metric={date:string;value:number|null};
export type Exercise={id:string;startTime:string|null;displayName:string|null;type:string|null;durationS:number|null;calories:number|null;distanceMm:number|null;avgHr:number|null};
export type HealthRecord={id:string;dataType:string;startTime:string|null;endTime:string|null;date:string|null;numericValue:number|null;payload:Record<string,unknown>};
export type SleepSession={id:string;date:string|null;startTime:string|null;endTime:string|null;minutesAsleep:number|null;minutesAwake:number|null;minutesInSleepPeriod:number|null;minutesToFallAsleep:number|null;minutesAfterWakeUp:number|null;stages:{awake:number;light:number;deep:number;rem:number}};
export type VitalPoint={id:string;date:string|null;time:string|null;value:number|null;unit:string;source:string};
