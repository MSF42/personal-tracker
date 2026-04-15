<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { useTaskApi } from '@/composables/api/useTaskApi';
import { useLoading } from '@/composables/useLoading';
import { useToast } from '@/composables/useToast';
import type { Task, TaskCreate, TaskUpdate } from '@/types/Task';

const { getTasks, createTask, updateTask, deleteTask } = useTaskApi();
const { loading, withLoading } = useLoading();
const toast = useToast();

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
const editingId = ref<number | null>(null);
const showDeleteConfirm = ref(false);
const deletingId = ref<number | null>(null);

const isFormValid = computed(() => form.title.trim() !== '');
const saveTooltip = computed(() =>
    isFormValid.value ? undefined : 'Title is required',
);

const form = reactive({
    title: '',
    description: '',
    category: '',
    due_date: '',
    repeat_type: null as 'daily' | 'weekly' | 'monthly' | null,
    repeat_interval: 1,
    repeat_days: [] as number[],
    priority: 'medium' as 'high' | 'medium' | 'low',
});

function resetForm() {
    form.title = '';
    form.description = '';
    form.category = '';
    form.due_date = '';
    form.repeat_type = null;
    form.repeat_interval = 1;
    form.repeat_days = [];
    form.priority = 'medium';
    editingId.value = null;
}

function openAddDialog() {
    resetForm();
    showDialog.value = true;
}

function openEditDialog(task: Task) {
    editingId.value = task.id;
    form.title = task.title;
    form.description = task.description ?? '';
    form.category = task.category ?? '';
    form.due_date = task.due_date ?? '';
    form.repeat_type = task.repeat_type as typeof form.repeat_type;
    form.repeat_interval = task.repeat_interval ?? 1;
    form.repeat_days = task.repeat_days ?? [];
    form.priority = task.priority;
    showDialog.value = true;
}

async function saveTask() {
    if (editingId.value) {
        const payload: TaskUpdate = {
            title: form.title,
            description: form.description || null,
            category: form.category || null,
            due_date: form.due_date || null,
            repeat_type: form.repeat_type,
            repeat_interval: form.repeat_type ? form.repeat_interval : null,
            repeat_days:
                form.repeat_type === 'weekly' && form.repeat_days.length
                    ? form.repeat_days
                    : null,
            priority: form.priority,
        };
        const res = await updateTask(editingId.value, payload);
        if (res.success) {
            toast.showSuccess('Task updated');
            showDialog.value = false;
            await loadData();
        } else {
            toast.showError(res.error?.message ?? 'Failed to save task');
        }
    } else {
        const payload: TaskCreate = {
            title: form.title,
            description: form.description || null,
            category: form.category || null,
            due_date: form.due_date || null,
            repeat_type: form.repeat_type,
            repeat_interval: form.repeat_type ? form.repeat_interval : null,
            repeat_days:
                form.repeat_type === 'weekly' && form.repeat_days.length
                    ? form.repeat_days
                    : null,
            priority: form.priority,
        };
        const res = await createTask(payload);
        if (res.success) {
            toast.showSuccess('Task added');
            showDialog.value = false;
            await loadData();
        } else {
            toast.showError(res.error?.message ?? 'Failed to save task');
        }
    }
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
});

// --- Helpers ---
function isOverdue(task: Task): boolean {
    return !task.completed && !!task.due_date && task.due_date < todayStr;
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function toggleDay(day: number) {
    const idx = form.repeat_days.indexOf(day);
    if (idx === -1) {
        form.repeat_days.push(day);
        form.repeat_days.sort();
    } else {
        form.repeat_days.splice(idx, 1);
    }
}

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

const repeatTypeOptions = [
    { label: 'None', value: null },
    { label: 'Daily', value: 'daily' },
    { label: 'Weekly', value: 'weekly' },
    { label: 'Monthly', value: 'monthly' },
];

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

const dialogHeader = computed(() =>
    editingId.value ? 'Edit Task' : 'Add Task',
);
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
                    isOverdue(data) ? 'bg-red-50 dark:!bg-red-950/20' : ''
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
                        {{ (data as Task).due_date }}
                    </span>
                    <span v-else class="text-surface-400">&mdash;</span>
                </template>
            </AppColumn>
            <AppColumn header="Repeat">
                <template #body="{ data }">
                    {{ formatRepeat(data as Task) }}
                </template>
            </AppColumn>
            <AppColumn header="Actions" style="width: 8rem">
                <template #body="{ data }">
                    <div class="row-actions flex gap-2">
                        <AppButton
                            icon="pi pi-pencil"
                            rounded
                            severity="info"
                            text
                            @click="openEditDialog(data as Task)"
                        />
                        <AppButton
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
        <AppDialog
            v-model:visible="showDialog"
            :header="dialogHeader"
            modal
            :style="{ width: '28rem', maxWidth: '92vw' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Title <span class="text-red-500">*</span>
                    </label>
                    <AppInputText v-model="form.title" class="w-full" />
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
                        Category
                    </label>
                    <AppSelect
                        v-model="form.category"
                        class="w-full"
                        editable
                        :options="categoryOptions"
                        placeholder="Select or type a category..."
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Due Date
                    </label>
                    <AppInputText
                        v-model="form.due_date"
                        class="w-full"
                        type="date"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Priority
                    </label>
                    <AppSelect
                        v-model="form.priority"
                        class="w-full"
                        option-label="label"
                        option-value="value"
                        :options="priorityOptions"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Repeat Type
                    </label>
                    <AppSelect
                        v-model="form.repeat_type"
                        class="w-full"
                        option-label="label"
                        option-value="value"
                        :options="repeatTypeOptions"
                    />
                </div>
                <div v-if="form.repeat_type">
                    <label class="mb-1 block text-sm font-medium">
                        Repeat Interval
                    </label>
                    <AppInputNumber
                        v-model="form.repeat_interval"
                        class="w-full"
                        :min="1"
                        show-buttons
                    />
                </div>
                <div v-if="form.repeat_type === 'weekly'">
                    <label class="mb-1 block text-sm font-medium">
                        Days of Week
                        <span class="text-surface-400 font-normal">
                            (optional)
                        </span>
                    </label>
                    <div class="flex gap-1">
                        <AppButton
                            v-for="(label, idx) in DAY_LABELS"
                            :key="idx"
                            :label="label"
                            :outlined="!form.repeat_days.includes(idx)"
                            :severity="
                                form.repeat_days.includes(idx)
                                    ? 'primary'
                                    : 'secondary'
                            "
                            size="small"
                            @click="toggleDay(idx)"
                        />
                    </div>
                    <p class="text-surface-400 mt-1 text-xs">
                        If no days selected, advances by interval weeks
                    </p>
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
                            @click="saveTask"
                        />
                    </span>
                </div>
            </div>
        </AppDialog>

        <!-- Delete Confirmation Dialog -->
        <AppDialog
            v-model:visible="showDeleteConfirm"
            header="Confirm Delete"
            modal
            :style="{ width: '24rem', maxWidth: '92vw' }"
        >
            <p>Are you sure you want to delete this task?</p>
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
