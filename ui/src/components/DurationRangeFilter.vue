<script setup lang="ts">
// One labeled min/max pair for the Duration filter on the Running list,
// entered/displayed as "H:MM:SS" (or "M:SS" under an hour) rather than a
// plain number of minutes — matching how duration is shown everywhere else.
import { ref, watch } from 'vue';

import { formatDuration, parseDuration } from '@/utils/format';

const minSeconds = defineModel<number | null>('min', { required: true });
const maxSeconds = defineModel<number | null>('max', { required: true });

// A separate, freely-editable text buffer per box — reformatting on every
// keystroke (if bound straight to a get/set computed) would fight the user
// mid-type, so parsing only happens on blur/Enter, and the display only
// resyncs from the model when it changes some other way (seeding, Clear
// Filters).
const minText = ref('');
const maxText = ref('');

watch(
    minSeconds,
    (v) => {
        minText.value = v != null ? formatDuration(v) : '';
    },
    { immediate: true },
);
watch(
    maxSeconds,
    (v) => {
        maxText.value = v != null ? formatDuration(v) : '';
    },
    { immediate: true },
);

function commitMin() {
    minSeconds.value = parseDuration(minText.value);
    minText.value =
        minSeconds.value != null ? formatDuration(minSeconds.value) : '';
}
function commitMax() {
    maxSeconds.value = parseDuration(maxText.value);
    maxText.value =
        maxSeconds.value != null ? formatDuration(maxSeconds.value) : '';
}
</script>

<template>
    <div>
        <label class="mb-1 block text-sm font-medium">Duration</label>
        <div class="flex items-center gap-2">
            <div class="w-20 shrink-0">
                <AppInputText
                    v-model="minText"
                    class="w-full"
                    placeholder="Min"
                    @blur="commitMin"
                    @keydown.enter="commitMin"
                />
            </div>
            <span class="text-surface-400 text-sm">to</span>
            <div class="w-20 shrink-0">
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
