<script setup lang="ts">
import { useUnits } from '@/composables/useUnits';
import type { RunBadge } from '@/types/Running';
import {
    BADGE_ICONS,
    badgeDetail,
    badgeLabel,
    badgeText,
} from '@/utils/badges';

// `compact` shows icons only (with the wording as a tooltip) for table cells;
// otherwise each badge is a chip with its headline and value. "Ever" badges
// are highlighted in amber.
withDefaults(defineProps<{ badges: RunBadge[]; compact?: boolean }>(), {
    compact: false,
});

const { fmtDistance } = useUnits();

const tone = (b: RunBadge) =>
    b.ever
        ? 'border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-300'
        : 'border-primary-200 bg-primary-50 text-primary-800 dark:border-primary-800 dark:bg-primary-950 dark:text-primary-300';
</script>

<template>
    <div v-if="compact" class="flex flex-wrap gap-1">
        <span
            v-for="(b, i) in badges"
            :key="i"
            v-tooltip.top="badgeText(b, fmtDistance)"
            :aria-label="badgeText(b, fmtDistance)"
            class="inline-flex h-6 w-6 items-center justify-center rounded-full border text-xs"
            :class="tone(b)"
            role="img"
        >
            <i :class="BADGE_ICONS[b.kind]"></i>
        </span>
    </div>
    <div v-else class="flex flex-wrap gap-2">
        <span
            v-for="(b, i) in badges"
            :key="i"
            class="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm"
            :class="tone(b)"
        >
            <i class="text-xs" :class="BADGE_ICONS[b.kind]"></i>
            <span class="font-medium">{{ badgeLabel(b) }}</span>
            <span v-if="badgeDetail(b, fmtDistance)" class="opacity-70">
                · {{ badgeDetail(b, fmtDistance) }}
            </span>
        </span>
    </div>
</template>
