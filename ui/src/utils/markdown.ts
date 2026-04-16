import DOMPurify from 'dompurify';
import hljs from 'highlight.js/lib/core';
import bash from 'highlight.js/lib/languages/bash';
import css from 'highlight.js/lib/languages/css';
import javascript from 'highlight.js/lib/languages/javascript';
import json from 'highlight.js/lib/languages/json';
import python from 'highlight.js/lib/languages/python';
import sql from 'highlight.js/lib/languages/sql';
import typescript from 'highlight.js/lib/languages/typescript';
import xml from 'highlight.js/lib/languages/xml';
import { Marked } from 'marked';

import { resolveUploadsUrl } from './uploads';
import { preprocessNoteMarkdown } from './wiki';

hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('js', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('ts', typescript);
hljs.registerLanguage('python', python);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('json', json);
hljs.registerLanguage('html', xml);
hljs.registerLanguage('css', css);
hljs.registerLanguage('sql', sql);

const marked = new Marked({
    renderer: {
        code({ text, lang }) {
            const language = lang && hljs.getLanguage(lang) ? lang : undefined;
            const highlighted = language
                ? hljs.highlight(text, { language }).value
                : hljs.highlightAuto(text).value;
            return `<pre><code class="hljs${language ? ` language-${language}` : ''}">${highlighted}</code></pre>`;
        },
    },
});

// DOMPurify normally drops non-standard attributes, but the outliner relies on
// data-wiki/data-tag/data-mention being preserved so a delegated click handler
// can drive navigation.
const PURIFY_CONFIG = { ADD_ATTR: ['data-wiki', 'data-tag', 'data-mention'] };

// In Electron the page is served from file:// so <img src="/uploads/...">
// won't reach the API server. Rewrite those srcs after sanitization.
function resolveImageSrcs(html: string): string {
    return html.replace(
        /(<img\s[^>]*\bsrc=")\/uploads\//g,
        (_, before) => `${before}${resolveUploadsUrl('/uploads/')}`,
    );
}

export function renderMarkdown(content: string): string {
    if (!content) return '';
    const pre = preprocessNoteMarkdown(content);
    const isMultiLine = pre.includes('\n');
    const html = isMultiLine
        ? (marked.parse(pre) as string)
        : (marked.parseInline(pre) as string);
    return resolveImageSrcs(DOMPurify.sanitize(html, PURIFY_CONFIG));
}
