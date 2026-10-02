import { describe, expect, it } from 'vitest';

import type { RunBadge } from '@/types/Running';

import { badgeLabel, badgeText } from '../badges';

const badge = (b: Partial<RunBadge> & Pick<RunBadge, 'kind'>): RunBadge => ({
    since: null,
    ever: false,
    effort: null,
    value: null,
    ...b,
});
const km = (n: number) => `${n.toFixed(2)} km`;

describe('badge wording', () => {
    it('phrases ever and since badges', () => {
        expect(
            badgeLabel(badge({ kind: 'longest', since: '2019-05-07' })),
        ).toBe('Longest run since 07 May 2019');
        expect(badgeLabel(badge({ kind: 'longest', ever: true }))).toBe(
            'Longest run ever',
        );
    });

    it('names efforts and lower-cases marathons', () => {
        expect(
            badgeLabel(badge({ kind: 'fastest', effort: '5K', ever: true })),
        ).toBe('Fastest 5K ever');
        expect(
            badgeLabel(
                badge({
                    kind: 'first_distance',
                    effort: 'Half Marathon',
                    since: '2018-03-25',
                }),
            ),
        ).toBe('First half marathon since 25 Mar 2018');
    });

    it('phrases weeks, months and comebacks', () => {
        expect(
            badgeLabel(badge({ kind: 'biggest_week', since: '2024-08-19' })),
        ).toBe('Biggest week since week of 19 Aug 2024');
        expect(
            badgeLabel(badge({ kind: 'biggest_month', since: '2024-08-01' })),
        ).toBe('Biggest month since Aug 2024');
        expect(badgeLabel(badge({ kind: 'comeback', value: 47 }))).toBe(
            'First run in 47 days',
        );
    });

    it('adds the value in the right unit', () => {
        expect(
            badgeText(
                badge({ kind: 'longest', since: '2019-05-07', value: 12.4 }),
                km,
            ),
        ).toBe('Longest run since 07 May 2019 · 12.40 km');
        expect(
            badgeText(
                badge({
                    kind: 'fastest',
                    effort: '5K',
                    ever: true,
                    value: 1361,
                }),
                km,
            ),
        ).toBe('Fastest 5K ever · 22:41');
        expect(badgeText(badge({ kind: 'comeback', value: 17 }), km)).toBe(
            'First run in 17 days',
        );
    });

    it('phrases the phase 2 badges', () => {
        expect(
            badgeText(
                badge({ kind: 'most_climb', ever: true, value: 255 }),
                km,
            ),
        ).toBe('Most climb ever · 255 m');
        expect(
            badgeText(badge({ kind: 'negative_split', value: 30 }), km),
        ).toBe('Negative split · 2nd half 0:30 faster');
        expect(badgeLabel(badge({ kind: 'weekly_streak', value: 8 }))).toBe(
            '8-week streak of 3+ runs',
        );
        expect(badgeText(badge({ kind: 'weekly_goal', value: 20 }), km)).toBe(
            'Weekly goal reached · 20.00 km',
        );
        expect(badgeText(badge({ kind: 'plan_complete', value: 4 }), km)).toBe(
            "Completed this week's plan · 4 runs",
        );
        expect(
            badgeLabel(badge({ kind: 'distance_milestone', value: 6000 })),
        ).toBe('6,000 km run in total');
        expect(badgeLabel(badge({ kind: 'run_milestone', value: 1300 }))).toBe(
            '1,300th run',
        );
        expect(badgeLabel(badge({ kind: 'run_milestone', value: 111 }))).toBe(
            '111th run',
        );
        expect(badgeLabel(badge({ kind: 'run_milestone', value: 1 }))).toBe(
            '1st run',
        );
        expect(
            badgeText(badge({ kind: 'beat_last_year', value: 385.98 }), km),
        ).toBe("Passed last year's total · 385.98 km");
    });
});
