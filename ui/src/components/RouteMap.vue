<script setup lang="ts">
import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import { sliceByTime, type TimeRange, type TrackPoint } from '@/utils/route';

import RouteOutline from './RouteOutline.vue';

const props = defineProps<{
    points: TrackPoint[];
    highlight?: TimeRange | null;
}>();

const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const ATTRIBUTION =
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
// Give up on tiles after this many failures before a single success.
const MAX_TILE_ERRORS = 4;

const mode = ref<'map' | 'outline'>(
    typeof navigator !== 'undefined' && navigator.onLine === false
        ? 'outline'
        : 'map',
);
const el = ref<HTMLElement | null>(null);

let map: L.Map | null = null;
let bounds: L.LatLngBounds | null = null;
let routeLine: L.Polyline | null = null;
let highlightLine: L.Polyline | null = null;
let observer: ResizeObserver | null = null;

function destroyMap() {
    map?.remove();
    map = null;
    bounds = null;
    routeLine = null;
    highlightLine = null;
}

function hasSize(node: HTMLElement | null): node is HTMLElement {
    return !!node && node.clientWidth > 0 && node.clientHeight > 0;
}

function buildMap() {
    destroyMap();
    // Dialogs lay out after mount; building into a zero-width box makes
    // Leaflet fit the route into nothing and zoom to a single street.
    if (!hasSize(el.value) || props.points.length < 2) return;

    map = L.map(el.value, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: false,
    });

    let errors = 0;
    let loaded = false;
    const tiles = L.tileLayer(TILE_URL, {
        maxZoom: 19,
        attribution: ATTRIBUTION,
    });
    tiles.on('tileload', () => {
        loaded = true;
    });
    tiles.on('tileerror', () => {
        errors++;
        if (!loaded && errors >= MAX_TILE_ERRORS) {
            mode.value = 'outline';
            destroyMap();
        }
    });
    tiles.addTo(map);

    const latlngs = props.points.map((p) => [p.lat, p.lon] as L.LatLngTuple);
    const line = L.polyline(latlngs, {
        color: '#6366f1',
        weight: 4,
        opacity: 0.9,
    }).addTo(map);
    routeLine = line;
    const marker = (pt: L.LatLngTuple, color: string) =>
        L.circleMarker(pt, {
            radius: 6,
            color: '#ffffff',
            weight: 2,
            fillColor: color,
            fillOpacity: 1,
        }).addTo(map!);
    marker(latlngs[0]!, '#22c55e');
    marker(latlngs[latlngs.length - 1]!, '#ef4444');

    bounds = line.getBounds();
    map.fitBounds(bounds, { padding: [16, 16] });
    applyHighlight();
}

/** Draw (or clear) the hovered lap / best effort on top of the route. */
function applyHighlight() {
    if (!map || !routeLine) return;
    highlightLine?.remove();
    highlightLine = null;
    const slice = sliceByTime(props.points, props.highlight);
    if (slice.length < 2) {
        routeLine.setStyle({ opacity: 0.9 });
        return;
    }
    routeLine.setStyle({ opacity: 0.35 });
    highlightLine = L.polyline(
        slice.map((p) => [p.lat, p.lon] as L.LatLngTuple),
        { color: '#f59e0b', weight: 6, opacity: 1 },
    ).addTo(map);
}

watch(() => props.highlight, applyHighlight);

/** Build once the box has a size, then keep the route framed as it resizes. */
function observe() {
    observer?.disconnect();
    observer = null;
    if (!el.value) return;
    observer = new ResizeObserver(() => {
        if (mode.value !== 'map') return;
        if (!map) {
            buildMap();
        } else if (hasSize(el.value)) {
            map.invalidateSize();
            if (bounds) map.fitBounds(bounds, { padding: [16, 16] });
        }
    });
    observer.observe(el.value);
}

function goOffline() {
    mode.value = 'outline';
    observer?.disconnect();
    observer = null;
    destroyMap();
}

async function goOnline() {
    mode.value = 'map';
    await nextTick();
    buildMap();
    observe();
}

onMounted(() => {
    if (mode.value === 'map') {
        buildMap();
        observe();
    }
    window.addEventListener('offline', goOffline);
    window.addEventListener('online', goOnline);
});

watch(
    () => props.points,
    async () => {
        if (mode.value !== 'map') return;
        await nextTick();
        buildMap();
    },
);

onBeforeUnmount(() => {
    window.removeEventListener('offline', goOffline);
    window.removeEventListener('online', goOnline);
    observer?.disconnect();
    destroyMap();
});
</script>

<template>
    <div
        class="border-surface-200 dark:border-surface-700 route-map h-64 w-full overflow-hidden rounded-lg border"
    >
        <div v-if="mode === 'map'" ref="el" class="h-full w-full" />
        <RouteOutline v-else :highlight="highlight" :points="points" />
    </div>
</template>

<style>
/* Unscoped on purpose: Vue's scoped compiler turned a :global()/:deep() mix
   into a bare `.dark { filter: … }` rule that inverted the whole app. The
   `.route-map` class is unique to this component, so plain selectors are safe. */

/* OpenStreetMap only ships light tiles; invert them for the dark theme. */
.dark .route-map .leaflet-tile-pane {
    filter: invert(1) hue-rotate(180deg) brightness(0.9) contrast(0.9);
}
.dark .route-map .leaflet-control-attribution,
.dark .route-map .leaflet-bar a {
    background: #1f2937;
    color: #d1d5db;
    border-color: #374151;
}
.dark .route-map .leaflet-control-attribution a {
    color: #93c5fd;
}
</style>
