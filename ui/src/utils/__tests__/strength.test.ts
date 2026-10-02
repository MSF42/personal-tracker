import { describe, expect, it } from 'vitest';

import type { Task } from '@/types/Task';
import type { WorkoutLog } from '@/types/WorkoutLog';

import { strengthByWeek, strengthStreak } from '../strength';

const log = (date: string, volume: number, completed = true): WorkoutLog =>
    ({ id: 0, date, completed, total_volume: volume }) as WorkoutLog;
const planned = (due_date: string): Task => ({ due_date }) as Task;

describe('strength summaries', () => {
    it('totals completed workouts, volume and plan per week', () => {
        const weeks = strengthByWeek(
            [
                log('2026-09-28', 5000),
                log('2026-09-30', 4000),
                log('2026-10-01', 3000, false), // in progress: not counted
            ],
            [
                planned('2026-09-28'),
                planned('2026-09-30'),
                planned('2026-10-03'),
            ],
        );
        expect(weeks.get('2026-09-28')).toEqual({
            workouts: 2,
            volumeKg: 9000,
            planned: 3,
        });
    });

    it('counts weeks on plan, not breaking on an unfinished week', () => {
        const weeks = strengthByWeek(
            [
                log('2026-09-14', 1),
                log('2026-09-16', 1),
                log('2026-09-21', 1),
                log('2026-09-23', 1),
                log('2026-09-28', 1), // this week: 1 of 2 so far
            ],
            [
                ...['2026-09-14', '2026-09-16'].map(planned),
                ...['2026-09-21', '2026-09-23'].map(planned),
                ...['2026-09-28', '2026-09-30'].map(planned),
            ],
        );
        const thursday = new Date(2026, 9, 1);
        expect(strengthStreak(weeks, thursday)).toBe(2);
        // Without a plan, one workout keeps the week on plan.
        const unplanned = strengthByWeek([log('2026-09-21', 1)], []);
        expect(strengthStreak(unplanned, thursday)).toBe(1);
        expect(strengthStreak(new Map(), thursday)).toBe(0);
    });
});
