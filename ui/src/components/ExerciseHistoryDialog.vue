<script setup lang="ts">
import {
    CategoryScale,
    Chart,
    Filler,
    Legend,
    LinearScale,
    LineController,
    LineElement,
    PointElement,
    Title,
    Tooltip,
} from 'chart.js';
import { computed, ref } from 'vue';

import type { ExerciseHistoryEntry } from '@/types/WorkoutLog';

const props = defineProps<{
    exerciseName: string;
    entries: ExerciseHistoryEntry[];
}>();

Chart.register(
    CategoryScale,
    Filler,
    Legend,
    LinearScale,
    LineController,
    LineElement,
    PointElement,
    Title,
    Tooltip,
);

const visible = defineModel<boolean>('visible', { required: true });

interface HistoryDateGroup {
    date: string;
    routineName: string;
    sets: ExerciseHistoryEntry[];
}

const expandedDates = ref<Record<string, boolean>>({});

function toggleDate(date: string) {
    expandedDates.value[date] = !expandedDates.value[date];
}

const historyByDate = computed<HistoryDateGroup[]>(() => {
    const groups: HistoryDateGroup[] = [];
    for (const entry of props.entries) {
        let group = groups.find((g) => g.date === entry.date);
        if (!group) {
            group = {
                date: entry.date,
                routineName: entry.routine_name,
                sets: [],
            };
            groups.push(group);
        }
        group.sets.push(entry);
    }
    return groups;
});

const hasWeightData = computed(() =>
    props.entries.some((e) => e.weight !== null && e.weight > 0),
);

const summaryStats = computed(() => {
    const groups = historyByDate.value;
    const sessions = groups.length;

    let prWeight = 0;
    let bestVolume = 0;
    let totalVolume = 0;

    for (const group of groups) {
        let sessionVolume = 0;
        for (const set of group.sets) {
            const w = set.weight ?? 0;
            if (w > prWeight) prWeight = w;
            sessionVolume += set.reps * w;
        }
        if (sessionVolume > bestVolume) bestVolume = sessionVolume;
        totalVolume += sessionVolume;
    }

    const avgVolume = sessions > 0 ? Math.round(totalVolume / sessions) : 0;

    return { sessions, prWeight, bestVolume, avgVolume };
});

const chartData = computed(() => {
    const groups = [...historyByDate.value].reverse();
    const labels = groups.map((g) => g.date);

    if (!hasWeightData.value) {
        const totalReps = groups.map((g) =>
            g.sets.reduce((sum, s) => sum + s.reps, 0),
        );
        return {
            labels,
            datasets: [
                {
                    label: 'Total Reps',
                    data: totalReps,
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    fill: true,
                    tension: 0.3,
                },
            ],
        };
    }

    const maxWeight = groups.map((g) =>
        Math.max(...g.sets.map((s) => s.weight ?? 0)),
    );
    const volume = groups.map((g) =>
        g.sets.reduce((sum, s) => sum + s.reps * (s.weight ?? 0), 0),
    );

    return {
        labels,
        datasets: [
            {
                label: 'Max Weight (lbs)',
                data: maxWeight,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                fill: false,
                tension: 0.3,
                yAxisID: 'y',
            },
            {
                label: 'Total Volume (lbs)',
                data: volume,
                borderColor: '#22c55e',
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                fill: true,
                tension: 0.3,
                yAxisID: 'y1',
            },
        ],
    };
});

const chartOptions = computed(() => {
    if (!hasWeightData.value) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: true } },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Reps' },
                },
            },
        };
    }

    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: true } },
        scales: {
            y: {
                type: 'linear' as const,
                position: 'left' as const,
                beginAtZero: true,
                title: { display: true, text: 'Weight (lbs)' },
            },
            y1: {
                type: 'linear' as const,
                position: 'right' as const,
                beginAtZero: true,
                title: { display: true, text: 'Volume (lbs)' },
                grid: { drawOnChartArea: false },
            },
        },
    };
});
</script>

<template>
    <AppDialog
        v-model:visible="visible"
        :header="`${exerciseName} History`"
        modal
        :style="{ width: '52rem' }"
    >
        <div class="flex flex-col gap-4">
            <div
                v-if="historyByDate.length === 0"
                class="text-surface-500 text-center text-sm"
            >
                No history found for this exercise.
            </div>

            <template v-else>
                <!-- Summary Stats -->
                <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <div
                        class="border-surface-200 dark:border-surface-700 rounded-lg border p-3 text-center"
                    >
                        <div class="text-xl font-bold">
                            {{ summaryStats.sessions }}
                        </div>
                        <div class="text-surface-500 text-xs">Sessions</div>
                    </div>
                    <div
                        v-if="hasWeightData"
                        class="border-surface-200 dark:border-surface-700 rounded-lg border p-3 text-center"
                    >
                        <div class="text-xl font-bold">
                            {{ summaryStats.prWeight }} lbs
                        </div>
                        <div class="text-surface-500 text-xs">PR Weight</div>
                    </div>
                    <div
                        v-if="hasWeightData"
                        class="border-surface-200 dark:border-surface-700 rounded-lg border p-3 text-center"
                    >
                        <div class="text-xl font-bold">
                            {{ summaryStats.bestVolume.toLocaleString() }}
                        </div>
                        <div class="text-surface-500 text-xs">
                            Best Volume (lbs)
                        </div>
                    </div>
                    <div
                        v-if="hasWeightData"
                        class="border-surface-200 dark:border-surface-700 rounded-lg border p-3 text-center"
                    >
                        <div class="text-xl font-bold">
                            {{ summaryStats.avgVolume.toLocaleString() }}
                        </div>
                        <div class="text-surface-500 text-xs">
                            Avg Volume (lbs)
                        </div>
                    </div>
                </div>

                <!-- Chart -->
                <div class="h-64">
                    <AppChart
                        :data="chartData"
                        :options="chartOptions"
                        type="line"
                    />
                </div>

                <!-- Session Details -->
                <div class="flex flex-col gap-2">
                    <div
                        v-for="group in historyByDate"
                        :key="group.date"
                        class="border-surface-200 dark:border-surface-700 rounded-lg border"
                    >
                        <button
                            class="flex w-full items-center justify-between p-3"
                            @click="toggleDate(group.date)"
                        >
                            <div class="flex items-center gap-2">
                                <i
                                    class="text-xs"
                                    :class="
                                        expandedDates[group.date]
                                            ? 'pi pi-chevron-down'
                                            : 'pi pi-chevron-right'
                                    "
                                />
                                <span class="font-medium">
                                    {{ group.date }}
                                </span>
                            </div>
                            <span class="text-surface-500 text-sm">
                                {{ group.routineName }}
                                &middot;
                                {{ group.sets.length }}
                                {{ group.sets.length === 1 ? 'set' : 'sets' }}
                            </span>
                        </button>

                        <div
                            v-if="expandedDates[group.date]"
                            class="border-surface-200 dark:border-surface-700 flex flex-col gap-1 border-t px-3 pt-2 pb-3"
                        >
                            <div
                                v-for="set in group.sets"
                                :key="set.set_number"
                                class="text-surface-600 dark:text-surface-400 flex items-center gap-3 text-sm"
                            >
                                <span class="text-surface-500 w-12">
                                    Set {{ set.set_number }}
                                </span>
                                <span>{{ set.reps }} reps</span>
                                <span>
                                    {{
                                        set.weight !== null
                                            ? `${set.weight} lbs`
                                            : '—'
                                    }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </template>

            <div class="flex justify-end">
                <AppButton label="Close" text @click="visible = false" />
            </div>
        </div>
    </AppDialog>
</template>
