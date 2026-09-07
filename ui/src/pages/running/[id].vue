<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import LoadingState from '@/components/LoadingState.vue';
import NotFoundState from '@/components/NotFoundState.vue';
import RouteMap from '@/components/RouteMap.vue';
import StatTileGrid from '@/components/StatTileGrid.vue';
import { useRunningApi } from '@/composables/api/useRunningApi';
import { useSmartBack } from '@/composables/useSmartBack';
import { useUnits } from '@/composables/useUnits';
import type {
    GpxSegment,
    RunLap,
    RunningActivity,
    RunSample,
} from '@/types/Running';
import { registerCharts } from '@/utils/chart';
import {
    detailTableClass,
    detailTableHoverRowClass,
} from '@/utils/detailTable';
import { formatDate, formatDuration } from '@/utils/format';
import { routePoints as toRoutePoints, type TimeRange } from '@/utils/route';

registerCharts();

const route = useRoute<'/running/[id]'>();
const { back } = useSmartBack('/running');
const { getActivity, getSegments, getLaps, getSamples } = useRunningApi();
const { distanceUnit, fmtDistance, fmtPace, fmtTemperature, fromKm } =
    useUnits();

const run = ref<RunningActivity | null>(null);
const segments = ref<GpxSegment[]>([]);
const laps = ref<RunLap[]>([]);
const samples = ref<RunSample[]>([]);
const loading = ref(true);
const notFound = ref(false);

async function load(id: number) {
    loading.value = true;
    notFound.value = false;
    run.value = null;
    segments.value = [];
    laps.value = [];
    samples.value = [];

    // Load the activity first: an unknown id should show one "not found" state,
    // not four separate 404 toasts from also probing its (nonexistent) tracks.
    const runRes = await getActivity(id);
    if (!runRes.success || !runRes.data) {
        notFound.value = true;
        loading.value = false;
        return;
    }
    run.value = runRes.data;

    const [segRes, lapRes, sampleRes] = await Promise.all([
        getSegments(id),
        getLaps(id),
        getSamples(id, 1500),
    ]);
    if (segRes.success && segRes.data) segments.value = segRes.data;
    if (lapRes.success && lapRes.data) laps.value = lapRes.data;
    if (sampleRes.success && sampleRes.data) samples.value = sampleRes.data;
    loading.value = false;
}

// Vue Router reuses this component instance when navigating between two
// run URLs directly, so the fetch must react to the param, not only mount.
watch(
    () => route.params.id,
    (value) => {
        const id = Number(value);
        if (Number.isNaN(id)) {
            notFound.value = true;
            loading.value = false;
            return;
        }
        void load(id);
    },
    { immediate: true },
);

const header = computed(() => {
    if (!run.value) return '';
    const name = run.value.title || 'Run';
    return `${name} — ${formatDate(run.value.date)}`;
});

// --- Summary tiles ---------------------------------------------------------
function fmtElevation(m: number): string {
    return distanceUnit.value === 'mi'
        ? `${Math.round(m * 3.28084)} ft`
        : `${Math.round(m)} m`;
}

// Headline numbers get their own large row; everything else is secondary.
const heroTiles = computed(() => {
    if (!run.value) return [];
    return [
        { label: 'Distance', value: fmtDistance(run.value.distance_km) },
        {
            label: 'Moving time',
            value: formatDuration(run.value.duration_seconds),
        },
        { label: 'Pace', value: fmtPace(run.value.pace) },
    ];
});

const detailTiles = computed(() => {
    if (!run.value) return [];
    const r = run.value;
    const out: { label: string; value: string }[] = [];
    if (r.elapsed_seconds && r.elapsed_seconds !== r.duration_seconds) {
        out.push({
            label: 'Elapsed',
            value: formatDuration(r.elapsed_seconds),
        });
    }
    if (r.avg_hr) {
        out.push({
            label: 'Heart rate',
            value: `${r.avg_hr} avg · ${r.max_hr ?? '—'} max`,
        });
    }
    if (r.avg_cadence)
        out.push({ label: 'Cadence', value: `${r.avg_cadence} spm` });
    if (r.calories)
        out.push({ label: 'Calories', value: `${r.calories} kcal` });
    if (r.total_ascent_m != null) {
        out.push({ label: 'Ascent', value: fmtElevation(r.total_ascent_m) });
    }
    if (r.avg_power)
        out.push({ label: 'Avg power', value: `${r.avg_power} W` });
    if (r.avg_temperature_c != null) {
        out.push({
            label: 'Temperature',
            value: fmtTemperature(r.avg_temperature_c),
        });
    }
    return out;
});

const routePoints = computed(() => toRoutePoints(samples.value));
const showMap = computed(
    () => !run.value?.is_indoor && routePoints.value.length >= 2,
);

// --- Hover highlight (laps / best efforts) -----------------------------------
const highlight = ref<TimeRange | null>(null);

/** Seconds from the run start covered by a lap. */
function lapRange(lap: RunLap, index: number): TimeRange | null {
    const runStart = run.value?.start_time
        ? Date.parse(run.value.start_time)
        : NaN;
    const lapStart = lap.start_time ? Date.parse(lap.start_time) : NaN;
    let start: number;
    if (!Number.isNaN(runStart) && !Number.isNaN(lapStart)) {
        start = (lapStart - runStart) / 1000;
    } else {
        // Fall back to summing the preceding laps' timer time.
        start = laps.value
            .slice(0, index)
            .reduce(
                (sum, l) => sum + (l.elapsed_seconds ?? l.timer_seconds),
                0,
            );
    }
    return { start, end: start + (lap.elapsed_seconds ?? lap.timer_seconds) };
}

function segmentRange(seg: GpxSegment): TimeRange | null {
    if (seg.start_seconds == null || seg.end_seconds == null) return null;
    return { start: seg.start_seconds, end: seg.end_seconds };
}

function setHighlight(range: TimeRange | null) {
    highlight.value = range;
}

/** Chart.js plugin: shade the highlighted time span behind the line. */
const highlightPlugin = {
    id: 'runHighlight',
    beforeDatasetsDraw(chart: {
        ctx: CanvasRenderingContext2D;
        chartArea: { top: number; bottom: number; left: number; right: number };
        scales: Record<string, { getPixelForValue: (v: number) => number }>;
    }) {
        const range = highlight.value;
        const xScale = chart.scales['x'];
        if (!range || !xScale) return;
        const ts = samples.value.map((s) => s.t_seconds);
        const first = ts.findIndex((t) => t >= range.start);
        let last = -1;
        for (let i = ts.length - 1; i >= 0; i--) {
            if (ts[i]! <= range.end) {
                last = i;
                break;
            }
        }
        if (first < 0 || last < first) return;
        const x1 = xScale.getPixelForValue(first);
        const x2 = xScale.getPixelForValue(last);
        const { top, bottom } = chart.chartArea;
        const { ctx } = chart;
        ctx.save();
        ctx.fillStyle = 'rgba(245, 158, 11, 0.18)';
        ctx.fillRect(
            Math.min(x1, x2),
            top,
            Math.max(2, Math.abs(x2 - x1)),
            bottom - top,
        );
        ctx.restore();
    },
};
const chartPlugins = [highlightPlugin];

// --- Charts -------------------------------------------------------------------
const chartLabels = computed(() =>
    samples.value.map((s) =>
        s.distance_km != null
            ? fromKm(s.distance_km).toFixed(2)
            : formatDuration(s.t_seconds),
    ),
);

function series<T>(pick: (s: RunSample) => T | null): (T | null)[] {
    return samples.value.map(pick);
}

const hasSeries = (values: (number | null)[]) =>
    values.filter((v) => v != null).length >= 2;

const hrSeries = computed(() => series((s) => s.heart_rate));

/** Centred rolling mean over `window` points; nulls are skipped, not zeroed. */
function smooth(values: (number | null)[], window = 9): (number | null)[] {
    const half = Math.floor(window / 2);
    return values.map((v, i) => {
        if (v == null) return null;
        let sum = 0;
        let n = 0;
        const lo = Math.max(0, i - half);
        const hi = Math.min(values.length - 1, i + half);
        for (let j = lo; j <= hi; j++) {
            const w = values[j];
            if (w != null) {
                sum += w;
                n++;
            }
        }
        return n ? Math.round((sum / n) * 100) / 100 : null;
    });
}

// Per-second GPS speed is noisy; smooth the pace so the line reads as effort.
const paceSeries = computed(() =>
    smooth(
        series((s) => {
            if (!s.speed_mps || s.speed_mps < 0.5) return null; // paused / walking
            const minPerKm = 1000 / s.speed_mps / 60;
            return distanceUnit.value === 'mi' ? minPerKm * 1.60934 : minPerKm;
        }),
    ),
);
const elevationSeries = computed(() =>
    series((s) =>
        s.altitude_m == null
            ? null
            : distanceUnit.value === 'mi'
              ? Math.round(s.altitude_m * 3.28084)
              : Math.round(s.altitude_m),
    ),
);

function lineData(label: string, data: (number | null)[], color: string) {
    return {
        labels: chartLabels.value,
        datasets: [
            {
                label,
                data,
                borderColor: color,
                backgroundColor: color + '22',
                fill: true,
                tension: 0.3,
                pointRadius: 0,
                spanGaps: true,
            },
        ],
    };
}

const xTitle = computed(() => `Distance (${distanceUnit.value})`);

function lineOptions(yTitle: string, reverse = false) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: false } },
        scales: {
            x: {
                title: { display: true, text: xTitle.value },
                ticks: { maxTicksLimit: 8 },
            },
            y: { reverse, title: { display: true, text: yTitle } },
        },
    };
}

const hrChart = computed(() =>
    lineData('Heart rate', hrSeries.value, '#ef4444'),
);
const paceChart = computed(() => lineData('Pace', paceSeries.value, '#6366f1'));
const elevationChart = computed(() =>
    lineData('Elevation', elevationSeries.value, '#22c55e'),
);
const paceUnit = computed(() => `min/${distanceUnit.value}`);
const elevationUnit = computed(() =>
    distanceUnit.value === 'mi' ? 'ft' : 'm',
);
</script>

<template>
    <div class="mx-auto max-w-7xl p-6">
        <button
            class="text-surface-500 hover:text-surface-900 dark:hover:text-surface-100 mb-4 inline-flex cursor-pointer items-center gap-1.5 text-sm"
            type="button"
            @click="back"
        >
            <i class="pi pi-arrow-left text-xs"></i>
            Back
        </button>

        <LoadingState v-if="loading" />

        <NotFoundState
            v-else-if="notFound"
            back-label="Back to Running"
            back-to="/running"
            entity="run"
        />

        <div v-else-if="run" class="flex flex-col gap-6">
            <h1 class="text-2xl font-bold">{{ header }}</h1>

            <div
                class="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_29rem]"
            >
                <!-- Left column: map + charts, sticky so a hovered lap or
                     best effort always stays visible while the tables scroll. -->
                <div
                    class="flex min-w-0 flex-col gap-6 lg:sticky lg:top-[4.5rem] lg:self-start"
                >
                    <StatTileGrid :tiles="heroTiles" value-size="xl" />
                    <div
                        v-if="detailTiles.length > 0"
                        class="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3"
                    >
                        <div v-for="tile in detailTiles" :key="tile.label">
                            <div class="text-surface-500 text-xs">
                                {{ tile.label }}
                            </div>
                            <div class="text-sm font-medium">
                                {{ tile.value }}
                            </div>
                        </div>
                    </div>

                    <div v-if="showMap">
                        <h3 class="mb-1 text-sm font-medium">Route</h3>
                        <RouteMap
                            :highlight="highlight"
                            :points="routePoints"
                        />
                    </div>

                    <div
                        v-if="samples.length > 1"
                        class="grid grid-cols-1 gap-4 lg:grid-cols-3"
                    >
                        <div v-if="hasSeries(hrSeries)">
                            <h3 class="mb-1 text-sm font-medium">
                                Heart rate (bpm)
                            </h3>
                            <div class="h-44">
                                <AppChart
                                    :data="hrChart"
                                    :options="lineOptions('bpm')"
                                    :plugins="chartPlugins"
                                    type="line"
                                />
                            </div>
                        </div>
                        <div v-if="hasSeries(paceSeries)">
                            <h3 class="mb-1 text-sm font-medium">
                                Pace ({{ paceUnit }})
                            </h3>
                            <div class="h-44">
                                <AppChart
                                    :data="paceChart"
                                    :options="lineOptions(paceUnit, true)"
                                    :plugins="chartPlugins"
                                    type="line"
                                />
                            </div>
                        </div>
                        <div v-if="hasSeries(elevationSeries)">
                            <h3 class="mb-1 text-sm font-medium">
                                Elevation ({{ elevationUnit }})
                            </h3>
                            <div class="h-44">
                                <AppChart
                                    :data="elevationChart"
                                    :options="lineOptions(elevationUnit)"
                                    :plugins="chartPlugins"
                                    type="line"
                                />
                            </div>
                        </div>
                    </div>

                    <div
                        v-if="
                            !showMap &&
                            samples.length === 0 &&
                            laps.length === 0 &&
                            segments.length === 0
                        "
                        class="text-surface-500 text-sm"
                    >
                        No track data for this run.
                    </div>
                </div>

                <!-- Right column: laps and best efforts, scrolls independently
                     of the sticky map/charts column. -->
                <div class="flex min-w-0 flex-col gap-6">
                    <div v-if="laps.length > 0">
                        <h3 class="mb-2 text-sm font-medium">Laps</h3>
                        <p class="text-surface-500 mb-2 text-xs">
                            Hover a row to see it on the map and charts.
                        </p>
                        <div class="overflow-x-auto">
                            <table
                                :class="[
                                    detailTableClass,
                                    detailTableHoverRowClass,
                                ]"
                            >
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>Distance</th>
                                        <th>Time</th>
                                        <th>Pace</th>
                                        <th>Avg HR</th>
                                        <th>Max HR</th>
                                        <th>Cadence</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr
                                        v-for="(lap, i) in laps"
                                        :key="lap.id"
                                        @mouseenter="
                                            setHighlight(lapRange(lap, i))
                                        "
                                        @mouseleave="setHighlight(null)"
                                    >
                                        <td>{{ lap.lap_index + 1 }}</td>
                                        <td>
                                            {{ fmtDistance(lap.distance_km) }}
                                        </td>
                                        <td>
                                            {{
                                                formatDuration(
                                                    lap.timer_seconds,
                                                )
                                            }}
                                        </td>
                                        <td>
                                            {{
                                                lap.pace != null
                                                    ? fmtPace(lap.pace)
                                                    : '—'
                                            }}
                                        </td>
                                        <td>{{ lap.avg_hr ?? '—' }}</td>
                                        <td>{{ lap.max_hr ?? '—' }}</td>
                                        <td>{{ lap.avg_cadence ?? '—' }}</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div v-if="segments.length > 0">
                        <h3 class="mb-2 text-sm font-medium">Best efforts</h3>
                        <div class="overflow-x-auto">
                            <table
                                :class="[
                                    detailTableClass,
                                    detailTableHoverRowClass,
                                ]"
                            >
                                <thead>
                                    <tr>
                                        <th>Segment</th>
                                        <th>Distance</th>
                                        <th>Time</th>
                                        <th>Pace</th>
                                        <th>Start</th>
                                        <th>End</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr
                                        v-for="seg in segments"
                                        :key="seg.id"
                                        @mouseenter="
                                            setHighlight(segmentRange(seg))
                                        "
                                        @mouseleave="setHighlight(null)"
                                    >
                                        <td>{{ seg.segment_name }}</td>
                                        <td>
                                            {{ fmtDistance(seg.distance_km) }}
                                        </td>
                                        <td>
                                            {{
                                                formatDuration(
                                                    seg.duration_seconds,
                                                )
                                            }}
                                        </td>
                                        <td>{{ fmtPace(seg.pace) }}</td>
                                        <td>
                                            {{
                                                seg.start_seconds != null
                                                    ? formatDuration(
                                                          seg.start_seconds,
                                                      )
                                                    : '—'
                                            }}
                                        </td>
                                        <td>
                                            {{
                                                seg.end_seconds != null
                                                    ? formatDuration(
                                                          seg.end_seconds,
                                                      )
                                                    : '—'
                                            }}
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
