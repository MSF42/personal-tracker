/**
 * Strength training summaries over workout logs and the plan (Strength
 * tasks, one per planned workout).
 */
import type { Task } from '@/types/Task';
import type { WorkoutLog } from '@/types/WorkoutLog';

import { fromIsoDate, startOfWeek, toIsoDate } from './week';

export interface StrengthWeek {
    workouts: number;
    volumeKg: number;
    planned: number;
}

const weekOf = (date: string) =>
    toIsoDate(startOfWeek(fromIsoDate(date.slice(0, 10))));

/** Completed workouts, volume and planned workouts per Mon–Sun week. */
export function strengthByWeek(
    logs: WorkoutLog[],
    plannedTasks: Task[],
): Map<string, StrengthWeek> {
    const weeks = new Map<string, StrengthWeek>();
    const get = (ws: string) => {
        let w = weeks.get(ws);
        if (!w) {
            w = { workouts: 0, volumeKg: 0, planned: 0 };
            weeks.set(ws, w);
        }
        return w;
    };
    for (const log of logs) {
        if (!log.completed) continue;
        const w = get(weekOf(log.date));
        w.workouts += 1;
        w.volumeKg += log.total_volume ?? 0;
    }
    for (const task of plannedTasks) {
        if (task.due_date) get(weekOf(task.due_date)).planned += 1;
    }
    return weeks;
}

/** A week is "on plan" when it has as many workouts as planned — or, with
 *  nothing planned, at least one. */
function onPlan(week: StrengthWeek | undefined): boolean {
    if (!week) return false;
    return week.workouts >= Math.max(1, week.planned);
}

/**
 * Consecutive Mon–Sun weeks on plan, ending with the current week if it's
 * already on plan, otherwise with last week — an unfinished week doesn't
 * break the streak.
 */
export function strengthStreak(
    weeks: Map<string, StrengthWeek>,
    today: Date = new Date(),
): number {
    const cursor = startOfWeek(today);
    if (!onPlan(weeks.get(toIsoDate(cursor)))) {
        cursor.setDate(cursor.getDate() - 7);
    }
    let streak = 0;
    while (onPlan(weeks.get(toIsoDate(cursor)))) {
        streak += 1;
        cursor.setDate(cursor.getDate() - 7);
    }
    return streak;
}
