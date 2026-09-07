<script setup lang="ts">
import { computed, reactive, watch } from 'vue';

import { useTaskApi } from '@/composables/api/useTaskApi';
import { useToast } from '@/composables/useToast';
import type { Task } from '@/types/Task';

const props = withDefaults(
    defineProps<{ task: Task | null; categoryOptions?: string[] }>(),
    { categoryOptions: () => [] },
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
});

const isFormValid = computed(() => form.title.trim() !== '');
const saveTooltip = computed(() =>
    isFormValid.value ? undefined : 'Title is required',
);

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
    } else {
        form.title = '';
        form.description = '';
        form.category = '';
        form.due_date = '';
        form.repeat_type = null;
        form.repeat_interval = 1;
        form.repeat_days = [];
        form.priority = 'medium';
    }
});

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
                <AppInputText
                    v-model="form.due_date"
                    class="w-full"
                    type="date"
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
