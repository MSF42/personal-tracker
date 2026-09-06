<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import LoadingState from '@/components/LoadingState.vue';
import { useCountdownApi } from '@/composables/api/useCountdownApi';
import { useRunningApi } from '@/composables/api/useRunningApi';
import { useTaskApi } from '@/composables/api/useTaskApi';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
import type { Countdown } from '@/types/Countdown';
import type { RunningActivity } from '@/types/Running';
import type { Task, TaskCreate } from '@/types/Task';
import type { WorkoutLog } from '@/types/WorkoutLog';
import { formatDate as formatIsoDate } from '@/utils/format';
import {
    mondayIndex,
    toIsoDate,
    WEEKDAY_LABELS,
    weekRange,
} from '@/utils/week';

const { getActivities, createActivity } = useRunningApi();
const { getTasks, createTask } = useTaskApi();
const { getWorkoutLogs } = useWorkoutLogApi();
const { getCountdowns, createCountdown, deleteCountdown } = useCountdownApi();
const toast = useToast();
const router = useRouter();
const { loading, withLoading } = useLoading();

const runs = ref<RunningActivity[]>([]);
const tasks = ref<Task[]>([]);
const workoutLogs = ref<WorkoutLog[]>([]);
const countdowns = ref<Countdown[]>([]);
const showAddCountdown = ref(false);
const countdownForm = reactive({ title: '', date: '' });
const calendarView = ref<'5-day' | 'month'>('5-day');

const today = new Date();
const todayStr = toIsoDate(today);
const currentYear = today.getFullYear();
const currentMonth = today.getMonth();

onMounted(() =>
    withLoading(async () => {
        const [runsRes, tasksRes, logsRes, countdownsRes] = await Promise.all([
            getActivities(),
            getTasks(),
            getWorkoutLogs(),
            getCountdowns(),
        ]);
        if (countdownsRes.success && countdownsRes.data)
            countdowns.value = countdownsRes.data;
        if (runsRes.success && runsRes.data) runs.value = runsRes.data;
        else if (!runsRes.success)
            toast.showError('Failed to load running activities');
        if (tasksRes.success && tasksRes.data) tasks.value = tasksRes.data;
        else if (!tasksRes.success) toast.showError('Failed to load tasks');
        if (logsRes.success && logsRes.data) workoutLogs.value = logsRes.data;
        else if (!logsRes.success)
            toast.showError('Failed to load workout logs');
    }),
);

// --- Summary computations ---

const tasksDueToday = computed(() => {
    const dueToday = tasks.value.filter(
        (t) => !t.completed && t.due_date === todayStr,
    );
    const overdue = tasks.value.filter(
        (t) => !t.completed && t.due_date && t.due_date < todayStr,
    );
    return { dueCount: dueToday.length, overdueCount: overdue.length };
});

const weeklyRunning = computed(() => {
    const { start: monStr, end: sunStr } = weekRange(today);
    const weekRuns = runs.value.filter(
        (r) => r.date >= monStr && r.date <= sunStr,
    );
    return {
        distance: weekRuns.reduce((s, r) => s + r.distance_km, 0).toFixed(1),
        count: weekRuns.length,
    };
});

const lastWorkout = computed(() => {
    if (workoutLogs.value.length === 0) return null;
    const log = workoutLogs.value[0] as WorkoutLog;
    return { date: log.date, routineName: log.routine_name };
});

// --- Add Run dialog ---
const showAddRun = ref(false);
const runForm = reactive({
    date: todayStr,
    title: '',
    minutes: 0,
    seconds: 0,
    distance_km: 0,
    notes: '',
});

function openAddRun() {
    runForm.date = todayStr;
    runForm.title = '';
    runForm.minutes = 0;
    runForm.seconds = 0;
    runForm.distance_km = 0;
    runForm.notes = '';
    showAddRun.value = true;
}

async function saveRun() {
    const res = await createActivity({
        date: runForm.date,
        duration_seconds: runForm.minutes * 60 + runForm.seconds,
        distance_km: runForm.distance_km,
        notes: runForm.notes || null,
        title: runForm.title || null,
    });
    if (res.success) {
        toast.showSuccess('Run added');
        showAddRun.value = false;
        const runsRes = await getActivities();
        if (runsRes.success && runsRes.data) runs.value = runsRes.data;
    }
}

// --- Add Task dialog ---
const showAddTask = ref(false);
const taskForm = reactive({
    title: '',
    description: '',
    category: '',
    due_date: '',
});
const isTaskFormValid = computed(() => taskForm.title.trim() !== '');
const taskSaveTooltip = computed(() =>
    isTaskFormValid.value ? undefined : 'Title is required',
);

function openAddTask() {
    taskForm.title = '';
    taskForm.description = '';
    taskForm.category = '';
    taskForm.due_date = '';
    showAddTask.value = true;
}

async function saveTask() {
    const payload: TaskCreate = {
        title: taskForm.title,
        description: taskForm.description || null,
        category: taskForm.category || null,
        due_date: taskForm.due_date || null,
    };
    const res = await createTask(payload);
    if (res.success) {
        toast.showSuccess('Task added');
        showAddTask.value = false;
        const tasksRes = await getTasks();
        if (tasksRes.success && tasksRes.data) tasks.value = tasksRes.data;
    }
}

// --- Countdowns ---
const DAY_MS = 86_400_000;

/** Whole days from today to an ISO date; negative when the date has passed. */
function daysUntil(isoDate: string): number {
    const [y, m, d] = isoDate.split('-').map(Number) as [
        number,
        number,
        number,
    ];
    const target = Date.UTC(y, m - 1, d);
    const now = Date.UTC(
        today.getFullYear(),
        today.getMonth(),
        today.getDate(),
    );
    return Math.round((target - now) / DAY_MS);
}

function countdownLabel(isoDate: string): string {
    const days = daysUntil(isoDate);
    if (days === 0) return 'Today';
    if (days === 1) return 'Tomorrow';
    if (days === -1) return 'Yesterday';
    if (days > 0) return `${days} days`;
    return `${-days} days ago`;
}

async function addCountdown() {
    if (!countdownForm.title.trim() || !countdownForm.date) return;
    const res = await createCountdown({
        title: countdownForm.title.trim(),
        date: countdownForm.date,
    });
    if (res.success && res.data) {
        countdowns.value = [...countdowns.value, res.data].sort((a, b) =>
            a.date.localeCompare(b.date),
        );
        countdownForm.title = '';
        countdownForm.date = '';
        showAddCountdown.value = false;
    } else if (!res.success) {
        toast.showError('Failed to add countdown');
    }
}

const showDeleteCountdown = ref(false);
const deletingCountdown = ref<Countdown | null>(null);

function confirmDeleteCountdown(countdown: Countdown) {
    deletingCountdown.value = countdown;
    showDeleteCountdown.value = true;
}

async function executeDeleteCountdown() {
    if (!deletingCountdown.value) return;
    const res = await deleteCountdown(deletingCountdown.value.id);
    if (res.success) {
        countdowns.value = countdowns.value.filter(
            (c) => c.id !== deletingCountdown.value!.id,
        );
    } else {
        toast.showError('Failed to delete countdown');
    }
    showDeleteCountdown.value = false;
    deletingCountdown.value = null;
}

// --- Calendar helpers ---

function formatDate(date: Date): string {
    return toIsoDate(date);
}

function getDayName(date: Date): string {
    return date.toLocaleDateString('en-US', { weekday: 'short' });
}

function getDayNumber(date: Date): number {
    return date.getDate();
}

const next5Days = computed(() => {
    const days: Date[] = [];
    for (let i = 0; i < 5; i++) {
        const d = new Date(today);
        d.setDate(today.getDate() + i);
        days.push(d);
    }
    return days;
});

interface CalendarEvent {
    type: 'run' | 'workout' | 'task';
    label: string;
}

function getEventsForDate(dateStr: string): CalendarEvent[] {
    const events: CalendarEvent[] = [];

    for (const r of runs.value) {
        if (r.date === dateStr) {
            events.push({
                type: 'run',
                label: `Run: ${r.distance_km} km`,
            });
        }
    }

    for (const w of workoutLogs.value) {
        if (w.date === dateStr) {
            events.push({
                type: 'workout',
                label: w.routine_name,
            });
        }
    }

    for (const t of tasks.value) {
        if (t.due_date === dateStr) {
            events.push({
                type: 'task',
                label: t.title,
            });
        }
    }

    return events;
}

// --- Month calendar ---

const monthDays = computed(() => {
    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay = new Date(currentYear, currentMonth + 1, 0);
    const startPad = mondayIndex(firstDay); // weeks start on Monday

    const days: (Date | null)[] = [];
    for (let i = 0; i < startPad; i++) {
        days.push(null);
    }
    for (let d = 1; d <= lastDay.getDate(); d++) {
        days.push(new Date(currentYear, currentMonth, d));
    }
    return days;
});

const monthName = today.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
});

function hasEventsOnDate(dateStr: string): {
    run: boolean;
    workout: boolean;
    task: boolean;
} {
    return {
        run: runs.value.some((r) => r.date === dateStr),
        workout: workoutLogs.value.some((w) => w.date === dateStr),
        task: tasks.value.some((t) => t.due_date === dateStr),
    };
}

function eventColorClass(type: 'run' | 'workout' | 'task'): string {
    switch (type) {
        case 'run':
            return 'bg-blue-500';
        case 'workout':
            return 'bg-green-500';
        case 'task':
            return 'bg-orange-500';
    }
}

function eventBorderClass(type: 'run' | 'workout' | 'task'): string {
    switch (type) {
        case 'run':
            return 'border-l-blue-500';
        case 'workout':
            return 'border-l-green-500';
        case 'task':
            return 'border-l-orange-500';
    }
}
</script>

<template>
    <div class="mx-auto max-w-6xl p-6">
        <h1 class="mb-6 text-2xl font-bold">Personal Tracker</h1>

        <LoadingState v-if="loading" label="Loading dashboard…" />

        <template v-else>
            <!-- Summary Cards -->
            <div
                class="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
            >
                <!-- Tasks Due Today -->
                <AppCard>
                    <template #title>
                        <div class="flex items-center gap-2">
                            <i class="pi pi-check-square text-orange-500"></i>
                            <span>Tasks Due Today</span>
                        </div>
                    </template>
                    <template #content>
                        <div class="text-2xl font-bold">
                            {{ tasksDueToday.dueCount }}
                        </div>
                        <div
                            v-if="tasksDueToday.overdueCount > 0"
                            class="text-sm font-semibold text-red-500"
                        >
                            {{ tasksDueToday.overdueCount }} overdue
                        </div>
                        <div v-else class="text-surface-500 text-sm">
                            none overdue
                        </div>
                    </template>
                </AppCard>

                <!-- Running This Week -->
                <AppCard>
                    <template #title>
                        <div class="flex items-center gap-2">
                            <i class="pi pi-bolt text-blue-500"></i>
                            <span>Running This Week</span>
                        </div>
                    </template>
                    <template #content>
                        <div class="text-2xl font-bold">
                            {{ weeklyRunning.distance }} km
                        </div>
                        <div class="text-surface-500 text-sm">
                            {{ weeklyRunning.count }}
                            {{ weeklyRunning.count === 1 ? 'run' : 'runs' }}
                        </div>
                    </template>
                </AppCard>

                <!-- Last Workout -->
                <AppCard>
                    <template #title>
                        <div class="flex items-center gap-2">
                            <i class="pi pi-heart text-green-500"></i>
                            <span>Last Workout</span>
                        </div>
                    </template>
                    <template #content>
                        <template v-if="lastWorkout">
                            <div class="text-2xl font-bold">
                                {{ formatIsoDate(lastWorkout.date) }}
                            </div>
                            <div class="text-surface-500 text-sm">
                                {{ lastWorkout.routineName }}
                            </div>
                        </template>
                        <div v-else class="text-surface-400 text-2xl font-bold">
                            &mdash;
                        </div>
                    </template>
                </AppCard>

                <!-- Quick Actions -->
                <AppCard>
                    <template #title>Quick Actions</template>
                    <template #content>
                        <div class="flex flex-col gap-2">
                            <AppButton
                                class="w-full"
                                icon="pi pi-plus"
                                label="Add Task"
                                outlined
                                size="small"
                                @click="openAddTask"
                            />
                            <AppButton
                                class="w-full"
                                icon="pi pi-plus"
                                label="Add Run"
                                outlined
                                size="small"
                                @click="openAddRun"
                            />
                            <AppButton
                                class="w-full"
                                icon="pi pi-list"
                                label="Log Workout"
                                outlined
                                size="small"
                                @click="router.push('/workout-routines')"
                            />
                        </div>
                    </template>
                </AppCard>
            </div>

            <!-- Countdowns -->
            <div class="mb-8">
                <div class="mb-4 flex items-center justify-between">
                    <h2 class="text-xl font-semibold">Countdowns</h2>
                    <AppButton
                        icon="pi pi-plus"
                        label="Add"
                        outlined
                        size="small"
                        @click="showAddCountdown = !showAddCountdown"
                    />
                </div>
                <div
                    v-if="showAddCountdown"
                    class="border-surface-200 dark:border-surface-700 mb-3 flex flex-wrap items-end gap-3 rounded-lg border p-3"
                >
                    <div class="min-w-48 flex-1">
                        <label class="mb-1 block text-xs font-medium"
                            >Title</label
                        >
                        <AppInputText
                            v-model="countdownForm.title"
                            class="w-full"
                            placeholder="e.g. Wicked 10K"
                            @keyup.enter="addCountdown"
                        />
                    </div>
                    <div>
                        <label class="mb-1 block text-xs font-medium"
                            >Date</label
                        >
                        <AppInputText
                            v-model="countdownForm.date"
                            type="date"
                        />
                    </div>
                    <AppButton
                        :disabled="
                            !countdownForm.title.trim() || !countdownForm.date
                        "
                        label="Save"
                        size="small"
                        @click="addCountdown"
                    />
                </div>
                <div
                    v-if="countdowns.length === 0"
                    class="text-surface-500 text-sm"
                >
                    No countdowns yet. Add a race or a deadline to see the days
                    remaining here.
                </div>
                <div
                    v-else
                    class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
                >
                    <div
                        v-for="c in countdowns"
                        :key="c.id"
                        class="border-surface-200 dark:border-surface-700 group relative rounded-lg border p-4"
                        :class="{ 'opacity-60': daysUntil(c.date) < 0 }"
                    >
                        <div
                            class="text-2xl font-bold"
                            :class="
                                daysUntil(c.date) < 0
                                    ? 'text-surface-500'
                                    : 'text-primary-600 dark:text-primary-400'
                            "
                        >
                            {{ countdownLabel(c.date) }}
                        </div>
                        <div class="truncate font-medium" :title="c.title">
                            {{ c.title }}
                        </div>
                        <div class="text-surface-500 text-xs">
                            {{ formatIsoDate(c.date) }}
                        </div>
                        <button
                            class="text-surface-400 absolute top-2 right-2 opacity-0 transition-opacity group-hover:opacity-100 hover:text-red-500"
                            title="Delete countdown"
                            @click="confirmDeleteCountdown(c)"
                        >
                            <i class="pi pi-times text-sm" />
                        </button>
                    </div>
                </div>
            </div>

            <!-- Calendar Section -->
            <div>
                <div class="mb-4 flex items-center justify-between">
                    <h2 class="text-xl font-semibold">Calendar</h2>
                    <AppSelectButton
                        v-model="calendarView"
                        option-label="label"
                        option-value="value"
                        :options="[
                            { label: '5-Day', value: '5-day' },
                            { label: 'Month', value: 'month' },
                        ]"
                    />
                </div>

                <!-- 5-Day View -->
                <div
                    v-if="calendarView === '5-day'"
                    class="grid grid-cols-5 gap-3"
                >
                    <div
                        v-for="day in next5Days"
                        :key="formatDate(day)"
                        class="border-surface-200 dark:border-surface-700 rounded-lg border p-3"
                        :class="{
                            'bg-primary-50 dark:bg-primary-950':
                                formatDate(day) === todayStr,
                        }"
                    >
                        <div class="mb-2 text-center">
                            <div class="text-surface-500 text-sm font-medium">
                                {{ getDayName(day) }}
                            </div>
                            <div class="text-lg font-bold">
                                {{ getDayNumber(day) }}
                            </div>
                        </div>
                        <div class="space-y-1">
                            <div
                                v-for="(event, idx) in getEventsForDate(
                                    formatDate(day),
                                )"
                                :key="idx"
                                class="truncate rounded border-l-3 px-2 py-1 text-xs"
                                :class="eventBorderClass(event.type)"
                            >
                                {{ event.label }}
                            </div>
                            <div
                                v-if="
                                    getEventsForDate(formatDate(day)).length ===
                                    0
                                "
                                class="text-surface-400 py-2 text-center text-xs"
                            >
                                No events
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Month View -->
                <div v-else>
                    <h3 class="mb-3 text-center text-lg font-medium">
                        {{ monthName }}
                    </h3>
                    <div class="grid grid-cols-7 gap-1">
                        <div
                            v-for="dayName in WEEKDAY_LABELS"
                            :key="dayName"
                            class="text-surface-500 py-1 text-center text-xs font-medium"
                        >
                            {{ dayName }}
                        </div>
                        <div
                            v-for="(day, idx) in monthDays"
                            :key="idx"
                            class="border-surface-100 dark:border-surface-800 min-h-16 rounded border p-1"
                            :class="{
                                'bg-primary-50 dark:bg-primary-950':
                                    day && formatDate(day) === todayStr,
                            }"
                        >
                            <template v-if="day">
                                <div class="text-xs font-medium">
                                    {{ getDayNumber(day) }}
                                </div>
                                <div class="mt-0.5 flex gap-1">
                                    <span
                                        v-if="
                                            hasEventsOnDate(formatDate(day)).run
                                        "
                                        v-tooltip="'Run'"
                                        class="inline-block h-2 w-2 rounded-full"
                                        :class="eventColorClass('run')"
                                    ></span>
                                    <span
                                        v-if="
                                            hasEventsOnDate(formatDate(day))
                                                .workout
                                        "
                                        v-tooltip="'Workout'"
                                        class="inline-block h-2 w-2 rounded-full"
                                        :class="eventColorClass('workout')"
                                    ></span>
                                    <span
                                        v-if="
                                            hasEventsOnDate(formatDate(day))
                                                .task
                                        "
                                        v-tooltip="'Task'"
                                        class="inline-block h-2 w-2 rounded-full"
                                        :class="eventColorClass('task')"
                                    ></span>
                                </div>
                            </template>
                        </div>
                    </div>
                    <!-- Legend -->
                    <div class="text-surface-500 mt-3 flex gap-4 text-xs">
                        <div class="flex items-center gap-1">
                            <span
                                class="inline-block h-2 w-2 rounded-full bg-blue-500"
                            ></span>
                            Running
                        </div>
                        <div class="flex items-center gap-1">
                            <span
                                class="inline-block h-2 w-2 rounded-full bg-green-500"
                            ></span>
                            Workouts
                        </div>
                        <div class="flex items-center gap-1">
                            <span
                                class="inline-block h-2 w-2 rounded-full bg-orange-500"
                            ></span>
                            Tasks
                        </div>
                    </div>
                </div>
            </div>
        </template>

        <!-- Add Task Dialog -->
        <AppDialog
            v-model:visible="showAddTask"
            header="Add Task"
            modal
            :style="{ width: '28rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Title <span class="text-red-500">*</span>
                    </label>
                    <AppInputText v-model="taskForm.title" class="w-full" />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Description
                    </label>
                    <AppTextarea
                        v-model="taskForm.description"
                        class="w-full"
                        rows="2"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Category
                    </label>
                    <AppInputText v-model="taskForm.category" class="w-full" />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Due Date
                    </label>
                    <AppInputText
                        v-model="taskForm.due_date"
                        class="w-full"
                        type="date"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showAddTask = false"
                    />
                    <span v-tooltip.top="taskSaveTooltip">
                        <AppButton
                            :disabled="!isTaskFormValid"
                            label="Save"
                            @click="saveTask"
                        />
                    </span>
                </div>
            </div>
        </AppDialog>

        <!-- Add Run Dialog -->
        <AppDialog
            v-model:visible="showAddRun"
            header="Add Run"
            modal
            :style="{ width: '28rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium"> Date </label>
                    <AppInputText
                        v-model="runForm.date"
                        class="w-full"
                        type="date"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Title
                    </label>
                    <AppInputText
                        v-model="runForm.title"
                        class="w-full"
                        placeholder="e.g. Morning Run"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Distance (km)
                    </label>
                    <AppInputNumber
                        v-model="runForm.distance_km"
                        class="w-full"
                        :max-fraction-digits="2"
                        :min-fraction-digits="1"
                        :step="0.1"
                        suffix=" km"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Duration
                    </label>
                    <div class="flex items-center gap-2">
                        <AppInputNumber
                            v-model="runForm.minutes"
                            class="min-w-0 flex-1"
                            fluid
                            :min="0"
                            suffix=" min"
                        />
                        <AppInputNumber
                            v-model="runForm.seconds"
                            class="min-w-0 flex-1"
                            fluid
                            :max="59"
                            :min="0"
                            suffix=" sec"
                        />
                    </div>
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Notes
                    </label>
                    <AppTextarea
                        v-model="runForm.notes"
                        class="w-full"
                        rows="2"
                    />
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showAddRun = false"
                    />
                    <AppButton label="Save" @click="saveRun" />
                </div>
            </div>
        </AppDialog>

        <!-- Delete Countdown Confirmation -->
        <AppDialog
            v-model:visible="showDeleteCountdown"
            header="Confirm Delete"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <p>Are you sure you want to delete this countdown?</p>
            <div class="mt-4 flex justify-end gap-2">
                <AppButton
                    label="Cancel"
                    text
                    @click="showDeleteCountdown = false"
                />
                <AppButton
                    label="Delete"
                    severity="danger"
                    @click="executeDeleteCountdown"
                />
            </div>
        </AppDialog>
    </div>
</template>
