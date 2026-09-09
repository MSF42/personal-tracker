<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import ConfirmDeleteDialog from '@/components/ConfirmDeleteDialog.vue';
import LoadingState from '@/components/LoadingState.vue';
import { useHabitApi } from '@/composables/api/useHabitApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
import type { Habit, HabitCreate, HabitUpdate } from '@/types/Habit';
import { formatDate } from '@/utils/format';
import { toIsoDate, weekDays } from '@/utils/week';

const {
    getHabits,
    createHabit,
    updateHabit,
    deleteHabit,
    toggleCompletion,
    getCompletionHistory,
} = useHabitApi();
const { loading, withLoading } = useLoading();
const toast = useToast();
const route = useRoute();
const router = useRouter();

const habits = ref<Habit[]>([]);
const completionHistory = ref<Record<number, string[]>>({});
const todayStr = toIsoDate(new Date());
const showArchived = ref(false);

// --- View mode ---
const viewMode = ref<'cards' | 'chain'>('cards');
const viewOptions = [
    { label: 'Cards', value: 'cards' },
    { label: 'Chain', value: 'chain' },
];

// --- Chain / history helpers ---
const last28Days = computed<string[]>(() => {
    const days: string[] = [];
    const today = new Date();
    for (let i = 27; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        days.push(toIsoDate(d));
    }
    return days;
});

const last7Days = computed(() => last28Days.value.slice(-7));

// Four calendar weeks (Mon..Sun) ending with the current week, for the
// dot-chain view. Days after today are shown as placeholders.
const weeksOf7 = computed(() => {
    const now = new Date();
    return [-3, -2, -1, 0].map((offset) => weekDays(now, offset));
});
const WEEK_LABELS = ['3 wks ago', '2 wks ago', 'Last week', 'This week'];

function isDayCompleted(habitId: number, dateStr: string): boolean {
    return completionHistory.value[habitId]?.includes(dateStr) ?? false;
}

function streakProgress(habit: Habit): number {
    if (!habit.longest_streak) return 0;
    return Math.min(
        100,
        Math.round((habit.current_streak / habit.longest_streak) * 100),
    );
}

// --- Computed ---
const activeHabits = computed(() => habits.value.filter((h) => !h.archived));
const archivedHabits = computed(() => habits.value.filter((h) => h.archived));

const stats = computed(() => {
    const completedToday = activeHabits.value.filter(
        (h) => h.completed_today,
    ).length;
    return { total: activeHabits.value.length, completedToday };
});

// --- Dialog state ---
const showDialog = ref(false);
const editingId = ref<number | null>(null);
const showDeleteConfirm = ref(false);
const deletingId = ref<number | null>(null);

const isFormValid = computed(() => form.name.trim() !== '');
const saveTooltip = computed(() =>
    isFormValid.value ? undefined : 'Name is required',
);

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const frequencyOptions = [
    { label: 'Daily', value: 'daily' },
    { label: 'Weekdays', value: 'weekdays' },
    { label: 'Weekly', value: 'weekly' },
];

// Preset swatches instead of a raw native color input, to match the rest of
// the app's themed controls.
const PRESET_COLORS = [
    { hex: '#ef4444', name: 'Red' },
    { hex: '#f97316', name: 'Orange' },
    { hex: '#f59e0b', name: 'Amber' },
    { hex: '#22c55e', name: 'Green' },
    { hex: '#06b6d4', name: 'Cyan' },
    { hex: '#3b82f6', name: 'Blue' },
    { hex: '#8b5cf6', name: 'Violet' },
    { hex: '#ec4899', name: 'Pink' },
    { hex: '#64748b', name: 'Slate' },
];

const form = reactive({
    name: '',
    description: '',
    frequency: 'daily' as 'daily' | 'weekdays' | 'weekly',
    frequency_days: [] as number[],
    color: '#3b82f6',
});

function resetForm() {
    form.name = '';
    form.description = '';
    form.frequency = 'daily';
    form.frequency_days = [];
    form.color = '#3b82f6';
    editingId.value = null;
}

function openAddDialog() {
    resetForm();
    showDialog.value = true;
}

function openEditDialog(habit: Habit) {
    editingId.value = habit.id;
    form.name = habit.name;
    form.description = habit.description ?? '';
    form.frequency = habit.frequency;
    form.frequency_days = habit.frequency_days ?? [];
    form.color = habit.color;
    showDialog.value = true;
}

function toggleDay(day: number) {
    const idx = form.frequency_days.indexOf(day);
    if (idx === -1) {
        form.frequency_days.push(day);
        form.frequency_days.sort();
    } else {
        form.frequency_days.splice(idx, 1);
    }
}

async function saveHabit() {
    if (editingId.value) {
        const payload: HabitUpdate = {
            name: form.name,
            description: form.description || null,
            frequency: form.frequency,
            frequency_days:
                form.frequency === 'weekly' && form.frequency_days.length
                    ? form.frequency_days
                    : null,
            color: form.color,
        };
        const res = await updateHabit(editingId.value, payload);
        if (res.success) {
            toast.showSuccess('Habit updated');
            showDialog.value = false;
            await loadData();
        } else {
            toast.showError(res.error?.message ?? 'Failed to save habit');
        }
    } else {
        const payload: HabitCreate = {
            name: form.name,
            description: form.description || null,
            frequency: form.frequency,
            frequency_days:
                form.frequency === 'weekly' && form.frequency_days.length
                    ? form.frequency_days
                    : null,
            color: form.color,
        };
        const res = await createHabit(payload);
        if (res.success) {
            toast.showSuccess('Habit created');
            showDialog.value = false;
            await loadData();
        } else {
            toast.showError(res.error?.message ?? 'Failed to save habit');
        }
    }
}

function confirmDelete(id: number) {
    deletingId.value = id;
    showDeleteConfirm.value = true;
}

async function executeDelete() {
    if (deletingId.value) {
        const res = await deleteHabit(deletingId.value);
        if (res.success) toast.showSuccess('Habit deleted');
        else toast.showError(res.error?.message ?? 'Failed to delete habit');
    }
    showDeleteConfirm.value = false;
    deletingId.value = null;
    await loadData();
}

async function toggle(habit: Habit, date: string = todayStr) {
    if (date > todayStr) return; // can't log a day that hasn't happened yet
    const res = await toggleCompletion(habit.id, date);
    if (res.success && res.data) {
        const idx = habits.value.findIndex((h) => h.id === habit.id);
        if (idx !== -1) habits.value[idx] = res.data;
        // Update history locally so dots update immediately. Assign a new
        // array (rather than push/splice on a possibly-missing one) so this
        // works even for a habit with zero completions in the loaded range.
        const existing = completionHistory.value[habit.id] ?? [];
        const dateIdx = existing.indexOf(date);
        completionHistory.value[habit.id] =
            dateIdx === -1
                ? [...existing, date]
                : existing.filter((d) => d !== date);
    } else if (!res.success) {
        toast.showError(res.error?.message ?? 'Failed to update habit');
    }
}

async function archiveHabit(habit: Habit) {
    const res = await updateHabit(habit.id, { archived: true });
    if (res.success) {
        toast.showSuccess('Habit archived');
        await loadData();
    } else {
        toast.showError(res.error?.message ?? 'Failed to archive habit');
    }
}

async function restoreHabit(habit: Habit) {
    const res = await updateHabit(habit.id, { archived: false });
    if (res.success) {
        toast.showSuccess('Habit restored');
        await loadData();
    } else {
        toast.showError(res.error?.message ?? 'Failed to restore habit');
    }
}

async function loadData() {
    const [habitsRes, historyRes] = await Promise.all([
        getHabits(true),
        getCompletionHistory(28),
    ]);
    if (habitsRes.success && habitsRes.data) habits.value = habitsRes.data;
    else if (!habitsRes.success) toast.showError('Failed to load habits');
    if (historyRes.success && historyRes.data) {
        completionHistory.value = Object.fromEntries(
            Object.entries(historyRes.data).map(([k, v]) => [Number(k), v]),
        );
    }
}

// Landing here from a command-palette search hit (`/habits?habit=123`)
// opens that habit for editing, then clears the param.
async function openFromSearch() {
    const id = Number(route.query.habit);
    if (!id) return;
    const match = habits.value.find((h) => h.id === id);
    if (match) openEditDialog(match);
    const { habit: _habit, ...rest } = route.query;
    await router.replace({ query: rest });
}

onMounted(() => withLoading(loadData).then(openFromSearch));

const dialogHeader = computed(() =>
    editingId.value ? 'Edit Habit' : 'Add Habit',
);
</script>

<template>
    <div class="mx-auto max-w-6xl p-6">
        <h1 class="mb-6 text-2xl font-bold">Habits</h1>

        <!-- Stats -->
        <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <AppCard>
                <template #title>Active Habits</template>
                <template #content>
                    <div class="text-2xl font-bold">{{ stats.total }}</div>
                    <div class="text-surface-500 text-sm">habits tracked</div>
                </template>
            </AppCard>
            <AppCard>
                <template #title>Completed Today</template>
                <template #content>
                    <div class="text-2xl font-bold text-green-500">
                        {{ stats.completedToday }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        of {{ stats.total }} habits done
                    </div>
                </template>
            </AppCard>
        </div>

        <!-- Header -->
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
            <h2 class="text-xl font-semibold">Today's Habits</h2>
            <div class="flex items-center gap-2">
                <AppSelectButton
                    v-model="viewMode"
                    :allow-empty="false"
                    option-label="label"
                    option-value="value"
                    :options="viewOptions"
                    size="small"
                />
                <AppButton
                    icon="pi pi-plus"
                    label="Add Habit"
                    @click="openAddDialog"
                />
            </div>
        </div>

        <!-- Loading -->
        <LoadingState v-if="loading" label="Loading habits…" />

        <!-- Chain view: 4-week completion history as a dot grid -->
        <div
            v-else-if="viewMode === 'chain' && activeHabits.length > 0"
            class="border-surface-200 dark:border-surface-700 overflow-hidden rounded-xl border bg-white dark:bg-slate-800"
        >
            <!-- Column headers: week labels. Small screens show only "This
                 week" (a shorter period) rather than scrolling horizontally
                 to fit all 4. -->
            <div
                class="border-surface-200 dark:border-surface-700 grid grid-cols-[6rem_minmax(0,1fr)_auto_auto] gap-2 border-b px-3 py-2 sm:grid-cols-[14rem_minmax(0,1fr)_auto_auto] sm:gap-4 sm:px-4"
            >
                <span class="text-surface-400 text-xs font-medium">Habit</span>
                <div class="flex gap-6 pl-1">
                    <span
                        v-for="(_, wi) in weeksOf7"
                        :key="wi"
                        class="text-surface-400 flex-1 text-center text-xs"
                        :class="wi < 3 ? 'hidden sm:block' : 'block'"
                    >
                        {{ WEEK_LABELS[wi] }}
                    </span>
                </div>
                <span class="text-surface-400 w-10 text-center text-xs sm:w-16"
                    >Streak</span
                >
                <span class="text-surface-400 w-16 text-center text-xs"
                    >Actions</span
                >
            </div>

            <!-- Habit rows -->
            <div
                v-for="(habit, idx) in activeHabits"
                :key="habit.id"
                class="grid grid-cols-[6rem_minmax(0,1fr)_auto_auto] items-center gap-2 px-3 py-3 transition-colors hover:bg-slate-50 sm:grid-cols-[14rem_minmax(0,1fr)_auto_auto] sm:gap-4 sm:px-4 dark:hover:bg-slate-700/40"
                :class="{
                    'border-surface-100 dark:border-surface-700 border-t':
                        idx > 0,
                }"
            >
                <!-- Name + color + check button -->
                <div class="flex min-w-0 items-center gap-2">
                    <div
                        class="h-3 w-3 shrink-0 rounded-full"
                        :style="{ backgroundColor: habit.color }"
                    ></div>
                    <span
                        class="text-primary min-w-0 flex-1 cursor-pointer truncate text-sm font-medium hover:underline"
                        @click="openEditDialog(habit)"
                    >
                        {{ habit.name }}
                    </span>
                    <button
                        :aria-label="
                            habit.completed_today
                                ? 'Mark incomplete'
                                : 'Mark complete'
                        "
                        class="shrink-0 rounded-full p-0.5 transition-opacity"
                        :title="
                            habit.completed_today
                                ? 'Mark incomplete'
                                : 'Mark complete'
                        "
                        @click="toggle(habit)"
                    >
                        <i
                            class="text-base"
                            :class="
                                habit.completed_today
                                    ? 'pi pi-check-circle text-green-500'
                                    : 'pi pi-circle text-surface-300 dark:text-surface-600'
                            "
                        ></i>
                    </button>
                </div>

                <!-- 28 dot chain (4 weeks × 7 days). Small screens show only
                     "This week" — a shorter period fits without needing to
                     scroll the table horizontally. -->
                <div class="flex gap-1 sm:gap-1.5">
                    <div
                        v-for="(week, wi) in weeksOf7"
                        :key="wi"
                        class="flex flex-1 justify-around"
                        :class="wi < 3 ? 'hidden sm:flex' : 'flex'"
                    >
                        <button
                            v-for="day in week"
                            :key="day"
                            :aria-label="`${formatDate(day)}: ${
                                isDayCompleted(habit.id, day)
                                    ? 'completed'
                                    : 'not completed'
                            }${day > todayStr ? ' (upcoming)' : ''}`"
                            class="h-4 w-4 rounded-full transition-all sm:h-5 sm:w-5"
                            :class="[
                                isDayCompleted(habit.id, day)
                                    ? ''
                                    : 'bg-surface-100 dark:bg-surface-700',
                                day > todayStr
                                    ? 'cursor-not-allowed opacity-30'
                                    : 'cursor-pointer hover:opacity-75',
                            ]"
                            :disabled="day > todayStr"
                            :style="[
                                isDayCompleted(habit.id, day)
                                    ? { backgroundColor: habit.color }
                                    : {},
                                day === todayStr
                                    ? {
                                          outline: `2px solid ${habit.color}`,
                                          outlineOffset: '2px',
                                      }
                                    : {},
                            ]"
                            :title="formatDate(day)"
                            type="button"
                            @click="toggle(habit, day)"
                        ></button>
                    </div>
                </div>

                <!-- Streak badge -->
                <div class="flex w-10 items-center justify-center sm:w-16">
                    <span
                        v-if="habit.current_streak > 0"
                        class="inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-semibold"
                        :style="{
                            backgroundColor: habit.color + '22',
                            color: habit.color,
                        }"
                    >
                        <i class="pi pi-bolt text-[10px]"></i>
                        {{ habit.current_streak }}
                    </span>
                    <span v-else class="text-surface-300 text-xs">—</span>
                </div>

                <!-- Actions -->
                <div class="flex w-16 items-center justify-center gap-1">
                    <AppButton
                        aria-label="Archive habit"
                        icon="pi pi-inbox"
                        rounded
                        severity="secondary"
                        size="small"
                        text
                        title="Archive habit"
                        @click="archiveHabit(habit)"
                    />
                    <AppButton
                        aria-label="Delete habit"
                        icon="pi pi-trash"
                        rounded
                        severity="danger"
                        size="small"
                        text
                        @click="confirmDelete(habit.id)"
                    />
                </div>
            </div>
        </div>

        <!-- Cards view: one card per habit, with streak stats and full actions -->
        <div
            v-else-if="viewMode === 'cards' && activeHabits.length > 0"
            class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
        >
            <div
                v-for="habit in activeHabits"
                :key="habit.id"
                class="border-surface-200 dark:border-surface-700 flex overflow-hidden rounded-xl border bg-white shadow-sm dark:bg-slate-800"
            >
                <!-- Left accent -->
                <div
                    class="w-2 shrink-0"
                    :style="{ backgroundColor: habit.color }"
                ></div>

                <div class="flex flex-1 flex-col gap-3 p-4">
                    <!-- Name + description -->
                    <div class="min-w-0">
                        <div class="truncate font-semibold">
                            {{ habit.name }}
                        </div>
                        <div
                            v-if="habit.description"
                            class="text-surface-500 mt-0.5 truncate text-xs"
                        >
                            {{ habit.description }}
                        </div>
                    </div>

                    <!-- Big streak number -->
                    <div class="flex items-end gap-3">
                        <div
                            class="text-5xl leading-none font-bold tabular-nums"
                            :style="{ color: habit.color }"
                        >
                            {{ habit.current_streak }}
                        </div>
                        <div
                            class="text-surface-500 mb-1 text-sm leading-tight"
                        >
                            <div class="font-medium">day streak</div>
                            <div class="text-xs">
                                best: {{ habit.longest_streak }}d
                            </div>
                        </div>
                        <span
                            v-if="
                                habit.current_streak > 0 &&
                                habit.current_streak === habit.longest_streak
                            "
                            class="mb-1 ml-auto inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-semibold"
                            :style="{
                                backgroundColor: habit.color + '22',
                                color: habit.color,
                            }"
                        >
                            <i class="pi pi-bolt text-[10px]"></i>
                            Personal best
                        </span>
                    </div>

                    <!-- Last 7 days mini-dots -->
                    <div>
                        <div class="text-surface-400 mb-1.5 text-xs">
                            Last 7 days
                        </div>
                        <div class="flex gap-1">
                            <button
                                v-for="day in last7Days"
                                :key="day"
                                :aria-label="`${formatDate(day)}: ${
                                    isDayCompleted(habit.id, day)
                                        ? 'completed'
                                        : 'not completed'
                                }`"
                                class="h-5 flex-1 cursor-pointer rounded-sm transition-all hover:opacity-75"
                                :class="[
                                    day === todayStr ? 'ring-1' : '',
                                    isDayCompleted(habit.id, day)
                                        ? ''
                                        : 'bg-surface-100 dark:bg-surface-700',
                                ]"
                                :style="
                                    isDayCompleted(habit.id, day)
                                        ? { backgroundColor: habit.color }
                                        : {}
                                "
                                :title="formatDate(day)"
                                type="button"
                                @click="toggle(habit, day)"
                            ></button>
                        </div>
                        <div
                            class="text-surface-400 mt-1 flex justify-between text-[10px]"
                        >
                            <span>7d ago</span><span>Today</span>
                        </div>
                    </div>

                    <!-- Progress bar (current / longest) -->
                    <div v-if="habit.longest_streak > 0">
                        <div
                            class="bg-surface-100 dark:bg-surface-700 h-1.5 w-full overflow-hidden rounded-full"
                        >
                            <div
                                class="h-full rounded-full transition-all duration-500"
                                :style="{
                                    width: streakProgress(habit) + '%',
                                    backgroundColor: habit.color,
                                }"
                            ></div>
                        </div>
                        <div
                            class="text-surface-400 mt-1 text-right text-[10px]"
                        >
                            {{ streakProgress(habit) }}% of best
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="mt-auto flex items-center justify-between">
                        <div class="flex items-center gap-1">
                            <AppButton
                                aria-label="Edit habit"
                                icon="pi pi-pencil"
                                rounded
                                severity="info"
                                size="small"
                                text
                                @click="openEditDialog(habit)"
                            />
                            <AppButton
                                aria-label="Archive habit"
                                icon="pi pi-inbox"
                                rounded
                                severity="secondary"
                                size="small"
                                text
                                title="Archive habit"
                                @click="archiveHabit(habit)"
                            />
                            <AppButton
                                aria-label="Delete habit"
                                icon="pi pi-trash"
                                rounded
                                severity="danger"
                                size="small"
                                text
                                @click="confirmDelete(habit.id)"
                            />
                        </div>
                        <AppButton
                            :aria-label="
                                habit.completed_today
                                    ? 'Mark incomplete'
                                    : 'Mark complete'
                            "
                            :icon="
                                habit.completed_today
                                    ? 'pi pi-check-circle'
                                    : 'pi pi-circle'
                            "
                            rounded
                            :severity="
                                habit.completed_today ? 'success' : 'secondary'
                            "
                            size="small"
                            :title="
                                habit.completed_today
                                    ? 'Mark incomplete'
                                    : 'Mark complete'
                            "
                            @click="toggle(habit)"
                        />
                    </div>
                </div>
            </div>
        </div>

        <div
            v-else-if="!loading"
            class="flex flex-col items-center py-10 text-center"
        >
            <i
                class="pi pi-inbox text-surface-300 dark:text-surface-600 mb-3 text-4xl"
            ></i>
            <p class="text-surface-500 mb-3">No habits yet</p>
            <AppButton
                icon="pi pi-plus"
                label="Add your first habit"
                size="small"
                @click="openAddDialog"
            />
        </div>

        <!-- Archived section -->
        <div v-if="archivedHabits.length > 0" class="mt-8">
            <div class="mb-3 flex items-center gap-3">
                <h2 class="text-surface-500 text-lg font-semibold">Archived</h2>
                <AppButton
                    :icon="
                        showArchived ? 'pi pi-chevron-up' : 'pi pi-chevron-down'
                    "
                    :label="
                        showArchived
                            ? 'Hide'
                            : `Show (${archivedHabits.length})`
                    "
                    severity="secondary"
                    size="small"
                    text
                    @click="showArchived = !showArchived"
                />
            </div>
            <div
                v-if="showArchived"
                class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
            >
                <div
                    v-for="habit in archivedHabits"
                    :key="habit.id"
                    class="border-surface-200 dark:border-surface-700 flex overflow-hidden rounded-lg border bg-white opacity-60 shadow-sm dark:bg-slate-800"
                >
                    <div
                        class="w-1.5 shrink-0"
                        :style="{ backgroundColor: habit.color }"
                    ></div>
                    <div class="flex-1 p-4">
                        <div
                            class="mb-2 flex items-center justify-between gap-2"
                        >
                            <div class="min-w-0 flex-1">
                                <div
                                    class="text-surface-500 truncate font-semibold line-through"
                                >
                                    {{ habit.name }}
                                </div>
                            </div>
                            <div class="flex items-center gap-1">
                                <AppButton
                                    aria-label="Restore habit"
                                    icon="pi pi-replay"
                                    rounded
                                    severity="success"
                                    size="small"
                                    text
                                    title="Restore habit"
                                    @click="restoreHabit(habit)"
                                />
                                <AppButton
                                    aria-label="Delete habit"
                                    icon="pi pi-trash"
                                    rounded
                                    severity="danger"
                                    size="small"
                                    text
                                    @click="confirmDelete(habit.id)"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Add/Edit Dialog -->
        <AppDialog
            v-model:visible="showDialog"
            :header="dialogHeader"
            modal
            :style="{ width: '28rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Name <span class="text-red-500">*</span>
                    </label>
                    <AppInputText v-model="form.name" class="w-full" />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium"
                        >Description</label
                    >
                    <AppTextarea
                        v-model="form.description"
                        class="w-full"
                        rows="2"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium"
                        >Frequency</label
                    >
                    <AppSelect
                        v-model="form.frequency"
                        class="w-full"
                        option-label="label"
                        option-value="value"
                        :options="frequencyOptions"
                    />
                </div>
                <div v-if="form.frequency === 'weekly'">
                    <label class="mb-1 block text-sm font-medium"
                        >Days of Week</label
                    >
                    <div class="flex flex-wrap gap-1">
                        <AppButton
                            v-for="(label, idx) in DAY_LABELS"
                            :key="idx"
                            :label="label"
                            :outlined="!form.frequency_days.includes(idx)"
                            :severity="
                                form.frequency_days.includes(idx)
                                    ? 'primary'
                                    : 'secondary'
                            "
                            size="small"
                            @click="toggleDay(idx)"
                        />
                    </div>
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">Color</label>
                    <div class="flex flex-wrap gap-2">
                        <button
                            v-for="preset in PRESET_COLORS"
                            :key="preset.hex"
                            :aria-label="preset.name"
                            :aria-pressed="form.color === preset.hex"
                            class="h-8 w-8 shrink-0 cursor-pointer rounded-full ring-offset-2 ring-offset-white transition-shadow outline-none dark:ring-offset-slate-800"
                            :class="
                                form.color === preset.hex
                                    ? 'ring-surface-900 dark:ring-surface-100 ring-2'
                                    : ''
                            "
                            :style="{ backgroundColor: preset.hex }"
                            :title="preset.name"
                            type="button"
                            @click="form.color = preset.hex"
                        >
                            <i
                                v-if="form.color === preset.hex"
                                class="pi pi-check text-xs text-white mix-blend-difference"
                            ></i>
                        </button>
                    </div>
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showDialog = false"
                    />
                    <span v-tooltip.top="saveTooltip">
                        <AppButton
                            :disabled="!isFormValid"
                            label="Save"
                            @click="saveHabit"
                        />
                    </span>
                </div>
            </div>
        </AppDialog>

        <!-- Delete Confirmation -->
        <ConfirmDeleteDialog
            v-model:visible="showDeleteConfirm"
            @confirm="executeDelete"
        >
            Are you sure you want to delete this habit?
        </ConfirmDeleteDialog>
    </div>
</template>
