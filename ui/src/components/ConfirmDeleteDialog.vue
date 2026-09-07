<script setup lang="ts">
defineProps<{
    visible: boolean;
}>();

const emit = defineEmits<{
    'update:visible': [value: boolean];
    confirm: [];
}>();
</script>

<template>
    <AppDialog
        header="Confirm Delete"
        modal
        :style="{ width: '24rem', maxWidth: '92vw' }"
        :visible="visible"
        @update:visible="emit('update:visible', $event)"
    >
        <p><slot /></p>
        <div class="mt-4 flex justify-end gap-2">
            <AppButton
                label="Cancel"
                text
                @click="emit('update:visible', false)"
            />
            <AppButton
                label="Delete"
                severity="danger"
                @click="emit('confirm')"
            />
        </div>
    </AppDialog>
</template>
