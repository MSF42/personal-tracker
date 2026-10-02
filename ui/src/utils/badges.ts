/**
 * Words and icons for run badges. The API sends structured badges (kind, the
 * date beaten, a value); the UI phrases them so dates and units match the
 * rest of the app.
 */
import type { RunBadge } from '@/types/Running';

import { formatDate, formatDuration } from './format';

const MONTH_NAMES = [
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

/** 1 -> "1st", 1300 -> "1,300th". */
function ordinal(n: number): string {
    const tens = n % 100;
    const suffix =
        tens >= 11 && tens <= 13
            ? 'th'
            : (({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[
                  n % 10
              ] ?? 'th');
    return `${n.toLocaleString('en-US')}${suffix}`;
}

/** "Half Marathon" -> "half marathon"; "5K" and "1 Mile" read fine as-is. */
function effortName(effort: string | null): string {
    if (!effort) return '';
    return /marathon/i.test(effort) ? effort.toLowerCase() : effort;
}

function sinceText(badge: RunBadge, period: 'run' | 'week' | 'month'): string {
    if (badge.ever || !badge.since) return 'ever';
    if (period === 'week') return `since week of ${formatDate(badge.since)}`;
    if (period === 'month') {
        const [year, month] = badge.since.split('-');
        return `since ${MONTH_NAMES[parseInt(month!, 10) - 1]} ${year}`;
    }
    return `since ${formatDate(badge.since)}`;
}

/** The badge's headline, e.g. "Longest run since 07 May 2019". */
export function badgeLabel(badge: RunBadge): string {
    switch (badge.kind) {
        case 'longest':
            return `Longest run ${sinceText(badge, 'run')}`;
        case 'longest_time':
            return `Longest time running ${sinceText(badge, 'run')}`;
        case 'fastest':
            return `Fastest ${effortName(badge.effort)} ${sinceText(badge, 'run')}`;
        case 'first_distance':
            return `First ${effortName(badge.effort)} ${sinceText(badge, 'run')}`;
        case 'biggest_week':
            return `Biggest week ${sinceText(badge, 'week')}`;
        case 'biggest_month':
            return `Biggest month ${sinceText(badge, 'month')}`;
        case 'comeback':
            return `First run in ${badge.value ?? '?'} days`;
        case 'most_climb':
            return `Most climb ${sinceText(badge, 'run')}`;
        case 'negative_split':
            return 'Negative split';
        case 'weekly_streak':
            return `${badge.value ?? '?'}-week streak of 3+ runs`;
        case 'weekly_goal':
            return 'Weekly goal reached';
        case 'plan_complete':
            return "Completed this week's plan";
        case 'distance_milestone':
            // Milestones are counted in whole km on the API side.
            return `${(badge.value ?? 0).toLocaleString('en-US')} km run in total`;
        case 'run_milestone':
            return `${ordinal(badge.value ?? 0)} run`;
        case 'beat_last_year':
            return "Passed last year's total";
    }
}

/** The number behind the badge ("12.4 km", "22:41"), or '' when none. */
export function badgeDetail(
    badge: RunBadge,
    fmtDistance: (km: number) => string,
): string {
    if (badge.value == null) return '';
    switch (badge.kind) {
        case 'longest':
        case 'biggest_week':
        case 'biggest_month':
        case 'weekly_goal':
        case 'beat_last_year':
            return fmtDistance(badge.value);
        case 'fastest':
        case 'longest_time':
            return formatDuration(badge.value);
        case 'negative_split':
            return `2nd half ${formatDuration(badge.value)} faster`;
        case 'most_climb':
            return `${Math.round(badge.value)} m`;
        case 'plan_complete':
            return `${badge.value} ${badge.value === 1 ? 'run' : 'runs'}`;
        default:
            return '';
    }
}

/** "Longest run since 07 May 2019 · 12.4 km". */
export function badgeText(
    badge: RunBadge,
    fmtDistance: (km: number) => string,
): string {
    const detail = badgeDetail(badge, fmtDistance);
    return detail ? `${badgeLabel(badge)} · ${detail}` : badgeLabel(badge);
}

export const BADGE_ICONS: Record<RunBadge['kind'], string> = {
    longest: 'pi pi-arrows-h',
    fastest: 'pi pi-bolt',
    longest_time: 'pi pi-clock',
    first_distance: 'pi pi-flag',
    biggest_week: 'pi pi-calendar',
    biggest_month: 'pi pi-calendar-plus',
    comeback: 'pi pi-replay',
    most_climb: 'pi pi-arrow-up-right',
    negative_split: 'pi pi-forward',
    weekly_streak: 'pi pi-sync',
    weekly_goal: 'pi pi-bullseye',
    plan_complete: 'pi pi-check-circle',
    distance_milestone: 'pi pi-trophy',
    run_milestone: 'pi pi-hashtag',
    beat_last_year: 'pi pi-angle-double-up',
};
