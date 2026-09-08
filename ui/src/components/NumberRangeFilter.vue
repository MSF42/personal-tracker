<script setup lang="ts">
// One labeled min/max pair for a numeric filter (distance/pace on the
// Running list) — Min and Max side by side, sized to their small numeric
// content rather than stretching to fill their container.
withDefaults(
    defineProps<{
        label: string;
        unit?: string;
        step?: number;
        maxFractionDigits?: number;
    }>(),
    { unit: '', step: 1, maxFractionDigits: 0 },
);

const minValue = defineModel<number | null>('min', { required: true });
const maxValue = defineModel<number | null>('max', { required: true });
</script>

<template>
    <div>
        <label class="mb-1 block text-sm font-medium">
            {{ label }}<template v-if="unit"> ({{ unit }})</template>
        </label>
        <div class="flex items-center gap-2">
            <div class="w-16 shrink-0">
                <AppInputNumber
                    v-model="minValue"
                    fluid
                    :max-fraction-digits="maxFractionDigits"
                    :min="0"
                    placeholder="Min"
                    :step="step"
                />
            </div>
            <span class="text-surface-400 text-sm">to</span>
            <div class="w-16 shrink-0">
                <AppInputNumber
                    v-model="maxValue"
                    fluid
                    :max-fraction-digits="maxFractionDigits"
                    :min="0"
                    placeholder="Max"
                    :step="step"
                />
            </div>
        </div>
    </div>
</template>
