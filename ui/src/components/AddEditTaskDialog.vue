<script setup lang="ts">
import { computed, reactive, watch } from 'vue';

import { useTaskApi } from '@/composables/api/useTaskApi';
import { useToast } from '@/composables/useToast';
import type { Task, TaskLinkType } from '@/types/Task';
import type { WorkoutRoutine } from '@/types/WorkoutRoutine';
import { fromIsoDate, toIsoDate } from '@/utils/week';

const props = withDefaults(
    defineProps<{
        task: Task | null;
        categoryOptions?: string[];
        routineOptions?: WorkoutRoutine[];
    }>(),
    { categoryOptions: () => [], routineOptions: () => [] },
);
const emit = defineEmits<{ saved: [] }>();
const visible = defineModel<boolean>('visible', { required: true });

const { createTask, updateTask } = useTaskApi();
const toast = useToast();

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const priorityOptions = [
    { label: 'High', value: 'high' },
    { label: 'Medium', value: 'medium' },
    { label: 'Low', value: 'low' },
];

const repeatTypeOptions = [
    { label: 'None', value: null },
    { label: 'Daily', value: 'daily' },
    { label: 'Weekly', value: 'weekly' },
    { label: 'Monthly', value: 'monthly' },
];

const linkTypeOptions = [
    { label: 'None', value: null },
    { label: 'Workout Routine', value: 'workout_routine' },
    { label: 'Run', value: 'run' },
];

const dialogHeader = computed(() => (props.task ? 'Edit Task' : 'Add Task'));

const form = reactive({
    title: '',
    description: '',
    category: '',
    due_date: '',
    repeat_type: null as 'daily' | 'weekly' | 'monthly' | null,
    repeat_interval: 1,
    repeat_days: [] as number[],
    priority: 'medium' as 'high' | 'medium' | 'low',
    link_type: null as TaskLinkType | null,
    link_routine_id: null as number | null,
});
// AppDatePicker binds to a Date; form.due_date stays a plain ISO string.
const dueDateModel = computed<Date | null>({
    get: () => (form.due_date ? fromIsoDate(form.due_date) : null),
    set: (value) => {
        form.due_date = value ? toIsoDate(value) : '';
    },
});

const isFormValid = computed(
    () =>
        form.title.trim() !== '' &&
        (form.link_type !== 'workout_routine' || form.link_routine_id !== null),
);
const saveTooltip = computed(() => {
    if (form.title.trim() === '') return 'Title is required';
    if (form.link_type === 'workout_routine' && form.link_routine_id === null)
        return 'Choose a routine to link to';
    return undefined;
});

// Populate the form whenever the dialog opens: reset for "add", or load the
// task being edited. `editingId` state lives entirely in the parent — this
// dialog is a plain form over the `task` prop.
watch(visible, (isVisible) => {
    if (!isVisible) return;
    const task = props.task;
    if (task) {
        form.title = task.title;
        form.description = task.description ?? '';
        form.category = task.category ?? '';
        form.due_date = task.due_date ?? '';
        form.repeat_type = task.repeat_type as typeof form.repeat_type;
        form.repeat_interval = task.repeat_interval ?? 1;
        form.repeat_days = task.repeat_days ?? [];
        form.priority = task.priority;
        form.link_type = task.link_type;
        form.link_routine_id = task.link_routine_id;
    } else {
        form.title = '';
        form.description = '';
        form.category = '';
        form.due_date = '';
        form.repeat_type = null;
        form.repeat_interval = 1;
        form.repeat_days = [];
        form.priority = 'medium';
        form.link_type = null;
        form.link_routine_id = null;
    }
});

// Selecting a link type other than "Workout Routine" clears any previously
// chosen routine so a stale id never rides along with the wrong type.
watch(
    () => form.link_type,
    (type) => {
        if (type !== 'workout_routine') form.link_routine_id = null;
    },
);

function toggleDay(day: number) {
    const idx = form.repeat_days.indexOf(day);
    if (idx === -1) {
        form.repeat_days.push(day);
        form.repeat_days.sort();
    } else {
        form.repeat_days.splice(idx, 1);
    }
}

async function save() {
    const payload = {
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
        link_type: form.link_type,
        link_routine_id:
            form.link_type === 'workout_routine' ? form.link_routine_id : null,
    };
    const res = props.task
        ? await updateTask(props.task.id, payload)
        : await createTask(payload);
    if (res.success) {
        toast.showSuccess(props.task ? 'Task updated' : 'Task added');
        visible.value = false;
        emit('saved');
    } else {
        toast.showError(res.error?.message ?? 'Failed to save task');
    }
}
</script>

<template>
    <AppDialog
        v-model:visible="visible"
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
                <label class="mb-1 block text-sm font-medium">Category</label>
                <AppSelect
                    v-model="form.category"
                    class="w-full"
                    editable
                    :options="categoryOptions"
                    placeholder="Select or type a category..."
                />
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">Due Date</label>
                <AppDatePicker
                    v-model="dueDateModel"
                    date-format="yy M dd"
                    fluid
                    icon-display="input"
                    show-icon
                />
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">Priority</label>
                <AppSelect
                    v-model="form.priority"
                    class="w-full"
                    option-label="label"
                    option-value="value"
                    :options="priorityOptions"
                />
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">Link To</label>
                <AppSelect
                    v-model="form.link_type"
                    class="w-full"
                    option-label="label"
                    option-value="value"
                    :options="linkTypeOptions"
                />
                <p class="text-surface-400 mt-1 text-xs">
                    Turns this task into a shortcut — click it on the dashboard
                    calendar to jump straight into logging the workout or run it
                    represents.
                </p>
            </div>
            <div v-if="form.link_type === 'workout_routine'">
                <label class="mb-1 block text-sm font-medium"> Routine </label>
                <AppSelect
                    v-model="form.link_routine_id"
                    class="w-full"
                    option-label="name"
                    option-value="id"
                    :options="routineOptions"
                    placeholder="Select a routine..."
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
                <AppButton label="Cancel" text @click="visible = false" />
                <span v-tooltip.top="saveTooltip">
                    <AppButton
                        :disabled="!isFormValid"
                        label="Save"
                        @click="save"
                    />
                </span>
            </div>
        </div>
    </AppDialog>
</template>
