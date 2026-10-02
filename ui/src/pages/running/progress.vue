<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import AddEditRunDialog from '@/components/AddEditRunDialog.vue';
import RunBadges from '@/components/RunBadges.vue';
import RunningCalendar from '@/components/RunningCalendar.vue';
import WeeklyProgressList from '@/components/WeeklyProgressList.vue';
import { useRunningApi } from '@/composables/api/useRunningApi';
import { useSettingsApi } from '@/composables/api/useSettingsApi';
import { useTaskApi } from '@/composables/api/useTaskApi';
import { useToast } from '@/composables/useToast';
import { useUnits } from '@/composables/useUnits';
import type { BestEffort, RunBadgeSet, RunningActivity } from '@/types/Running';
import type { Task } from '@/types/Task';
import { formatDate, formatDateRange, formatDuration } from '@/utils/format';
import { planByWeek, plannedDays, weeklyGoal } from '@/utils/plan';
import { bestWindow } from '@/utils/running';
import { rollingRange, weekRange } from '@/utils/week';

const { getActivities, getBadges, getBestEfforts } = useRunningApi();
const { getSetting, setSetting } = useSettingsApi();
const { getTasks } = useTaskApi();
const toast = useToast();
const { distanceUnit, fmtDistance, fmtPace, toKm, fromKm } = useUnits();

const activities = ref<RunningActivity[]>([]);
// Fastest time ever at each standard distance (1K … Marathon), counting the
// fastest stretch inside longer runs — computed by the API from the tracks.
const bestEfforts = ref<BestEffort[]>([]);
// Runs from the past 30 days that earned badges, newest first.
const recentBadges = ref<RunBadgeSet[]>([]);
// Every Running task, done or not: the training plan (see utils/plan.ts).
const runningTasks = ref<Task[]>([]);
const plan = computed(() => plannedDays(runningTasks.value));
const weekPlan = computed(() => planByWeek(plan.value));

// --- Weekly Goal ---
// This Mon–Sun week against the plan's distance for it; the manual goal only
// applies to weeks with nothing planned.
const weeklyGoalKm = ref<number | null>(null);
const showGoalDialog = ref(false);
const goalFormValue = ref<number>(0);

const weeklyGoalProgress = computed(() => {
    const { start, end } = weekRange();
    const goal = weeklyGoal(start, weekPlan.value, weeklyGoalKm.value);
    if (!goal) return null;
    const current = activities.value
        .filter((r) => r.date >= start && r.date <= end)
        .reduce((s, r) => s + r.distance_km, 0);
    return {
        percentage: Math.round(Math.min((current / goal.km) * 100, 100)),
        currentKm: current,
        goalKm: goal.km,
        source: goal.source,
    };
});

function openGoalDialog() {
    goalFormValue.value = parseFloat(
        fromKm(weeklyGoalKm.value ?? 0).toFixed(1),
    );
    showGoalDialog.value = true;
}

async function saveGoal() {
    const goalKm = goalFormValue.value > 0 ? toKm(goalFormValue.value) : 0;
    const res = await setSetting('running_weekly_goal_km', String(goalKm));
    if (res.success) {
        weeklyGoalKm.value = goalKm > 0 ? goalKm : null;
        toast.showSuccess('Weekly goal updated');
        showGoalDialog.value = false;
    } else {
        toast.showError(res.error?.message ?? 'Failed to save weekly goal');
    }
}

// --- Data loading ---
// This tab always reflects your whole running history — the Log tab's
// filters are for finding specific runs in the list, not for narrowing what
// the trend/summary views below show.
async function loadData() {
    const [runsRes, effortsRes, badgesRes] = await Promise.all([
        getActivities(),
        getBestEfforts(),
        getBadges({ date_from: rollingRange(30).start }),
    ]);
    if (effortsRes.success && effortsRes.data) {
        bestEfforts.value = effortsRes.data;
    }
    if (badgesRes.success && badgesRes.data) {
        recentBadges.value = badgesRes.data;
    }
    if (runsRes.success && runsRes.data) {
        activities.value = runsRes.data;
    } else if (!runsRes.success) {
        toast.showError('Failed to load running activities');
    }
}

// The whole plan, completed tasks included: a completed task (usually
// auto-completed by logging that day's run) is what that week planned, which
// planned-vs-actual and the calendar both compare against.
async function loadRunningTasks() {
    const res = await getTasks({ category: 'Running' });
    if (res.success && res.data) {
        runningTasks.value = res.data;
    }
}

async function loadGoal() {
    const res = await getSetting('running_weekly_goal_km');
    if (res.success && res.data?.value) {
        const val = parseFloat(res.data.value);
        if (val > 0) weeklyGoalKm.value = val;
    }
}

onMounted(() => {
    void loadData();
    void loadRunningTasks();
    void loadGoal();
});

// --- Computed stats ---
// These are trailing windows (past 7/30/365 days ending today), not calendar
// periods — so "This Month" on the 3rd doesn't reset to almost nothing.
// Weekly Progress below is the calendar-week breakdown; this is unrelated.
const weekStats = computed(() => {
    const { start, end } = rollingRange(7);
    const runs = activities.value.filter(
        (r) => r.date >= start && r.date <= end,
    );
    return {
        distance: runs.reduce((s, r) => s + r.distance_km, 0),
        count: runs.length,
    };
});

const monthStats = computed(() => {
    const { start, end } = rollingRange(30);
    const runs = activities.value.filter(
        (r) => r.date >= start && r.date <= end,
    );
    return {
        distance: runs.reduce((s, r) => s + r.distance_km, 0),
        count: runs.length,
    };
});

const yearStats = computed(() => {
    const { start, end } = rollingRange(365);
    const runs = activities.value.filter(
        (r) => r.date >= start && r.date <= end,
    );
    return {
        distance: runs.reduce((s, r) => s + r.distance_km, 0),
        count: runs.length,
    };
});

// Best-ever 7/30/365-day stretch (any start date), shown under each trailing
// window card so "now" reads against "my best".
const bestWeek = computed(() => bestWindow(activities.value, 7));
const bestMonth = computed(() => bestWindow(activities.value, 30));
const bestYear = computed(() => bestWindow(activities.value, 365));

const allTimeBests = computed(() => {
    const runs = activities.value;
    if (runs.length === 0) {
        return { longest: null, totalDistanceKm: 0 };
    }
    const longest = runs.reduce((best, r) =>
        r.distance_km > best.distance_km ? r : best,
    );
    const totalDistanceKm = runs.reduce((s, r) => s + r.distance_km, 0);
    return { longest, totalDistanceKm };
});

// --- Weekly Progress ---------------------------------------------------------
// List (planned vs actual per week) or month calendar; the plan feeds both.
type WeeklyView = 'list' | 'calendar';
const weeklyView = ref<WeeklyView>('list');
const weeklyViewOptions: { label: string; value: WeeklyView }[] = [
    { label: 'List', value: 'list' },
    { label: 'Calendar', value: 'calendar' },
];

// Logging a planned-but-not-yet-run calendar day opens Add Run pre-dated.
const showAddRunDialog = ref(false);
const addRunDefaultDate = ref<string | null>(null);

function openAddRun(date: string) {
    addRunDefaultDate.value = date;
    showAddRunDialog.value = true;
}

async function onAddRunSaved() {
    await Promise.all([loadData(), loadRunningTasks()]);
}
</script>

<template>
    <div>
        <h1 class="mb-6 text-2xl font-bold">Running</h1>

        <!-- Stats Cards -->
        <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <AppCard>
                <template #title>
                    <div class="flex items-center justify-between">
                        <span>Past 7 Days</span>
                        <AppButton
                            aria-label="Set weekly goal"
                            icon="pi pi-cog"
                            rounded
                            severity="secondary"
                            size="small"
                            text
                            title="Set weekly goal"
                            @click="openGoalDialog"
                        />
                    </div>
                </template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ fmtDistance(weekStats.distance) }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{ weekStats.count }}
                        {{ weekStats.count === 1 ? 'run' : 'runs' }}
                    </div>
                    <div v-if="weeklyGoalProgress" class="mt-2">
                        <div class="text-surface-500 mb-1 text-xs">
                            This week:
                            {{ fmtDistance(weeklyGoalProgress.currentKm) }} /
                            {{ fmtDistance(weeklyGoalProgress.goalKm) }}
                            {{
                                weeklyGoalProgress.source === 'plan'
                                    ? '(plan)'
                                    : '(goal)'
                            }}
                        </div>
                        <div
                            class="bg-surface-200 dark:bg-surface-700 h-2 w-full overflow-hidden rounded-full"
                        >
                            <div
                                class="h-full rounded-full transition-all"
                                :class="
                                    weeklyGoalProgress.percentage >= 100
                                        ? 'bg-green-500'
                                        : 'bg-blue-500'
                                "
                                :style="{
                                    width: `${weeklyGoalProgress.percentage}%`,
                                }"
                            ></div>
                        </div>
                    </div>
                    <div
                        v-if="bestWeek"
                        class="border-surface-200 dark:border-surface-700 mt-3 border-t pt-2"
                    >
                        <div class="text-surface-500 text-xs">Best 7 days</div>
                        <div class="font-semibold">
                            {{ fmtDistance(bestWeek.distanceKm) }}
                        </div>
                        <div class="text-surface-400 text-xs">
                            {{ formatDateRange(bestWeek.start, bestWeek.end) }}
                        </div>
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>Past 30 Days</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ fmtDistance(monthStats.distance) }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{ monthStats.count }}
                        {{ monthStats.count === 1 ? 'run' : 'runs' }}
                    </div>
                    <div
                        v-if="bestMonth"
                        class="border-surface-200 dark:border-surface-700 mt-3 border-t pt-2"
                    >
                        <div class="text-surface-500 text-xs">Best 30 days</div>
                        <div class="font-semibold">
                            {{ fmtDistance(bestMonth.distanceKm) }}
                        </div>
                        <div class="text-surface-400 text-xs">
                            {{
                                formatDateRange(bestMonth.start, bestMonth.end)
                            }}
                        </div>
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>Past 365 Days</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ fmtDistance(yearStats.distance) }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{ yearStats.count }}
                        {{ yearStats.count === 1 ? 'run' : 'runs' }}
                    </div>
                    <div
                        v-if="bestYear"
                        class="border-surface-200 dark:border-surface-700 mt-3 border-t pt-2"
                    >
                        <div class="text-surface-500 text-xs">
                            Best 365 days
                        </div>
                        <div class="font-semibold">
                            {{ fmtDistance(bestYear.distanceKm) }}
                        </div>
                        <div class="text-surface-400 text-xs">
                            {{ formatDateRange(bestYear.start, bestYear.end) }}
                        </div>
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>All Time</template>
                <template #content>
                    <div class="space-y-1">
                        <div>
                            <span class="text-surface-500 text-sm">
                                Longest:
                            </span>
                            <span class="font-semibold">
                                {{
                                    allTimeBests.longest
                                        ? fmtDistance(
                                              allTimeBests.longest.distance_km,
                                          )
                                        : '—'
                                }}
                            </span>
                        </div>
                        <div>
                            <span class="text-surface-500 text-sm">
                                Total:
                            </span>
                            <span class="font-semibold">
                                {{ fmtDistance(allTimeBests.totalDistanceKm) }}
                            </span>
                        </div>
                    </div>
                </template>
            </AppCard>
        </div>

        <!-- Recent Achievements: badges earned in the past 30 days -->
        <div class="mb-6">
            <h2 class="mb-3 text-xl font-semibold">Recent Achievements</h2>
            <div
                v-if="recentBadges.length"
                class="border-surface-200 dark:border-surface-700 divide-surface-200 dark:divide-surface-700 divide-y rounded-lg border"
            >
                <RouterLink
                    v-for="entry in recentBadges"
                    :key="entry.run_id"
                    class="hover:bg-surface-50 dark:hover:bg-surface-800 flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:gap-4"
                    :to="`/running/${entry.run_id}`"
                >
                    <span class="text-surface-500 w-28 shrink-0 text-sm">
                        {{ formatDate(entry.date) }}
                    </span>
                    <RunBadges :badges="entry.badges" />
                </RouterLink>
            </div>
            <p v-else class="text-surface-500 text-sm">
                No badges earned in the past 30 days.
            </p>
        </div>

        <!-- Fastest time at each standard distance, including the fastest
             stretch inside a longer run -->
        <div v-if="bestEfforts.length" class="mb-6">
            <h2 class="mb-3 text-xl font-semibold">Fastest by Distance</h2>
            <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
                <RouterLink
                    v-for="effort in bestEfforts"
                    :key="effort.name"
                    class="border-surface-200 dark:border-surface-700 hover:bg-surface-50 dark:hover:bg-surface-800 rounded-lg border p-3 text-center"
                    :to="`/running/${effort.run_id}`"
                >
                    <div class="text-surface-500 mb-1 text-sm font-medium">
                        {{ effort.name }}
                    </div>
                    <div class="text-xl font-bold">
                        {{ formatDuration(effort.duration_seconds) }}
                    </div>
                    <div class="text-surface-400 mt-1 text-xs">
                        {{ fmtPace(effort.pace) }} &middot;
                        {{ formatDate(effort.date) }}
                    </div>
                </RouterLink>
            </div>
        </div>

        <!-- Weekly Progress -->
        <div v-if="activities.length > 0 || weekPlan.size > 0" class="mb-8">
            <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h2 class="text-xl font-semibold">Weekly Progress</h2>
                <AppSelectButton
                    v-model="weeklyView"
                    :allow-empty="false"
                    option-label="label"
                    option-value="value"
                    :options="weeklyViewOptions"
                    size="small"
                />
            </div>
            <WeeklyProgressList
                v-if="weeklyView === 'list'"
                :activities="activities"
                :week-plan="weekPlan"
            />
            <RunningCalendar
                v-else
                :activities="activities"
                :plan="plan"
                @add-run="openAddRun"
            />
        </div>

        <!-- Weekly Goal Dialog -->
        <AppDialog
            v-model:visible="showGoalDialog"
            header="Weekly Distance Goal"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <p class="text-surface-500 text-sm">
                    Weeks with planned runs use the plan's distance; this goal
                    covers the weeks without one.
                </p>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Goal ({{ distanceUnit }} per week)
                    </label>
                    <AppInputNumber
                        v-model="goalFormValue"
                        class="w-full"
                        :max-fraction-digits="1"
                        :min="0"
                        :step="distanceUnit === 'mi' ? 3 : 5"
                        :suffix="' ' + distanceUnit"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showGoalDialog = false"
                    />
                    <AppButton label="Save" @click="saveGoal" />
                </div>
            </div>
        </AppDialog>

        <!-- Add Run, opened by clicking a planned-but-not-yet-run Calendar day -->
        <AddEditRunDialog
            v-model:visible="showAddRunDialog"
            :default-date="addRunDefaultDate"
            :run="null"
            @saved="onAddRunSaved"
        />
    </div>
</template>
