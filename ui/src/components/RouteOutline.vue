<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

import {
    pathFor,
    projectTrack,
    sliceByTime,
    type TimeRange,
    type TrackPoint,
} from '@/utils/route';

const props = defineProps<{
    points: TrackPoint[];
    highlight?: TimeRange | null;
}>();

const container = ref<HTMLElement | null>(null);
const size = ref({ width: 600, height: 240 });
let observer: ResizeObserver | null = null;

onMounted(() => {
    if (!container.value) return;
    const measure = () => {
        const rect = container.value?.getBoundingClientRect();
        if (rect && rect.width > 0 && rect.height > 0) {
            size.value = { width: rect.width, height: rect.height };
        }
    };
    measure();
    observer = new ResizeObserver(measure);
    observer.observe(container.value);
});

onBeforeUnmount(() => observer?.disconnect());

const track = computed(() =>
    projectTrack(props.points, size.value.width, size.value.height, 16),
);

const highlightPath = computed(() => {
    const slice = sliceByTime(props.points, props.highlight);
    return slice.length >= 2 ? pathFor(slice.map(track.value.project)) : '';
});
</script>

<template>
    <div ref="container" class="relative h-full w-full">
        <svg
            class="h-full w-full"
            preserveAspectRatio="none"
            :viewBox="`0 0 ${size.width} ${size.height}`"
        >
            <path
                class="stroke-primary-500"
                :d="track.path"
                fill="none"
                :opacity="highlightPath ? 0.35 : 1"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="3"
            />
            <path
                v-if="highlightPath"
                :d="highlightPath"
                fill="none"
                stroke="#f59e0b"
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="5"
            />
            <circle
                v-if="track.start"
                :cx="track.start.x"
                :cy="track.start.y"
                fill="#22c55e"
                r="5"
            />
            <circle
                v-if="track.end"
                :cx="track.end.x"
                :cy="track.end.y"
                fill="#ef4444"
                r="5"
            />
        </svg>
        <div class="text-surface-500 absolute right-2 bottom-1 text-[10px]">
            Route outline (map tiles unavailable)
        </div>
    </div>
</template>
