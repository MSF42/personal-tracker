/**
 * Week helpers. The app's convention is that weeks start on Monday and end
 * on Sunday, everywhere: calendars, "this week" totals, habit chains.
 * All helpers work in local time and format dates as YYYY-MM-DD.
 */

export const WEEKDAY_LABELS = [
    'Mon',
    'Tue',
    'Wed',
    'Thu',
    'Fri',
    'Sat',
    'Sun',
] as const;

/** Format a Date as a local ISO date (YYYY-MM-DD), without any UTC shift. */
export function toIsoDate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

/** Parse a YYYY-MM-DD string as a local-time Date at midnight. */
export function fromIsoDate(iso: string): Date {
    const [y, m, d] = iso.split('-').map(Number) as [number, number, number];
    return new Date(y, m - 1, d);
}

/** 0 for Monday … 6 for Sunday (JS getDay() is 0 for Sunday). */
export function mondayIndex(d: Date): number {
    return (d.getDay() + 6) % 7;
}

/** Midnight on the Monday of the week containing `d`. */
export function startOfWeek(d: Date): Date {
    const start = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    start.setDate(start.getDate() - mondayIndex(start));
    return start;
}

/** Midnight on the Sunday of the week containing `d`. */
export function endOfWeek(d: Date): Date {
    const end = startOfWeek(d);
    end.setDate(end.getDate() + 6);
    return end;
}

/** Inclusive Monday..Sunday ISO date range for the week containing `d`. */
export function weekRange(d: Date = new Date()): {
    start: string;
    end: string;
} {
    return { start: toIsoDate(startOfWeek(d)), end: toIsoDate(endOfWeek(d)) };
}

/** The seven ISO dates (Mon..Sun) of the week `offset` weeks from the one containing `d`. */
export function weekDays(d: Date, offset = 0): string[] {
    const monday = startOfWeek(d);
    monday.setDate(monday.getDate() + offset * 7);
    return Array.from({ length: 7 }, (_, i) => {
        const day = new Date(monday);
        day.setDate(monday.getDate() + i);
        return toIsoDate(day);
    });
}
