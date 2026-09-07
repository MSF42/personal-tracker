<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import AddEditRunDialog from '@/components/AddEditRunDialog.vue';
import AddEditTaskDialog from '@/components/AddEditTaskDialog.vue';
import ConfirmDeleteDialog from '@/components/ConfirmDeleteDialog.vue';
import LogWorkoutDialog from '@/components/LogWorkoutDialog.vue';
import { useTaskApi } from '@/composables/api/useTaskApi';
import { useLoading } from '@/composables/useLoading';
import { useTaskLinks } from '@/composables/useTaskLinks';
import { useToast } from '@/composables/useToast';
import type { Task } from '@/types/Task';
import { formatDate } from '@/utils/format';

const { getTasks, updateTask, deleteTask } = useTaskApi();
const { loading, withLoading } = useLoading();
const toast = useToast();

const {
    routines,
    loadRoutines,
    showLogWorkoutDialog,
    activeRoutineId,
    activeRoutineName,
    activeResumeLogId,
    showRunDialog,
    runDefaultDate,
    openLinkedWorkout,
    openLinkedRun,
    onWorkoutLogged,
    onRunSaved,
} = useTaskLinks(loadData);

const tasks = ref<Task[]>([]);
const todayStr = new Date().toISOString().split('T')[0] as string;

// --- Filters ---
const showCompleted = ref(false);
const selectedCategory = ref('');
const selectedPriority = ref('');

const PRIORITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

const filteredTasks = computed(() => {
    return tasks.value
        .filter((t) => {
            if (!showCompleted.value && t.completed) return false;
            if (selectedCategory.value && t.category !== selectedCategory.value)
                return false;
            if (selectedPriority.value && t.priority !== selectedPriority.value)
                return false;
            return true;
        })
        .sort(
            (a, b) =>
                (PRIORITY_ORDER[a.priority] ?? 1) -
                (PRIORITY_ORDER[b.priority] ?? 1),
        );
});

// --- Stats ---
const stats = computed(() => {
    const incomplete = tasks.value.filter((t) => !t.completed).length;
    const overdue = tasks.value.filter(
        (t) => !t.completed && t.due_date && t.due_date < todayStr,
    ).length;
    const completedToday = tasks.value.filter(
        (t) => t.completed && t.updated_at.startsWith(todayStr),
    ).length;
    return { incomplete, overdue, completedToday };
});

// --- Dialog state ---
const showDialog = ref(false);
const editingTask = ref<Task | null>(null);
const showDeleteConfirm = ref(false);
const deletingId = ref<number | null>(null);

function openAddDialog() {
    editingTask.value = null;
    showDialog.value = true;
}

function openEditDialog(task: Task) {
    editingTask.value = task;
    showDialog.value = true;
}

function enterLinkedTask(task: Task) {
    if (task.link_type === 'workout_routine') void openLinkedWorkout(task);
    else if (task.link_type === 'run') openLinkedRun(task);
}

async function toggleCompleted(task: Task) {
    const res = await updateTask(task.id, { completed: !task.completed });
    if (res.success) {
        await loadData();
    }
}

function confirmDelete(id: number) {
    deletingId.value = id;
    showDeleteConfirm.value = true;
}

async function executeDelete() {
    if (deletingId.value) {
        const res = await deleteTask(deletingId.value);
        if (res.success) {
            toast.showSuccess('Task deleted');
        }
    }
    showDeleteConfirm.value = false;
    deletingId.value = null;
    await loadData();
}

// --- Data loading ---
async function loadData() {
    const res = await getTasks();
    if (res.success && res.data) tasks.value = res.data;
    else if (!res.success) toast.showError('Failed to load tasks');
}

onMounted(() => {
    withLoading(loadData);
    void loadRoutines();
});

// --- Helpers ---
function isOverdue(task: Task): boolean {
    return !task.completed && !!task.due_date && task.due_date < todayStr;
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function formatRepeat(task: Task): string {
    if (!task.repeat_type) return '\u2014';
    const interval = task.repeat_interval ?? 1;
    const base =
        interval === 1
            ? task.repeat_type.charAt(0).toUpperCase() +
              task.repeat_type.slice(1)
            : `Every ${interval} ${task.repeat_type.replace(/ly$/, '')}${interval > 1 ? 's' : ''}`;
    if (task.repeat_type === 'weekly' && task.repeat_days?.length) {
        const days = task.repeat_days.map((d) => DAY_LABELS[d]).join(', ');
        return `${base}: ${days}`;
    }
    return base;
}

const priorityOptions = [
    { label: 'High', value: 'high' },
    { label: 'Medium', value: 'medium' },
    { label: 'Low', value: 'low' },
];

const filterPriorityOptions = [
    { label: 'All priorities', value: '' },
    ...priorityOptions,
];

const PRIORITY_DOT: Record<string, string> = {
    high: 'bg-red-500',
    medium: 'bg-yellow-400',
    low: 'bg-gray-300',
};

const categoryOptions = computed(() => {
    const cats = new Set(
        tasks.value.map((t) => t.category).filter(Boolean) as string[],
    );
    return [...cats].sort();
});

const filterCategoryOptions = computed(() => [
    { label: 'All categories', value: '' },
    ...categoryOptions.value.map((c) => ({ label: c, value: c })),
]);
</script>

<template>
    <div class="mx-auto max-w-6xl p-6">
        <h1 class="mb-6 text-2xl font-bold">Tasks</h1>

        <!-- Stats Cards -->
        <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <AppCard>
                <template #title>Incomplete</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ stats.incomplete }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{ stats.incomplete === 1 ? 'task' : 'tasks' }}
                        remaining
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>Overdue</template>
                <template #content>
                    <div class="text-2xl font-bold text-red-500">
                        {{ stats.overdue }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{ stats.overdue === 1 ? 'task' : 'tasks' }} past due
                    </div>
                </template>
            </AppCard>

            <AppCard>
                <template #title>Completed Today</template>
                <template #content>
                    <div class="text-2xl font-bold">
                        {{ stats.completedToday }}
                    </div>
                    <div class="text-surface-500 text-sm">
                        {{ stats.completedToday === 1 ? 'task' : 'tasks' }}
                        done today
                    </div>
                </template>
            </AppCard>
        </div>

        <!-- Table Header -->
        <div class="mb-4 flex items-center justify-between">
            <div class="flex items-center gap-4">
                <h2 class="text-xl font-semibold">Task List</h2>
                <AppSelect
                    v-model="selectedCategory"
                    class="min-w-44"
                    option-label="label"
                    option-value="value"
                    :options="filterCategoryOptions"
                    size="small"
                />
                <AppSelect
                    v-model="selectedPriority"
                    class="min-w-40"
                    option-label="label"
                    option-value="value"
                    :options="filterPriorityOptions"
                    size="small"
                />
                <label
                    class="text-surface-600 dark:text-surface-400 flex cursor-pointer items-center gap-2 text-sm"
                >
                    <AppToggleSwitch v-model="showCompleted" />
                    Show completed
                </label>
            </div>
            <AppButton
                icon="pi pi-plus"
                label="Add Task"
                @click="openAddDialog"
            />
        </div>

        <!-- Data Table -->
        <AppDataTable
            :loading="loading"
            :row-class="
                (data: Task) =>
                    isOverdue(data)
                        ? 'group bg-red-50 dark:!bg-red-950/20'
                        : 'group'
            "
            sort-field="due_date"
            :sort-order="1"
            striped-rows
            :value="filteredTasks"
        >
            <template #empty>
                <div class="flex flex-col items-center py-10 text-center">
                    <i
                        class="pi pi-inbox text-surface-300 dark:text-surface-600 mb-3 text-4xl"
                    ></i>
                    <p class="text-surface-500 mb-3">No tasks found</p>
                    <AppButton
                        icon="pi pi-plus"
                        label="Add your first task"
                        size="small"
                        @click="openAddDialog"
                    />
                </div>
            </template>
            <AppColumn header="Done" style="width: 4rem">
                <template #body="{ data }">
                    <AppButton
                        :aria-label="
                            (data as Task).completed
                                ? 'Mark incomplete'
                                : 'Mark complete'
                        "
                        :icon="
                            (data as Task).completed
                                ? 'pi pi-check-square'
                                : 'pi pi-stop'
                        "
                        rounded
                        :severity="
                            (data as Task).completed ? 'success' : 'secondary'
                        "
                        text
                        @click="toggleCompleted(data as Task)"
                    />
                </template>
            </AppColumn>
            <AppColumn header="" style="width: 2rem">
                <template #body="{ data }">
                    <span
                        class="inline-block h-2.5 w-2.5 rounded-full"
                        :class="
                            PRIORITY_DOT[(data as Task).priority] ??
                            'bg-gray-300'
                        "
                        :title="(data as Task).priority"
                    ></span>
                </template>
            </AppColumn>
            <AppColumn field="title" header="Title" sortable />
            <AppColumn field="category" header="Category" sortable>
                <template #body="{ data }">
                    <AppTag
                        v-if="(data as Task).category"
                        :value="(data as Task).category!"
                    />
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn field="due_date" header="Due Date" sortable>
                <template #body="{ data }">
                    <span
                        v-if="(data as Task).due_date"
                        :class="{
                            'font-semibold text-red-500': isOverdue(
                                data as Task,
                            ),
                        }"
                    >
                        {{ formatDate((data as Task).due_date!) }}
                    </span>
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn header="Repeat">
                <template #body="{ data }">
                    {{ formatRepeat(data as Task) }}
                </template>
            </AppColumn>
            <AppColumn header="Actions" style="width: 10rem">
                <template #body="{ data }">
                    <div
                        class="flex gap-2 opacity-20 transition-opacity group-hover:opacity-100"
                    >
                        <AppButton
                            v-if="(data as Task).link_type"
                            aria-label="Enter"
                            icon="pi pi-play"
                            rounded
                            severity="success"
                            text
                            title="Enter"
                            @click="enterLinkedTask(data as Task)"
                        />
                        <AppButton
                            aria-label="Edit task"
                            icon="pi pi-pencil"
                            rounded
                            severity="info"
                            text
                            @click="openEditDialog(data as Task)"
                        />
                        <AppButton
                            aria-label="Delete task"
                            icon="pi pi-trash"
                            rounded
                            severity="danger"
                            text
                            @click="confirmDelete((data as Task).id)"
                        />
                    </div>
                </template>
            </AppColumn>
        </AppDataTable>

        <!-- Add/Edit Dialog -->
        <AddEditTaskDialog
            v-model:visible="showDialog"
            :category-options="categoryOptions"
            :routine-options="routines"
            :task="editingTask"
            @saved="loadData"
        />

        <!-- Delete Confirmation Dialog -->
        <ConfirmDeleteDialog
            v-model:visible="showDeleteConfirm"
            @confirm="executeDelete"
        >
            Are you sure you want to delete this task?
        </ConfirmDeleteDialog>

        <!-- Enter a linked task: workout or run -->
        <LogWorkoutDialog
            v-model:visible="showLogWorkoutDialog"
            :resume-log-id="activeResumeLogId"
            :routine-id="activeRoutineId"
            :routine-name="activeRoutineName"
            @logged="onWorkoutLogged"
        />
        <AddEditRunDialog
            v-model:visible="showRunDialog"
            :default-date="runDefaultDate"
            :run="null"
            @saved="onRunSaved"
        />
    </div>
</template>
