<script setup lang="ts">
import { nextTick, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import { useSearchApi } from '@/composables/api/useSearchApi';
import { useUiState } from '@/composables/useUiState';
import type { SearchHit, SearchKind } from '@/types/Search';

const ui = useUiState();
const router = useRouter();
const { search } = useSearchApi();

const inputRef = ref<HTMLInputElement | null>(null);
const query = ref('');
const hits = ref<SearchHit[]>([]);
const selectedIdx = ref(0);
let searchTimer: ReturnType<typeof setTimeout> | null = null;

watch(
    () => ui.paletteOpen.value,
    async (open) => {
        if (!open) return;
        query.value = ui.paletteInitialQuery.value || '';
        hits.value = [];
        selectedIdx.value = 0;
        await nextTick();
        inputRef.value?.focus();
        if (query.value) runSearch();
    },
);

watch(query, () => {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(runSearch, 150);
});

onUnmounted(() => {
    if (searchTimer) clearTimeout(searchTimer);
});

async function runSearch() {
    const q = query.value.trim();
    if (!q) {
        hits.value = [];
        return;
    }
    const res = await search(q);
    if (res.success && res.data) {
        hits.value = res.data.hits;
        selectedIdx.value = 0;
    } else {
        hits.value = [];
    }
}

function routeFor(hit: SearchHit): string {
    const routes: Record<SearchKind, string> = {
        note: `/notes?note=${hit.entity_id}`,
        task: `/tasks?task=${hit.entity_id}`,
        habit: `/habits?habit=${hit.entity_id}`,
        exercise: `/exercises?exercise=${hit.entity_id}`,
        routine: `/workout-routines?routine=${hit.entity_id}`,
    };
    return routes[hit.kind];
}

async function jumpTo(hit: SearchHit) {
    ui.closePalette();
    await router.push(routeFor(hit));
}

function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
        e.preventDefault();
        ui.closePalette();
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (hits.value.length) {
            selectedIdx.value = (selectedIdx.value + 1) % hits.value.length;
        }
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (hits.value.length) {
            selectedIdx.value =
                (selectedIdx.value - 1 + hits.value.length) % hits.value.length;
        }
    } else if (e.key === 'Enter') {
        e.preventDefault();
        const hit = hits.value[selectedIdx.value];
        if (hit) jumpTo(hit);
    }
}
</script>

<template>
    <Transition
        enter-active-class="transition-opacity duration-150"
        enter-from-class="opacity-0"
        leave-active-class="transition-opacity duration-100"
        leave-to-class="opacity-0"
    >
        <div
            v-if="ui.paletteOpen.value"
            class="fixed inset-0 z-[1000] flex items-start justify-center bg-black/60 pt-[12vh] backdrop-blur-sm"
            @click.self="ui.closePalette()"
        >
            <div
                class="border-surface-200 bg-surface-0 dark:border-surface-700 dark:bg-surface-900 w-[640px] max-w-[92vw] overflow-hidden rounded-xl border shadow-2xl"
            >
                <div
                    class="border-surface-200 dark:border-surface-700 flex items-center gap-2 border-b px-4 py-3"
                >
                    <i class="pi pi-search text-primary-500 text-sm"></i>
                    <input
                        ref="inputRef"
                        v-model="query"
                        class="text-surface-900 dark:text-surface-100 placeholder:text-surface-400 flex-1 bg-transparent text-sm outline-none"
                        placeholder="Search notes, tasks, habits, exercises, routines…"
                        type="text"
                        @keydown="onKeydown"
                    />
                    <span
                        class="text-surface-400 text-[10px] tracking-widest uppercase"
                        >esc</span
                    >
                </div>
                <div class="max-h-[55vh] overflow-y-auto">
                    <div
                        v-if="!query"
                        class="text-surface-400 px-4 py-6 text-center text-xs"
                    >
                        Type to search across everything.
                    </div>
                    <div
                        v-else-if="!hits.length"
                        class="text-surface-400 px-4 py-6 text-center text-xs"
                    >
                        No results
                    </div>
                    <button
                        v-for="(hit, i) in hits"
                        :key="hit.kind + '-' + hit.entity_id"
                        :class="[
                            'flex w-full items-start gap-3 border-l-2 px-4 py-2.5 text-left transition-colors',
                            i === selectedIdx
                                ? 'border-primary-500 bg-surface-100 dark:bg-surface-800'
                                : 'hover:bg-surface-50 dark:hover:bg-surface-800/50 border-transparent',
                        ]"
                        @click="jumpTo(hit)"
                        @mouseenter="selectedIdx = i"
                    >
                        <span
                            class="text-surface-400 w-16 shrink-0 text-[10px] tracking-widest uppercase"
                        >
                            {{ hit.kind }}
                        </span>
                        <div class="min-w-0 flex-1">
                            <div
                                class="text-surface-900 dark:text-surface-100 truncate text-sm font-semibold"
                            >
                                {{ hit.title || '(untitled)' }}
                            </div>
                            <div
                                v-if="hit.snippet"
                                class="text-surface-500 mt-0.5 line-clamp-2 text-xs"
                                v-html="hit.snippet"
                            ></div>
                        </div>
                    </button>
                </div>
            </div>
        </div>
    </Transition>
</template>

<style>
.wikilink {
    color: rgb(59 130 246);
    background: rgba(59, 130, 246, 0.08);
    border: 1px solid rgba(59, 130, 246, 0.22);
    padding: 0 5px;
    border-radius: 4px;
    text-decoration: none;
    font-weight: 500;
}
.wikilink:hover {
    background: rgba(59, 130, 246, 0.18);
}
.tag {
    color: rgb(14 165 233);
    background: rgba(14, 165, 233, 0.1);
    padding: 0 4px;
    border-radius: 3px;
    font-size: 12px;
    cursor: pointer;
}
.mention {
    color: rgb(168 85 247);
    background: rgba(168, 85, 247, 0.1);
    padding: 0 4px;
    border-radius: 3px;
    font-size: 12px;
    cursor: pointer;
}
mark {
    background: rgba(245, 165, 36, 0.25);
    color: inherit;
    padding: 0 2px;
    border-radius: 2px;
}
@keyframes flash-highlight {
    0% {
        background-color: rgba(59, 130, 246, 0.25);
    }
    100% {
        background-color: transparent;
    }
}
.flash-highlight {
    animation: flash-highlight 1.2s ease-out;
}
</style>
