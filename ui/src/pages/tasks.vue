<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';

import { useTaskApi } from '@/composables/api/useTaskApi';
import { useToast } from '@/composables/useToast';
import type { Task, TaskCreate, TaskUpdate } from '@/types/Task';

const { getTasks, createTask, updateTask, deleteTask } = useTaskApi();
const toast = useToast();

const tasks = ref<Task[]>([]);
const todayStr = new Date().toISOString().split('T')[0] as string;

// --- Filters ---
const showFilters = ref(false);
const filters = reactive({
    status: 'all' as 'all' | 'incomplete' | 'completed',
    category: '',
    dateFrom: '',
    dateTo: '',
});

const hasActiveFilters = computed(() =>
    Boolean(
        filters.status !== 'all' ||
        filters.category ||
        filters.dateFrom ||
        filters.dateTo,
    ),
);

function clearFilters() {
    filters.status = 'all';
    filters.category = '';
    filters.dateFrom = '';
    filters.dateTo = '';
}

const filteredTasks = computed(() => {
    return tasks.value.filter((t) => {
        if (filters.status === 'incomplete' && t.completed) return false;
        if (filters.status === 'completed' && !t.completed) return false;
        if (
            filters.category &&
            (!t.category ||
                !t.category
                    .toLowerCase()
                    .includes(filters.category.toLowerCase()))
        )
            return false;
        if (filters.dateFrom && (!t.due_date || t.due_date < filters.dateFrom))
            return false;
        if (filters.dateTo && (!t.due_date || t.due_date > filters.dateTo))
            return false;
        return true;
    });
});

// --- Stats ---
const stats = computed(() => {
    const incomplete = filteredTasks.value.filter((t) => !t.completed).length;
    const overdue = filteredTasks.value.filter(
        (t) => !t.completed && t.due_date && t.due_date < todayStr,
    ).length;
    const completedToday = filteredTasks.value.filter(
        (t) => t.completed && t.updated_at.startsWith(todayStr),
    ).length;
    return { incomplete, overdue, completedToday };
});

// --- Dialog state ---
const showDialog = ref(false);
const editingId = ref<number | null>(null);
const showDeleteConfirm = ref(false);
const deletingId = ref<number | null>(null);

const form = reactive({
    title: '',
    description: '',
    category: '',
    due_date: '',
    repeat_type: null as 'daily' | 'weekly' | 'monthly' | null,
    repeat_interval: 1,
});

function resetForm() {
    form.title = '';
    form.description = '';
    form.category = '';
    form.due_date = '';
    form.repeat_type = null;
    form.repeat_interval = 1;
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
        };
        const res = await updateTask(editingId.value, payload);
        if (res.success) {
            toast.showSuccess('Task updated');
        }
    } else {
        const payload: TaskCreate = {
            title: form.title,
            description: form.description || null,
            category: form.category || null,
            due_date: form.due_date || null,
            repeat_type: form.repeat_type,
            repeat_interval: form.repeat_type ? form.repeat_interval : null,
        };
        const res = await createTask(payload);
        if (res.success) {
            toast.showSuccess('Task added');
        }
    }
    showDialog.value = false;
    await loadData();
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
}

onMounted(loadData);

// --- Helpers ---
function isOverdue(task: Task): boolean {
    return !task.completed && !!task.due_date && task.due_date < todayStr;
}

function formatRepeat(task: Task): string {
    if (!task.repeat_type) return '\u2014';
    const interval = task.repeat_interval ?? 1;
    return `Every ${interval} ${task.repeat_type.replace(/ly$/, '')}${interval > 1 ? 's' : ''}`;
}

const statusOptions = [
    { label: 'All', value: 'all' },
    { label: 'Incomplete', value: 'incomplete' },
    { label: 'Completed', value: 'completed' },
];

const repeatTypeOptions = [
    { label: 'None', value: null },
    { label: 'Daily', value: 'daily' },
    { label: 'Weekly', value: 'weekly' },
    { label: 'Monthly', value: 'monthly' },
];

const categoryOptions = computed(() => {
    const cats = new Set(
        tasks.value.map((t) => t.category).filter(Boolean) as string[],
    );
    return [...cats].sort();
});

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
            <h2 class="text-xl font-semibold">Task List</h2>
            <div class="flex gap-2">
                <AppButton
                    :icon="showFilters ? 'pi pi-filter-slash' : 'pi pi-filter'"
                    :label="showFilters ? 'Hide Filters' : 'Filters'"
                    outlined
                    :severity="hasActiveFilters ? 'warn' : 'secondary'"
                    @click="showFilters = !showFilters"
                />
                <AppButton
                    icon="pi pi-plus"
                    label="Add Task"
                    @click="openAddDialog"
                />
            </div>
        </div>

        <!-- Filters Panel -->
        <div
            v-if="showFilters"
            class="border-surface-200 dark:border-surface-700 mb-4 rounded-lg border p-4"
        >
            <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Status
                    </label>
                    <AppSelect
                        v-model="filters.status"
                        class="w-full"
                        option-label="label"
                        option-value="value"
                        :options="statusOptions"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Category
                    </label>
                    <AppInputText
                        v-model="filters.category"
                        class="w-full"
                        placeholder="Search category..."
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Due Date From
                    </label>
                    <AppInputText
                        v-model="filters.dateFrom"
                        class="w-full"
                        type="date"
                    />
                </div>
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Due Date To
                    </label>
                    <AppInputText
                        v-model="filters.dateTo"
                        class="w-full"
                        type="date"
                    />
                </div>
            </div>
            <div class="mt-3 flex items-center justify-between">
                <span class="text-surface-500 text-sm">
                    {{ filteredTasks.length }} of {{ tasks.length }} tasks
                </span>
                <AppButton
                    v-if="hasActiveFilters"
                    icon="pi pi-times"
                    label="Clear Filters"
                    severity="secondary"
                    size="small"
                    text
                    @click="clearFilters"
                />
            </div>
        </div>

        <!-- Data Table -->
        <AppDataTable
            sort-field="due_date"
            :sort-order="1"
            striped-rows
            :value="filteredTasks"
        >
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
            :style="{ width: '28rem' }"
        >
            <div class="flex flex-col gap-4">
                <div>
                    <label class="mb-1 block text-sm font-medium">
                        Title
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
                <div class="flex justify-end gap-2">
                    <AppButton
                        label="Cancel"
                        text
                        @click="showDialog = false"
                    />
                    <AppButton label="Save" @click="saveTask" />
                </div>
            </div>
        </AppDialog>

        <!-- Delete Confirmation Dialog -->
        <AppDialog
            v-model:visible="showDeleteConfirm"
            header="Confirm Delete"
            modal
            :style="{ width: '24rem' }"
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
