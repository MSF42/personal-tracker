/**
 * The training plan, as Running tasks: one task per planned run, with the
 * distance only in its title ("Run 2.0 km", "Long run 5.0 km",
 * "Race: Fall Creek Falls Half (21.1 km)").
 */
import type { Task } from '@/types/Task';

import { fromIsoDate, startOfWeek, toIsoDate } from './week';

/** The last "N km" / "N.N km" in a title — the intended distance in every
 *  title shape the plan uses — or null when there is none. */
export function parseTaskDistanceKm(title: string): number | null {
    const matches = [...title.matchAll(/(\d+(?:\.\d+)?)\s*km/gi)];
    if (matches.length === 0) return null;
    return parseFloat(matches[matches.length - 1]![1]!);
}

export interface PlannedDay {
    date: string;
    title: string;
    km: number | null;
    isRace: boolean;
}

/** Planned runs by due date (one per day; a later task on the same day wins). */
export function plannedDays(tasks: Task[]): Map<string, PlannedDay> {
    const map = new Map<string, PlannedDay>();
    for (const t of tasks) {
        if (!t.due_date) continue;
        const date = t.due_date.slice(0, 10);
        map.set(date, {
            date,
            title: t.title,
            km: parseTaskDistanceKm(t.title),
            isRace: t.title.startsWith('Race:'),
        });
    }
    return map;
}

export interface WeekPlan {
    km: number;
    runs: number;
    longestKm: number;
}

/** The whole plan per Mon–Sun week, done or not — what each week asked for. */
export function planByWeek(
    days: Map<string, PlannedDay>,
): Map<string, WeekPlan> {
    const map = new Map<string, WeekPlan>();
    for (const day of days.values()) {
        const ws = toIsoDate(startOfWeek(fromIsoDate(day.date)));
        const agg = map.get(ws) ?? { km: 0, runs: 0, longestKm: 0 };
        agg.km += day.km ?? 0;
        agg.runs += 1;
        agg.longestKm = Math.max(agg.longestKm, day.km ?? 0);
        map.set(ws, agg);
    }
    return map;
}

export interface WeeklyGoal {
    km: number;
    source: 'plan' | 'goal';
}

/** A week's distance goal: the plan's distance when the week has planned
 *  runs, otherwise the manual weekly goal (if one is set). */
export function weeklyGoal(
    weekStart: string,
    plan: Map<string, WeekPlan>,
    manualGoalKm: number | null,
): WeeklyGoal | null {
    const planned = plan.get(weekStart)?.km ?? 0;
    if (planned > 0) return { km: planned, source: 'plan' };
    if (manualGoalKm && manualGoalKm > 0) {
        return { km: manualGoalKm, source: 'goal' };
    }
    return null;
}
