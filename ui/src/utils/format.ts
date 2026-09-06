const MONTH_ABBRS = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
];

/**
 * Format an ISO date string (YYYY-MM-DD) as "DD MMM YYYY" (e.g. "20 Mar 2026").
 */
export function formatDate(isoDate: string): string {
    const [year, month, day] = isoDate.split('-');
    return `${day} ${MONTH_ABBRS[parseInt(month!, 10) - 1]} ${year}`;
}

/**
 * Format a duration in seconds as "H:MM:SS", or "M:SS" under an hour.
 */
export function formatDuration(seconds: number): string {
    const total = Math.round(seconds);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    if (h > 0) {
        return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
    return `${m}:${String(s).padStart(2, '0')}`;
}
