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

/**
 * Parse a "H:MM:SS" or "M:SS" string (the shape formatDuration produces)
 * back into whole seconds. A bare number with no colon is treated as plain
 * minutes, for quick entry. Returns null for empty/unparseable input.
 */
export function parseDuration(text: string): number | null {
    const trimmed = text.trim();
    if (!trimmed) return null;

    const parts = trimmed.split(':');
    if (parts.some((p) => p === '' || Number.isNaN(Number(p)))) return null;
    const nums = parts.map(Number);

    if (nums.length === 1) return Math.round(nums[0]! * 60); // bare minutes
    if (nums.length === 2) return nums[0]! * 60 + nums[1]!; // M:SS
    if (nums.length === 3) return nums[0]! * 3600 + nums[1]! * 60 + nums[2]!; // H:MM:SS
    return null;
}
