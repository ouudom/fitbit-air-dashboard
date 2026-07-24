export function formatSleepDuration(hours: number): string {
  const totalMinutes = Math.max(0, Math.round(hours * 60));
  const wholeHours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (wholeHours === 0) return `${minutes}mn`;
  if (minutes === 0) return `${wholeHours}h`;
  return `${wholeHours}h ${minutes}mn`;
}
