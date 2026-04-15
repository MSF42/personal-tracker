// Pre-processing helpers for note content. These run *before* marked so that
// wiki-links, tags, and mentions are rendered as styled HTML spans/anchors
// that the outliner can attach click handlers to via event delegation.

const WIKI_RE = /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g;
const TAG_RE = /(^|\s)#([a-zA-Z0-9_-]{2,32})/g;
const MENTION_RE = /(^|\s)@([a-zA-Z0-9_-]{2,32})/g;

function escapeAttr(value: string): string {
    return value
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

export function transformWikiLinks(text: string): string {
    return text.replace(WIKI_RE, (_, target: string, alias?: string) => {
        const label = (alias ?? target).trim();
        const cleanTarget = target.trim();
        const attr = escapeAttr(cleanTarget);
        return `<a class="wikilink" data-wiki="${attr}" href="#wiki:${encodeURIComponent(cleanTarget)}">${label}</a>`;
    });
}

export function transformTagsAndMentions(text: string): string {
    return text
        .replace(TAG_RE, (_, prefix: string, tag: string) => {
            return `${prefix}<span class="tag" data-tag="#${tag}">#${tag}</span>`;
        })
        .replace(MENTION_RE, (_, prefix: string, name: string) => {
            return `${prefix}<span class="mention" data-mention="@${name}">@${name}</span>`;
        });
}

export function preprocessNoteMarkdown(raw: string): string {
    if (!raw) return '';
    return transformTagsAndMentions(transformWikiLinks(raw));
}
