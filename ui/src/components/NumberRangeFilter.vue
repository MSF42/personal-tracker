<script setup lang="ts">
// One labeled min/max pair for a numeric filter (distance/duration/pace on
// the Running list). Renders two grid cells, so it's meant to sit directly
// inside the same grid as its siblings rather than wrap them.
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
            Min {{ label }}<template v-if="unit"> ({{ unit }})</template>
        </label>
        <AppInputNumber
            v-model="minValue"
            class="w-full"
            :max-fraction-digits="maxFractionDigits"
            :min="0"
            placeholder="Min"
            show-buttons
            :step="step"
        />
    </div>
    <div>
        <label class="mb-1 block text-sm font-medium">
            Max {{ label }}<template v-if="unit"> ({{ unit }})</template>
        </label>
        <AppInputNumber
            v-model="maxValue"
            class="w-full"
            :max-fraction-digits="maxFractionDigits"
            :min="0"
            placeholder="Max"
            show-buttons
            :step="step"
        />
    </div>
</template>
