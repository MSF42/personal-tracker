import { ref } from 'vue';

/**
 * Drag-and-drop handling for a file drop zone. `isOver` drives a visual
 * highlight while a matching drag is over the zone — tracked with an
 * enter/leave counter rather than a plain boolean, since `dragleave` fires
 * every time the pointer crosses a child element's border, not just when it
 * actually leaves the zone. Dropped files are filtered to `extensions`
 * before `onDrop` is called; a drop with no matching files is silently a
 * no-op (the caller's own toast strategy applies only to real attempts).
 */
export function useFileDrop(
    onDrop: (files: File[]) => void,
    extensions: string[],
) {
    const isOver = ref(false);
    let depth = 0;

    function hasFiles(e: DragEvent): boolean {
        return !!e.dataTransfer?.types.includes('Files');
    }

    function matches(file: File): boolean {
        const name = file.name.toLowerCase();
        return extensions.some((ext) => name.endsWith(ext));
    }

    function onDragEnter(e: DragEvent) {
        if (!hasFiles(e)) return;
        e.preventDefault();
        depth++;
        isOver.value = true;
    }

    function onDragOver(e: DragEvent) {
        if (!hasFiles(e)) return;
        e.preventDefault();
        if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
    }

    function onDragLeave(e: DragEvent) {
        if (!hasFiles(e)) return;
        e.preventDefault();
        depth = Math.max(0, depth - 1);
        if (depth === 0) isOver.value = false;
    }

    function onFileDrop(e: DragEvent) {
        if (!hasFiles(e)) return;
        e.preventDefault();
        depth = 0;
        isOver.value = false;
        const files = [...(e.dataTransfer?.files ?? [])].filter(matches);
        if (files.length > 0) onDrop(files);
    }

    return { isOver, onDragEnter, onDragOver, onDragLeave, onFileDrop };
}
