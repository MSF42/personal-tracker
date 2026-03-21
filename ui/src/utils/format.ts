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
