import { useRunningApi } from '@/composables/api/useRunningApi';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import { badgeText } from '@/utils/badges';
import { formatDate } from '@/utils/format';

// Past this many lines the toast gets unwieldy (a big bulk import); the rest
// are summarised and remain visible in the Log and on each run's page.
const MAX_LINES = 6;

/**
 * After runs are added or imported, tell the user which badges they earned.
 * Quiet when there are none.
 */
export function useBadgeAnnouncer() {
    const { getBadges } = useRunningApi();
    const { showBadges } = useToast();
    const { fmtDistance } = useUnits();

    async function announceBadges(runs: { id: number; date: string }[]) {
        if (runs.length === 0) return;
        const dates = runs.map((r) => r.date).sort();
        const res = await getBadges({
            date_from: dates[0],
            date_to: dates[dates.length - 1],
        });
        if (!res.success || !res.data) return;
        const ids = new Set(runs.map((r) => r.id));
        const earned = res.data.filter((r) => ids.has(r.run_id));
        if (earned.length === 0) return;

        const multiRun = earned.length > 1;
        const lines = earned.flatMap((r) =>
            r.badges.map((b) =>
                multiRun
                    ? `${formatDate(r.date)}: ${badgeText(b, fmtDistance)}`
                    : badgeText(b, fmtDistance),
            ),
        );
        const shown = lines.slice(0, MAX_LINES);
        if (lines.length > MAX_LINES) {
            shown.push(`…and ${lines.length - MAX_LINES} more`);
        }
        showBadges(
            lines.length === 1 ? 'New badge' : `${lines.length} new badges`,
            shown.join('\n'),
        );
    }

    return { announceBadges };
}
