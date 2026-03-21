import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { NoteTreeNode } from '@/types/Note';

vi.mock('@/composables/api/useNoteApi', () => ({
    useNoteApi: () => ({
        getNotes: vi.fn().mockResolvedValue({ success: false }),
        createNote: vi.fn(),
        updateNote: vi.fn(),
        moveNote: vi.fn(),
        deleteNote: vi.fn(),
    }),
}));

// Prevent onMounted from running in Node environment
vi.mock('vue', async () => {
    const actual = await vi.importActual<typeof import('vue')>('vue');
    return {
        ...actual,
        onMounted: vi.fn(),
    };
});

import { useNoteTree } from '../useNoteTree';

// --- helpers ---

function makeNode(
    id: number,
    children: NoteTreeNode[] = [],
    collapsed = false,
): NoteTreeNode {
    return {
        id,
        content: `Note ${id}`,
        parent_id: null,
        sort_order: id,
        collapsed,
        created_at: '2024-01-01T00:00:00',
        updated_at: '2024-01-01T00:00:00',
        children,
    };
}

/**
 * Builds a test tree:
 *
 * root (id=1)
 *   child1 (id=2)
 *     grandchild (id=4)
 *   child2 (id=3)
 */
function buildTestTree(): NoteTreeNode[] {
    const grandchild = makeNode(4);
    const child1 = makeNode(2, [grandchild]);
    const child2 = makeNode(3);
    const root = makeNode(1, [child1, child2]);
    return [root];
}

describe('useNoteTree', () => {
    let nt: ReturnType<typeof useNoteTree>;

    beforeEach(() => {
        nt = useNoteTree();
        nt.tree.value = buildTestTree();
        nt.selectedNoteId.value = null;
        nt.focusedNodeId.value = null;
    });

    // --- findInTree ---

    describe('findInTree', () => {
        it('finds a root-level node by id', () => {
            const node = nt.findInTree(nt.tree.value, 1);
            expect(node).not.toBeNull();
            expect(node!.id).toBe(1);
        });

        it('finds a deeply nested node', () => {
            const node = nt.findInTree(nt.tree.value, 4);
            expect(node).not.toBeNull();
            expect(node!.id).toBe(4);
        });

        it('returns null for a non-existent id', () => {
            const node = nt.findInTree(nt.tree.value, 999);
            expect(node).toBeNull();
        });
    });

    // --- findPath ---

    describe('findPath', () => {
        it('returns a single-element array (the node itself) for a root node', () => {
            const path = nt.findPath(nt.tree.value, 1, []);
            expect(path).not.toBeNull();
            // Path includes the node itself; root has no ancestors before it
            const last = path![path!.length - 1];
            expect(last!.id).toBe(1);
            expect(path!.length).toBe(1);
        });

        it('returns the full ancestor chain for a nested node', () => {
            // grandchild (id=4) is under root(1) -> child1(2) -> grandchild(4)
            const path = nt.findPath(nt.tree.value, 4, []);
            expect(path).not.toBeNull();
            // path = [root(1), child1(2), grandchild(4)]
            expect(path!.map((n) => n.id)).toEqual([1, 2, 4]);
        });

        it('returns null when the id is not found', () => {
            const path = nt.findPath(nt.tree.value, 999, []);
            expect(path).toBeNull();
        });

        it('returns correct path for a direct child', () => {
            const path = nt.findPath(nt.tree.value, 3, []);
            expect(path).not.toBeNull();
            expect(path!.map((n) => n.id)).toEqual([1, 3]);
        });
    });

    // --- flatNodes ---

    describe('flatNodes', () => {
        it('returns empty array when no note is selected', () => {
            nt.selectedNoteId.value = null;
            expect(nt.flatNodes.value).toEqual([]);
        });

        it('returns children of selected root in depth-first order', () => {
            // Select root (id=1); viewRoot = selectedNote = root
            // flatNodes walks root.children: child1(2), grandchild(4), child2(3)
            nt.selectedNoteId.value = 1;
            const ids = nt.flatNodes.value.map((f) => f.node.id);
            expect(ids).toEqual([2, 4, 3]);
        });

        it('assigns correct depth values', () => {
            nt.selectedNoteId.value = 1;
            const flat = nt.flatNodes.value;
            const byId = Object.fromEntries(flat.map((f) => [f.node.id, f.depth]));
            expect(byId[2]).toBe(0); // child1 — depth 0
            expect(byId[4]).toBe(1); // grandchild — depth 1
            expect(byId[3]).toBe(0); // child2 — depth 0
        });

        it('skips collapsed subtrees', () => {
            // Collapse child1 (id=2) so grandchild (id=4) is not walked
            nt.selectedNoteId.value = 1;
            const root = nt.findInTree(nt.tree.value, 1)!;
            const child1 = root.children[0]!;
            child1.collapsed = true;

            const ids = nt.flatNodes.value.map((f) => f.node.id);
            expect(ids).toEqual([2, 3]); // grandchild(4) excluded
        });
    });
});
