import { describe, expect, it } from 'vitest';

import {
    fromIsoDate,
    mondayIndex,
    toIsoDate,
    weekDays,
    weekRange,
} from '../week';

describe('week helpers (Monday start)', () => {
    it('maps Monday to 0 and Sunday to 6', () => {
        expect(mondayIndex(fromIsoDate('2026-09-07'))).toBe(0); // Mon
        expect(mondayIndex(fromIsoDate('2026-09-06'))).toBe(6); // Sun
        expect(mondayIndex(fromIsoDate('2026-09-09'))).toBe(2); // Wed
    });

    it('puts a Sunday in the week that started the previous Monday', () => {
        expect(weekRange(fromIsoDate('2026-09-06'))).toEqual({
            start: '2026-08-31',
            end: '2026-09-06',
        });
    });

    it('starts a Monday week on that Monday', () => {
        expect(weekRange(fromIsoDate('2026-09-07'))).toEqual({
            start: '2026-09-07',
            end: '2026-09-13',
        });
    });

    it('lists Mon..Sun for the current and previous weeks', () => {
        const wed = fromIsoDate('2026-09-09');
        expect(weekDays(wed)).toEqual([
            '2026-09-07',
            '2026-09-08',
            '2026-09-09',
            '2026-09-10',
            '2026-09-11',
            '2026-09-12',
            '2026-09-13',
        ]);
        expect(weekDays(wed, -1)[0]).toBe('2026-08-31');
    });

    it('formats local dates without a UTC shift', () => {
        expect(toIsoDate(new Date(2026, 0, 1, 23, 30))).toBe('2026-01-01');
    });
});
