import { computed, nextTick, onMounted, ref, watch } from 'vue';

import { useNoteApi } from '@/composables/api/useNoteApi';
import type { NoteTreeNode } from '@/types/Note';

export function useNoteTree() {
    const { getNotes, createNote, updateNote, moveNote, deleteNote } =
        useNoteApi();

    const tree = ref<NoteTreeNode[]>([]);
    const focusId = ref<number | null>(null);
    const selectedNoteId = ref<number | null>(null);
    const focusedNodeId = ref<number | null>(null);
    const dirtyNodes = new Set<number>();

    // --- helpers ---

    function findInTree(
        nodes: NoteTreeNode[],
        id: number,
    ): NoteTreeNode | null {
        for (const n of nodes) {
            if (n.id === id) return n;
            const found = findInTree(n.children, id);
            if (found) return found;
        }
        return null;
    }

    function findPath(
        nodes: NoteTreeNode[],
        id: number,
        path: NoteTreeNode[],
    ): NoteTreeNode[] | null {
        for (const n of nodes) {
            if (n.id === id) return [...path, n];
            const found = findPath(n.children, id, [...path, n]);
            if (found) return found;
        }
        return null;
    }

    function findParentAndIndex(
        nodes: NoteTreeNode[],
        id: number,
        parent: NoteTreeNode | null = null,
    ): {
        parent: NoteTreeNode | null;
        index: number;
        siblings: NoteTreeNode[];
    } | null {
        for (let i = 0; i < nodes.length; i++) {
            const current = nodes[i]!;
            if (current.id === id) {
                return { parent, index: i, siblings: nodes };
            }
            if (current.children.length) {
                const found = findParentAndIndex(current.children, id, current);
                if (found) return found;
            }
        }
        return null;
    }

    function noteTitle(node: NoteTreeNode): string {
        const first = node.content.split('\n')[0]?.trim();
        return first || 'Untitled';
    }

    // --- computeds ---

    const selectedNote = computed(() =>
        selectedNoteId.value
            ? findInTree(tree.value, selectedNoteId.value)
            : null,
    );

    const focusedNode = computed(() =>
        focusedNodeId.value && selectedNote.value
            ? findInTree(selectedNote.value.children, focusedNodeId.value)
            : null,
    );

    const viewRoot = computed(
        () => focusedNode.value ?? selectedNote.value ?? null,
    );

    const focusedPath = computed<NoteTreeNode[]>(() =>
        focusedNodeId.value && selectedNote.value
            ? (findPath(selectedNote.value.children, focusedNodeId.value, []) ??
              [])
            : [],
    );

    interface FlatNode {
        node: NoteTreeNode;
        depth: number;
    }

    const flatNodes = computed<FlatNode[]>(() => {
        const result: FlatNode[] = [];
        function walk(nodes: NoteTreeNode[], depth: number) {
            for (const node of nodes) {
                result.push({ node, depth });
                if (!node.collapsed && node.children.length) {
                    walk(node.children, depth + 1);
                }
            }
        }
        walk(viewRoot.value?.children ?? [], 0);
        return result;
    });

    // --- data loading ---

    async function loadData() {
        const res = await getNotes();
        if (res.success && res.data) {
            tree.value = res.data;
            if (tree.value.length > 0 && !selectedNoteId.value) {
                selectedNoteId.value = tree.value[0]!.id;
            }
        }
    }

    onMounted(loadData);

    watch(selectedNoteId, () => {
        focusedNodeId.value = null;
    });

    // --- focus ---

    function setFocus(id: number) {
        focusId.value = id;
    }

    function focusTitleArea() {
        nextTick(() => {
            const el = document.querySelector(
                '[data-title-area]',
            ) as HTMLTextAreaElement | null;
            el?.focus();
        });
    }

    // --- mutations ---

    async function toggleCollapse(node: NoteTreeNode) {
        const newVal = !node.collapsed;
        await updateNote(node.id, { collapsed: newVal });
        node.collapsed = newVal;
    }

    async function addSibling(afterNode: NoteTreeNode) {
        const info = findParentAndIndex(tree.value, afterNode.id);
        if (!info) return;

        const newSortOrder = afterNode.sort_order + 1;

        // Bump sort_order for subsequent siblings
        for (let i = info.index + 1; i < info.siblings.length; i++) {
            const sibling = info.siblings[i]!;
            sibling.sort_order++;
            await moveNote(sibling.id, {
                parent_id: info.parent?.id ?? null,
                sort_order: sibling.sort_order,
            });
        }

        const res = await createNote({
            parent_id: info.parent?.id ?? null,
            content: '',
            sort_order: newSortOrder,
        });
        if (res.success && res.data) {
            const newNode: NoteTreeNode = {
                ...res.data,
                children: [],
            };
            info.siblings.splice(info.index + 1, 0, newNode);
            setFocus(newNode.id);
        }
    }

    async function addChild(parentNode: NoteTreeNode) {
        const res = await createNote({
            parent_id: parentNode.id,
            content: '',
        });
        if (res.success && res.data) {
            const newNode: NoteTreeNode = {
                ...res.data,
                children: [],
            };
            parentNode.children.push(newNode);
            parentNode.collapsed = false;
            await updateNote(parentNode.id, { collapsed: false });
            setFocus(newNode.id);
        }
    }

    async function addRootNote() {
        const res = await createNote({ content: '' });
        if (res.success && res.data) {
            const newNode: NoteTreeNode = {
                ...res.data,
                children: [],
            };
            tree.value.push(newNode);
            selectedNoteId.value = newNode.id;
            focusTitleArea();
        }
    }

    async function deleteRootNote(node: NoteTreeNode) {
        const idx = tree.value.findIndex((n) => n.id === node.id);
        if (idx === -1) return;
        await deleteNote(node.id);
        tree.value.splice(idx, 1);
        if (selectedNoteId.value === node.id) {
            selectedNoteId.value = tree.value[0]?.id ?? null;
        }
    }

    async function handleDelete(node: NoteTreeNode) {
        const info = findParentAndIndex(tree.value, node.id);
        if (!info) return;

        await deleteNote(node.id);
        info.siblings.splice(info.index, 1);

        // Focus previous visible node
        const flat = flatNodes.value;
        const idx = flat.findIndex((f) => f.node.id === node.id);
        if (idx > 0) {
            setFocus(flat[idx - 1]!.node.id);
        }
    }

    async function indent(node: NoteTreeNode) {
        const info = findParentAndIndex(tree.value, node.id);
        if (!info || info.index === 0) return;

        const prevSibling = info.siblings[info.index - 1]!;

        // Remove from current position
        info.siblings.splice(info.index, 1);

        // Add as last child of previous sibling
        const newSortOrder = prevSibling.children.length;
        prevSibling.children.push(node);
        prevSibling.collapsed = false;

        await moveNote(node.id, {
            parent_id: prevSibling.id,
            sort_order: newSortOrder,
        });
        await updateNote(prevSibling.id, { collapsed: false });
        setFocus(node.id);
    }

    async function outdent(node: NoteTreeNode) {
        const info = findParentAndIndex(tree.value, node.id);
        if (!info || !info.parent) return;

        const grandparentInfo = findParentAndIndex(tree.value, info.parent.id);
        if (!grandparentInfo) return;

        // Remove from parent's children
        info.siblings.splice(info.index, 1);

        // Insert after parent in grandparent's children
        const parentIdx = grandparentInfo.index;
        const newSortOrder = info.parent.sort_order + 1;

        // Bump subsequent siblings of grandparent
        for (let i = parentIdx + 1; i < grandparentInfo.siblings.length; i++) {
            const gpSibling = grandparentInfo.siblings[i]!;
            gpSibling.sort_order++;
            await moveNote(gpSibling.id, {
                parent_id: grandparentInfo.parent?.id ?? null,
                sort_order: gpSibling.sort_order,
            });
        }

        grandparentInfo.siblings.splice(parentIdx + 1, 0, node);

        await moveNote(node.id, {
            parent_id: grandparentInfo.parent?.id ?? null,
            sort_order: newSortOrder,
        });
        setFocus(node.id);
    }

    // --- content ---

    function handleInput(e: Event, node: NoteTreeNode) {
        const el = e.target as HTMLTextAreaElement;
        node.content = el.value;
        dirtyNodes.add(node.id);
        autoResize(e);
    }

    async function handleBlur(node: NoteTreeNode) {
        if (dirtyNodes.has(node.id)) {
            dirtyNodes.delete(node.id);
            await updateNote(node.id, { content: node.content });
        }
    }

    async function flushNode(node: NoteTreeNode) {
        if (dirtyNodes.has(node.id)) {
            dirtyNodes.delete(node.id);
            await updateNote(node.id, { content: node.content });
        }
    }

    function handleKeydown(e: KeyboardEvent, node: NoteTreeNode) {
        const target = e.target as HTMLTextAreaElement;

        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            flushNode(node).then(() => addSibling(node));
            return;
        }

        if (e.key === 'Tab' && !e.shiftKey) {
            e.preventDefault();
            flushNode(node).then(() => indent(node));
            return;
        }

        if (e.key === 'Tab' && e.shiftKey) {
            e.preventDefault();
            flushNode(node).then(() => outdent(node));
            return;
        }

        if (e.key === 'Backspace' && target.value === '') {
            e.preventDefault();
            handleDelete(node);
            return;
        }

        if (e.key === 'ArrowUp' && target.selectionStart === 0) {
            e.preventDefault();
            const flat = flatNodes.value;
            const idx = flat.findIndex((f) => f.node.id === node.id);
            if (idx > 0) setFocus(flat[idx - 1]!.node.id);
            return;
        }

        if (
            e.key === 'ArrowDown' &&
            target.selectionStart === target.value.length
        ) {
            e.preventDefault();
            const flat = flatNodes.value;
            const idx = flat.findIndex((f) => f.node.id === node.id);
            if (idx < flat.length - 1) setFocus(flat[idx + 1]!.node.id);
        }
    }

    function autoResize(e: Event) {
        const el = e.target as HTMLTextAreaElement;
        el.style.height = 'auto';
        el.style.height = el.scrollHeight + 'px';
    }

    return {
        // state
        tree,
        focusId,
        selectedNoteId,
        focusedNodeId,
        // computeds
        selectedNote,
        focusedNode,
        viewRoot,
        focusedPath,
        flatNodes,
        // helpers
        findInTree,
        findPath,
        noteTitle,
        // focus
        setFocus,
        focusTitleArea,
        // mutations
        toggleCollapse,
        addSibling,
        addChild,
        addRootNote,
        deleteRootNote,
        handleDelete,
        indent,
        outdent,
        // content
        handleInput,
        handleBlur,
        flushNode,
        handleKeydown,
        autoResize,
    };
}
