import { describe, expect, it } from 'vitest';

import { formatDateRange } from '../format';
import { bestWindow } from '../running';

describe('formatDateRange', () => {
    it('shows the year once within a year, twice across years', () => {
        expect(formatDateRange('2011-04-12', '2011-04-18')).toBe(
            '12 Apr – 18 Apr 2011',
        );
        expect(formatDateRange('2010-12-20', '2011-12-19')).toBe(
            '20 Dec 2010 – 19 Dec 2011',
        );
    });
});

const run = (date: string, distance_km: number) => ({ date, distance_km });

describe('bestWindow', () => {
    it('returns null with no runs', () => {
        expect(bestWindow([], 7)).toBeNull();
    });

    it('finds the densest window anywhere in history, ending on a run', () => {
        const runs = [
            run('2011-04-01', 10),
            run('2011-04-05', 10),
            run('2011-04-07', 10), // 1st..7th = 30 km
            run('2011-04-08', 5), // 2nd..8th = 25 km
            run('2026-09-01', 12),
        ];
        expect(bestWindow(runs, 7)).toEqual({
            start: '2011-04-01',
            end: '2011-04-07',
            distanceKm: 30,
            count: 3,
        });
    });

    it('drops a run exactly `days` days before the window end', () => {
        const runs = [run('2026-03-01', 10), run('2026-03-08', 4)];
        // 1st..7th holds only the first run; 2nd..8th only the second.
        expect(bestWindow(runs, 7)?.distanceKm).toBe(10);
    });

    it('counts every run on a shared day', () => {
        const runs = [run('2026-03-01', 3), run('2026-03-01', 4)];
        expect(bestWindow(runs, 1)).toEqual({
            start: '2026-03-01',
            end: '2026-03-01',
            distanceKm: 7,
            count: 2,
        });
    });

    it('ignores input order and spans DST changes by whole days', () => {
        const runs = [run('2026-03-14', 5), run('2026-03-08', 5)];
        expect(bestWindow(runs, 7)).toMatchObject({
            start: '2026-03-08',
            end: '2026-03-14',
            distanceKm: 10,
        });
    });
});
