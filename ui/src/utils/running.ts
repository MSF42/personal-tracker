/**
 * Running aggregate helpers that don't belong to a single page.
 */

export interface BestWindow {
    /** Inclusive ISO date range of the `days`-day window. */
    start: string;
    end: string;
    distanceKm: number;
    count: number;
}

const DAY_MS = 86_400_000;

/** Whole days since the epoch for a YYYY-MM-DD string — UTC so DST can't
 *  shift the count. */
function dayNumber(iso: string): number {
    const [y, m, d] = iso.split('-').map(Number) as [number, number, number];
    return Math.round(Date.UTC(y, m - 1, d) / DAY_MS);
}

function isoFromDayNumber(n: number): string {
    return new Date(n * DAY_MS).toISOString().slice(0, 10);
}

/**
 * The `days`-day window (any start date, not just trailing from today) with
 * the most total distance. An optimal window can always be slid so it ends on
 * a run's date, so only those end dates are checked; ties go to the earliest.
 */
export function bestWindow(
    runs: { date: string; distance_km: number }[],
    days: number,
): BestWindow | null {
    if (runs.length === 0 || days < 1) return null;
    const sorted = runs
        .map((r) => ({ day: dayNumber(r.date), km: r.distance_km }))
        .sort((a, b) => a.day - b.day);

    let best: { endDay: number; km: number; count: number } | null = null;
    let lo = 0;
    let sum = 0;
    for (let hi = 0; hi < sorted.length; hi++) {
        const end = sorted[hi]!;
        sum += end.km;
        while (sorted[lo]!.day <= end.day - days) {
            sum -= sorted[lo]!.km;
            lo++;
        }
        // Several runs on one day: only score the window after the last one.
        if (sorted[hi + 1]?.day === end.day) continue;
        if (best === null || sum > best.km + 1e-9) {
            best = { endDay: end.day, km: sum, count: hi - lo + 1 };
        }
    }
    if (best === null) return null;
    return {
        start: isoFromDayNumber(best.endDay - (days - 1)),
        end: isoFromDayNumber(best.endDay),
        distanceKm: best.km,
        count: best.count,
    };
}
