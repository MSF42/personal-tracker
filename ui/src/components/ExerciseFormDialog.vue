<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue';

import { useExerciseApi } from '@/composables/api/useExerciseApi';
import { useToast } from '@/composables/useToast';
import type {
    Exercise,
    ExerciseCreate,
    ExerciseUpdate,
} from '@/types/Exercise';

const props = defineProps<{
    visible: boolean;
    // Exercise being edited; null/omitted opens the dialog in "add" mode.
    exercise?: Exercise | null;
    // Pre-fills the name in "add" mode (e.g. the text typed into a picker).
    initialName?: string;
}>();

const emit = defineEmits<{
    'update:visible': [value: boolean];
    saved: [exercise: Exercise];
}>();

const { createExercise, updateExercise } = useExerciseApi();
const toast = useToast();

const MUSCLE_GROUP_OPTIONS = [
    { label: 'Back', value: 'back' },
    { label: 'Chest', value: 'chest' },
    { label: 'Biceps', value: 'biceps' },
    { label: 'Triceps', value: 'triceps' },
    { label: 'Shoulders', value: 'shoulders' },
    { label: 'Legs', value: 'legs' },
    { label: 'Core', value: 'core' },
];

const EQUIPMENT_OPTIONS = [
    'Barbell',
    'Dumbbell',
    'Kettlebell',
    'Machine',
    'Cable',
    'Resistance Band',
    'Bodyweight',
    'Other',
];

const form = reactive({
    name: '',
    muscle_group: '',
    equipment: '',
    description: '',
    instructions: '',
});
const formError = ref('');

// Re-seed the form each time the dialog opens.
watch(
    () => props.visible,
    (visible) => {
        if (!visible) return;
        const ex = props.exercise;
        form.name = ex?.name ?? props.initialName?.trim() ?? '';
        form.muscle_group = ex?.muscle_group ?? '';
        form.equipment = ex?.equipment ?? '';
        form.description = ex?.description ?? '';
        form.instructions = ex?.instructions ?? '';
        formError.value = '';
    },
    { immediate: true },
);

const isFormValid = computed(
    () =>
        form.name.trim().length >= 3 &&
        form.name.trim().length <= 50 &&
        form.muscle_group !== '',
);
const saveTooltip = computed(() => {
    if (form.name.trim().length < 3)
        return 'Name must be at least 3 characters';
    if (form.name.trim().length > 50)
        return 'Name must be 50 characters or fewer';
    if (form.muscle_group === '') return 'Muscle group is required';
    return undefined;
});

const dialogHeader = computed(() =>
    props.exercise ? 'Edit Exercise' : 'Add Exercise',
);

async function saveExercise() {
    formError.value = '';
    const payload: ExerciseCreate & ExerciseUpdate = {
        name: form.name,
        muscle_group: form.muscle_group,
        equipment: form.equipment || null,
        description: form.description || null,
        instructions: form.instructions || null,
    };
    const res = props.exercise
        ? await updateExercise(props.exercise.id, payload)
        : await createExercise(payload);
    if (res.success && res.data) {
        toast.showSuccess(
            props.exercise ? 'Exercise updated' : 'Exercise added',
        );
        emit('update:visible', false);
        emit('saved', res.data);
    } else {
        formError.value = res.error?.message ?? 'Something went wrong';
    }
}
</script>

<template>
    <AppDialog
        :header="dialogHeader"
        modal
        :style="{ width: '28rem', maxWidth: '92vw' }"
        :visible="visible"
        @update:visible="emit('update:visible', $event)"
    >
        <div class="flex flex-col gap-4">
            <div>
                <label class="mb-1 block text-sm font-medium">
                    Name <span class="text-red-500">*</span>
                </label>
                <AppInputText
                    v-model="form.name"
                    class="w-full"
                    maxlength="50"
                />
                <p v-if="formError" class="mt-1 text-sm text-red-500">
                    {{ formError }}
                </p>
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">
                    Muscle Group <span class="text-red-500">*</span>
                </label>
                <AppSelect
                    v-model="form.muscle_group"
                    class="w-full"
                    option-label="label"
                    option-value="value"
                    :options="MUSCLE_GROUP_OPTIONS"
                    placeholder="Select a muscle group"
                />
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium">Equipment</label>
                <AppSelect
                    v-model="form.equipment"
                    class="w-full"
                    editable
                    :options="EQUIPMENT_OPTIONS"
                    placeholder="Select or type equipment"
                />
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
                    Instructions
                </label>
                <AppTextarea
                    v-model="form.instructions"
                    class="w-full"
                    rows="3"
                />
            </div>
            <div class="flex justify-end gap-2">
                <AppButton
                    label="Cancel"
                    text
                    @click="emit('update:visible', false)"
                />
                <span v-tooltip.top="saveTooltip">
                    <AppButton
                        :disabled="!isFormValid"
                        label="Save"
                        @click="saveExercise"
                    />
                </span>
            </div>
        </div>
    </AppDialog>
</template>
