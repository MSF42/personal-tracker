<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { useHabitApi } from '@/composables/api/useHabitApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
import type { Habit, HabitCreate, HabitUpdate } from '@/types/Habit';

const { getHabits, createHabit, updateHabit, deleteHabit, toggleCompletion } =
    useHabitApi();
const { loading, withLoading } = useLoading();
const toast = useToast();

const habits = ref<Habit[]>([]);
const todayStr = new Date().toISOString().split('T')[0] as string;
const showArchived = ref(false);

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

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const frequencyOptions = [
    { label: 'Daily', value: 'daily' },
    { label: 'Weekdays', value: 'weekdays' },
    { label: 'Weekly', value: 'weekly' },
];

const form = reactive({
    name: '',
    description: '',
    frequency: 'daily' as string,
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
        if (res.success) toast.showSuccess('Habit updated');
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
        if (res.success) toast.showSuccess('Habit created');
    }
    showDialog.value = false;
    await loadData();
}

function confirmDelete(id: number) {
    deletingId.value = id;
    showDeleteConfirm.value = true;
}

async function executeDelete() {
    if (deletingId.value) {
        const res = await deleteHabit(deletingId.value);
        if (res.success) toast.showSuccess('Habit deleted');
    }
    showDeleteConfirm.value = false;
    deletingId.value = null;
    await loadData();
}

async function toggle(habit: Habit) {
    const res = await toggleCompletion(habit.id, todayStr);
    if (res.success && res.data) {
        const idx = habits.value.findIndex((h) => h.id === habit.id);
        if (idx !== -1) habits.value[idx] = res.data;
    }
}

async function loadData() {
    const res = await getHabits(true);
    if (res.success && res.data) habits.value = res.data;
}

async function archiveHabit(habit: Habit) {
    const res = await updateHabit(habit.id, { archived: true });
    if (res.success) {
        toast.showSuccess('Habit archived');
        await loadData();
    }
}

async function restoreHabit(habit: Habit) {
    const res = await updateHabit(habit.id, { archived: false });
    if (res.success) {
        toast.showSuccess('Habit restored');
        await loadData();
    }
}

onMounted(() => withLoading(loadData));

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
        <div class="mb-4 flex items-center justify-between">
            <h2 class="text-xl font-semibold">Today's Habits</h2>
            <AppButton
                icon="pi pi-plus"
                label="Add Habit"
                @click="openAddDialog"
            />
        </div>

        <!-- Loading indicator -->
        <div v-if="loading" class="text-surface-400 py-12 text-center">
            <i class="pi pi-spin pi-spinner mr-2"></i>Loading habits...
        </div>

        <!-- Habit cards grid -->
        <div
            v-else-if="activeHabits.length > 0"
            class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
        >
            <div
                v-for="habit in activeHabits"
                :key="habit.id"
                class="border-surface-200 dark:border-surface-700 flex overflow-hidden rounded-lg border bg-white shadow-sm dark:bg-slate-800"
            >
                <!-- Color stripe (left border) -->
                <div
                    class="w-1.5 shrink-0"
                    :style="{ backgroundColor: habit.color }"
                ></div>
                <div class="flex-1 p-4">
                    <div class="mb-3 flex items-start justify-between gap-2">
                        <div class="min-w-0 flex-1">
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
                        <!-- Streak badge -->
                        <div
                            v-if="habit.current_streak > 0"
                            class="shrink-0 rounded-full bg-orange-100 px-2 py-0.5 text-xs font-semibold text-orange-600 dark:bg-orange-900/30 dark:text-orange-400"
                        >
                            <i class="pi pi-bolt mr-0.5"></i>{{ habit.current_streak }}
                        </div>
                    </div>

                    <div class="flex items-center justify-between">
                        <div class="text-surface-400 text-xs">
                            Best: {{ habit.longest_streak }} days
                        </div>
                        <div class="flex items-center gap-1">
                            <AppButton
                                icon="pi pi-pencil"
                                rounded
                                severity="info"
                                size="small"
                                text
                                @click="openEditDialog(habit)"
                            />
                            <AppButton
                                icon="pi pi-inbox"
                                rounded
                                severity="secondary"
                                size="small"
                                text
                                title="Archive habit"
                                @click="archiveHabit(habit)"
                            />
                            <AppButton
                                icon="pi pi-trash"
                                rounded
                                severity="danger"
                                size="small"
                                text
                                @click="confirmDelete(habit.id)"
                            />
                            <AppButton
                                :icon="
                                    habit.completed_today
                                        ? 'pi pi-check-circle'
                                        : 'pi pi-circle'
                                "
                                rounded
                                :severity="
                                    habit.completed_today
                                        ? 'success'
                                        : 'secondary'
                                "
                                size="small"
                                @click="toggle(habit)"
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div v-else-if="!loading" class="text-surface-400 py-12 text-center">
            No habits yet. Add one to get started!
        </div>

        <!-- Archived habits section -->
        <div v-if="archivedHabits.length > 0" class="mt-8">
            <div class="mb-3 flex items-center gap-3">
                <h2 class="text-surface-500 text-lg font-semibold">Archived</h2>
                <AppButton
                    :icon="showArchived ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
                    :label="showArchived ? 'Hide' : `Show (${archivedHabits.length})`"
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
                        <div class="mb-2 flex items-center justify-between gap-2">
                            <div class="min-w-0 flex-1">
                                <div class="text-surface-500 truncate font-semibold line-through">
                                    {{ habit.name }}
                                </div>
                                <div
                                    v-if="habit.description"
                                    class="text-surface-400 mt-0.5 truncate text-xs"
                                >
                                    {{ habit.description }}
                                </div>
                            </div>
                            <div class="flex items-center gap-1">
                                <AppButton
                                    icon="pi pi-replay"
                                    rounded
                                    severity="success"
                                    size="small"
                                    text
                                    title="Restore habit"
                                    @click="restoreHabit(habit)"
                                />
                                <AppButton
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
                    <label class="mb-1 block text-sm font-medium">Name</label>
                    <AppInputText v-model="form.name" class="w-full" />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Description
                    </label>
                    <AppTextarea
                        v-model="form.description"
                        class="w-full"
                        rows="2"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Frequency
                    </label>
                    <AppSelect
                        v-model="form.frequency"
                        class="w-full"
                        option-label="label"
                        option-value="value"
                        :options="frequencyOptions"
                    />
                </div>
                <div v-if="form.frequency === 'weekly'">
                    <label class="mb-1 block text-sm font-medium">
                        Days of Week
                    </label>
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
                    <div class="flex items-center gap-3">
                        <input
                            v-model="form.color"
                            class="h-9 w-14 cursor-pointer rounded border-0 p-0.5"
                            type="color"
                        />
                        <span class="text-surface-500 text-sm">{{
                            form.color
                        }}</span>
                    </div>
                </div>
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showDialog = false"
                    />
                    <AppButton label="Save" @click="saveHabit" />
                </div>
            </div>
        </AppDialog>

        <!-- Delete Confirmation -->
        <AppDialog
            v-model:visible="showDeleteConfirm"
            header="Confirm Delete"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <p>Are you sure you want to delete this habit?</p>
            <div class="mt-4 flex justify-end gap-2">
                <AppButton
                    label="Cancel"
                    text
                    @click="showDeleteConfirm = false"
                />
                <AppButton
                    label="Delete"
                    severity="danger"
                    @click="executeDelete"
                />
            </div>
        </AppDialog>
    </div>
</template>
