<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { useRunningApi } from '@/composables/api/useRunningApi';
import { useTaskApi } from '@/composables/api/useTaskApi';
import { useWorkoutLogApi } from '@/composables/api/useWorkoutLogApi';
import { useToast } from '@/composables/useToast';
import type { RunningActivity } from '@/types/Running';
import type { Task, TaskCreate } from '@/types/Task';
import type { WorkoutLog } from '@/types/WorkoutLog';

const { getActivities, createActivity } = useRunningApi();
const { getTasks, createTask } = useTaskApi();
const { getWorkoutLogs } = useWorkoutLogApi();
const toast = useToast();

const runs = ref<RunningActivity[]>([]);
const tasks = ref<Task[]>([]);
const workoutLogs = ref<WorkoutLog[]>([]);
const calendarView = ref<'5-day' | 'month'>('5-day');

const today = new Date();
const todayStr = today.toISOString().split('T')[0] as string;
const currentYear = today.getFullYear();
const currentMonth = today.getMonth();

onMounted(async () => {
    const [runsRes, tasksRes, logsRes] = await Promise.all([
        getActivities(),
        getTasks(),
        getWorkoutLogs(),
    ]);
    if (runsRes.success && runsRes.data) runs.value = runsRes.data;
    if (tasksRes.success && tasksRes.data) tasks.value = tasksRes.data;
    if (logsRes.success && logsRes.data) workoutLogs.value = logsRes.data;
});

// --- Summary computations ---

const runningSummary = computed(() => {
    const monthStart = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-01`;
    const monthEnd = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-31`;
    const monthRuns = runs.value.filter(
        (r) => r.date >= monthStart && r.date <= monthEnd,
    );
    const totalDistance = monthRuns.reduce((sum, r) => sum + r.distance_km, 0);
    const avgPace =
        monthRuns.length > 0
            ? monthRuns.reduce((sum, r) => sum + r.pace, 0) / monthRuns.length
            : 0;
    const avgMin = Math.floor(avgPace);
    const avgSec = Math.round((avgPace - avgMin) * 60);
    return {
        count: monthRuns.length,
        totalDistance: totalDistance.toFixed(1),
        avgPace: `${avgMin}:${String(avgSec).padStart(2, '0')}`,
    };
});

const workoutSummary = computed(() => {
    const recentLogs = workoutLogs.value.slice(0, 5);
    const lastDate =
        workoutLogs.value.length > 0
            ? (workoutLogs.value[0] as WorkoutLog).date
            : 'N/A';
    return {
        totalLogs: workoutLogs.value.length,
        recentCount: recentLogs.length,
        lastDate,
    };
});

const taskSummary = computed(() => {
    const incomplete = tasks.value.filter((t) => !t.completed);
    const overdue = incomplete.filter(
        (t) => t.due_date && t.due_date < todayStr,
    );
    const completedToday = tasks.value.filter(
        (t) => t.completed && t.updated_at.startsWith(todayStr),
    );
    return {
        incomplete: incomplete.length,
        overdue: overdue.length,
        completedToday: completedToday.length,
    };
});

// --- Add Run dialog ---
const showAddRun = ref(false);
const runForm = reactive({
    date: todayStr,
    minutes: 0,
    seconds: 0,
    distance_km: 0,
    notes: '',
});

function openAddRun() {
    runForm.date = todayStr;
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

// --- Calendar helpers ---

function formatDate(date: Date): string {
    return date.toISOString().split('T')[0] as string;
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
    const startPad = firstDay.getDay();

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
        <h1 class="mb-6 text-3xl font-bold">
            Personal Fitness and Task Tracker
        </h1>

        <!-- Summary Cards -->
        <div class="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
            <!-- Running Summary -->
            <AppCard class="group">
                <template #title>
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <i class="pi pi-bolt text-blue-500"></i>
                            <span>Running</span>
                        </div>
                        <AppButton
                            class="opacity-0 transition-opacity group-hover:opacity-100"
                            icon="pi pi-plus"
                            rounded
                            size="small"
                            text
                            @click="openAddRun"
                        />
                    </div>
                </template>
                <template #content>
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span class="text-surface-500">
                                Runs this month
                            </span>
                            <span class="font-semibold">
                                {{ runningSummary.count }}
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-surface-500">
                                Total distance
                            </span>
                            <span class="font-semibold">
                                {{ runningSummary.totalDistance }} km
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-surface-500">Avg pace</span>
                            <span class="font-semibold">
                                {{ runningSummary.avgPace }} /km
                            </span>
                        </div>
                    </div>
                </template>
            </AppCard>

            <!-- Workouts Summary -->
            <AppCard>
                <template #title>
                    <div class="flex items-center gap-2">
                        <i class="pi pi-heart text-green-500"></i>
                        <span>Workouts</span>
                    </div>
                </template>
                <template #content>
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span class="text-surface-500">Total logs</span>
                            <span class="font-semibold">
                                {{ workoutSummary.totalLogs }}
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-surface-500">Recent</span>
                            <span class="font-semibold">
                                {{ workoutSummary.recentCount }}
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-surface-500"> Last workout </span>
                            <span class="font-semibold">
                                {{ workoutSummary.lastDate }}
                            </span>
                        </div>
                    </div>
                </template>
            </AppCard>

            <!-- Tasks Summary -->
            <AppCard class="group">
                <template #title>
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <i class="pi pi-check-square text-orange-500"></i>
                            <span>Tasks</span>
                        </div>
                        <AppButton
                            class="opacity-0 transition-opacity group-hover:opacity-100"
                            icon="pi pi-plus"
                            rounded
                            size="small"
                            text
                            @click="openAddTask"
                        />
                    </div>
                </template>
                <template #content>
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span class="text-surface-500">Incomplete</span>
                            <span class="font-semibold">
                                {{ taskSummary.incomplete }}
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-surface-500">Overdue</span>
                            <span class="font-semibold text-red-500">
                                {{ taskSummary.overdue }}
                            </span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-surface-500">
                                Completed today
                            </span>
                            <span class="font-semibold">
                                {{ taskSummary.completedToday }}
                            </span>
                        </div>
                    </div>
                </template>
            </AppCard>
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
            <div v-if="calendarView === '5-day'" class="grid grid-cols-5 gap-3">
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
                                getEventsForDate(formatDate(day)).length === 0
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
                        v-for="dayName in [
                            'Sun',
                            'Mon',
                            'Tue',
                            'Wed',
                            'Thu',
                            'Fri',
                            'Sat',
                        ]"
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
                                    v-if="hasEventsOnDate(formatDate(day)).run"
                                    v-tooltip="'Run'"
                                    class="inline-block h-2 w-2 rounded-full"
                                    :class="eventColorClass('run')"
                                ></span>
                                <span
                                    v-if="
                                        hasEventsOnDate(formatDate(day)).workout
                                    "
                                    v-tooltip="'Workout'"
                                    class="inline-block h-2 w-2 rounded-full"
                                    :class="eventColorClass('workout')"
                                ></span>
                                <span
                                    v-if="hasEventsOnDate(formatDate(day)).task"
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
        <!-- Add Task Dialog -->
        <AppDialog
            v-model:visible="showAddTask"
            header="Add Task"
            modal
            :style="{ width: '28rem' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Title
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
                    <AppButton label="Save" @click="saveTask" />
                </div>
            </div>
        </AppDialog>

        <!-- Add Run Dialog -->
        <AppDialog
            v-model:visible="showAddRun"
            header="Add Run"
            modal
            :style="{ width: '28rem' }"
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
                            class="w-full"
                            :min="0"
                            suffix=" min"
                        />
                        <AppInputNumber
                            v-model="runForm.seconds"
                            class="w-full"
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
    </div>
</template>
