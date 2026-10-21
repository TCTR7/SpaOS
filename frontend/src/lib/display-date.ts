/** Format a calendar date without UTC conversion. */
export function displayDate(day: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day);
  return match ? match[3] + "/" + match[2] + "/" + match[1] : day;
}
