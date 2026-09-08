<script setup lang="ts">
// One labeled min/max pair for the Pace filter on the Running list, entered
// and displayed as "M:SS" — matching how pace is shown everywhere else —
// rather than decimal minutes. The model stays decimal minutes (what the
// rest of the page's filtering already expects); this just reuses
// formatDuration/parseDuration via a minutes<->seconds conversion, since
// pace never runs long enough to need an hours component.
import { ref, watch } from 'vue';

import { formatDuration, parseDuration } from '@/utils/format';

defineProps<{ unit: string }>();

const minPace = defineModel<number | null>('min', { required: true });
const maxPace = defineModel<number | null>('max', { required: true });

function toText(paceMinutes: number): string {
    return formatDuration(paceMinutes * 60);
}
function toMinutes(text: string): number | null {
    const seconds = parseDuration(text);
    return seconds != null ? seconds / 60 : null;
}

const minText = ref('');
const maxText = ref('');

watch(
    minPace,
    (v) => {
        minText.value = v != null ? toText(v) : '';
    },
    { immediate: true },
);
watch(
    maxPace,
    (v) => {
        maxText.value = v != null ? toText(v) : '';
    },
    { immediate: true },
);

function commitMin() {
    minPace.value = toMinutes(minText.value);
    minText.value = minPace.value != null ? toText(minPace.value) : '';
}
function commitMax() {
    maxPace.value = toMinutes(maxText.value);
    maxText.value = maxPace.value != null ? toText(maxPace.value) : '';
}
</script>

<template>
    <div>
        <label class="mb-1 block text-sm font-medium">Pace ({{ unit }})</label>
        <div class="flex items-center gap-2">
            <div class="w-16 shrink-0">
                <AppInputText
                    v-model="minText"
                    class="w-full"
                    placeholder="Min"
                    @blur="commitMin"
                    @keydown.enter="commitMin"
                />
            </div>
            <span class="text-surface-400 text-sm">to</span>
            <div class="w-16 shrink-0">
                <AppInputText
                    v-model="maxText"
                    class="w-full"
                    placeholder="Max"
                    @blur="commitMax"
                    @keydown.enter="commitMax"
                />
            </div>
        </div>
    </div>
</template>
