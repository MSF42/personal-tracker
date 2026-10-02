import { describe, expect, it } from 'vitest';

import type { Task } from '@/types/Task';

import {
    parseTaskDistanceKm,
    planByWeek,
    plannedDays,
    weeklyGoal,
} from '../plan';

const task = (due_date: string, title: string): Task =>
    ({ id: 0, title, due_date, completed: false }) as Task;

describe('training plan helpers', () => {
    it('reads the last distance in a title', () => {
        expect(parseTaskDistanceKm('Run 2.0 km')).toBe(2);
        expect(
            parseTaskDistanceKm('Race: Fall Creek Falls Half (21.1 km)'),
        ).toBe(21.1);
        expect(parseTaskDistanceKm('Long run 5 km after 1 km warmup 6km')).toBe(
            6,
        );
        expect(parseTaskDistanceKm('Rest day')).toBeNull();
    });

    it('totals the whole plan per Mon–Sun week, done or not', () => {
        const days = plannedDays([
            task('2026-10-05', 'Run 3.0 km'), // Mon
            task('2026-10-07', 'Run 3.0 km'),
            task('2026-10-11', 'Long run 6.0 km'), // Sun, same week
            task('2026-10-12', 'Run 4.0 km'), // next Mon
            task('2026-10-13', 'Strides'), // no distance: counts as a run
        ]);
        const weeks = planByWeek(days);
        expect(weeks.get('2026-10-05')).toEqual({
            km: 12,
            runs: 3,
            longestKm: 6,
        });
        expect(weeks.get('2026-10-12')).toEqual({
            km: 4,
            runs: 2,
            longestKm: 4,
        });
        expect(days.get('2026-10-05')?.isRace).toBe(false);
    });

    it('takes the goal from the plan, falling back to the manual goal', () => {
        const plan = planByWeek(
            plannedDays([task('2026-10-05', 'Run 8.0 km')]),
        );
        expect(weeklyGoal('2026-10-05', plan, 20)).toEqual({
            km: 8,
            source: 'plan',
        });
        expect(weeklyGoal('2026-10-12', plan, 20)).toEqual({
            km: 20,
            source: 'goal',
        });
        expect(weeklyGoal('2026-10-12', plan, null)).toBeNull();
    });
});
