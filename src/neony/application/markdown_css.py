"""Scoped stylesheet for rendered Markdown content.

Injected once per window by :class:`NeonApplication` (next to the theme
block).  The stylesheet is fully token-driven: every colour goes through
the ``--md-*`` custom properties defined on ``[data-neony-markdown]``
(which point at ``--color-*`` theme tokens by default), so all eight
presets — and live theme switches — restyle rendered content, including
the syntax-highlight palette.  No literal colours live here.

Fenced code blocks sit on a pure, uniform surface: ``--color-bg`` — a
single clean dark in dark presets, a single clean light in light
presets, never blended with a theme hue — so code reads as code on
every bubble.  Hosts on colored fills re-point the ``--md-*``
properties instead of fighting the tokens; a ``from_me`` chat bubble
(see ``chat._ACCENT_MD_STYLE``) swaps the well to
``--color-accent-secondary`` and the text back to the page text color,
and lets links, rules and table bands ride the same secondary hue.
"""

from __future__ import annotations

_MARKDOWN_CSS = """
[data-neony-markdown] {
  --md-text: var(--color-text-primary);
  --md-muted: var(--color-text-secondary);
  --md-link: var(--color-accent);
  --md-link-decoration: none;
  --md-chip: var(--color-surface-raised);
  --md-line: var(--color-border);
  /* The code well: pure page background by default — one clean dark in
     dark presets, one clean light in light presets, no hue mixed in.
     Hosts on colored fills re-point it (from_me bubbles use
     --color-accent-secondary) via --md-well-bg.  The table header band
     and zebra stripe are re-pointable too. */
  --md-well-bg: var(--color-bg);
  --md-th-chip: var(--md-chip);
  --md-zebra: var(--md-chip);
  line-height: 1.55; word-wrap: break-word;
}
[data-neony-markdown] > :first-child { margin-top: 0; }
[data-neony-markdown] > :last-child { margin-bottom: 0; }
[data-neony-markdown] h1, [data-neony-markdown] h2, [data-neony-markdown] h3,
[data-neony-markdown] h4, [data-neony-markdown] h5, [data-neony-markdown] h6 {
  margin: 14px 0 6px; font-weight: 700; line-height: 1.25;
  color: var(--md-text);
}
[data-neony-markdown] h1, [data-neony-markdown] h2 {
  padding-bottom: 4px; border-bottom: 1px solid var(--md-line);
}
[data-neony-markdown] h1 { font-size: 1.5em; }
[data-neony-markdown] h2 { font-size: 1.3em; }
[data-neony-markdown] h3 { font-size: 1.15em; }
[data-neony-markdown] h4 { font-size: 1.05em; }
[data-neony-markdown] h5 { font-size: 1em; }
[data-neony-markdown] h6 { font-size: 0.95em; color: var(--md-muted); }
[data-neony-markdown] p { margin: 6px 0; }
[data-neony-markdown] a { color: var(--md-link); text-decoration: var(--md-link-decoration); }
[data-neony-markdown] a:hover { text-decoration: underline; }
[data-neony-markdown] code {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.9em;
  background: var(--md-chip);
  /* Opaque raised chip — page text always reads on it, whatever the
     host bubble's own text color is. */
  color: var(--color-text-primary);
  padding: 1px 5px; border-radius: 4px;
}
[data-neony-markdown] pre {
  margin: 8px 0; padding: 10px 12px; border-radius: 8px;
  border: 1px solid var(--md-line);
  /* Pure page background — one clean dark per dark preset, one clean
     light per light preset, no theme hue blended in.  A from_me bubble
     re-points this to --color-accent-secondary. */
  background-color: var(--md-well-bg);
  overflow-x: auto;
}
[data-neony-markdown] pre code {
  display: block; background: transparent; padding: 0; font-size: 0.88em;
  /* Page text, not the host's bubble text: the well keeps its own
     readable ink whatever fill it sits on. */
  color: var(--color-text-primary);
}
/* Syntax highlighting palette — theme hue tokens, restyled by every
   preset along with the well they sit on.  Keyword-class tokens can be
   re-pointed by the host: on a well tinted with the accent family
   (from_me bubbles) they would blend into it. */
[data-neony-markdown] .hljs-comment, [data-neony-markdown] .hljs-quote {
  color: var(--color-text-secondary); font-style: italic;
}
[data-neony-markdown] .hljs-keyword,
[data-neony-markdown] .hljs-selector-tag,
[data-neony-markdown] .hljs-selector-id,
[data-neony-markdown] .hljs-selector-class {
  color: var(--md-hi-keyword, var(--color-accent));
}
[data-neony-markdown] .hljs-built_in,
[data-neony-markdown] .hljs-type,
[data-neony-markdown] .hljs-title.function_,
[data-neony-markdown] .hljs-title.class_,
[data-neony-markdown] .hljs-class {
  color: var(--md-hi-dim, var(--color-accent-dim));
}
[data-neony-markdown] .hljs-string,
[data-neony-markdown] .hljs-regexp,
[data-neony-markdown] .hljs-template-variable,
[data-neony-markdown] .hljs-addition {
  color: var(--color-success);
}
[data-neony-markdown] .hljs-number,
[data-neony-markdown] .hljs-symbol,
[data-neony-markdown] .hljs-bullet,
[data-neony-markdown] .hljs-link,
[data-neony-markdown] .hljs-deletion {
  color: var(--color-danger);
}
[data-neony-markdown] .hljs-meta,
[data-neony-markdown] .hljs-doctag {
  color: var(--color-text-secondary);
}
[data-neony-markdown] .hljs-title,
[data-neony-markdown] .hljs-section,
[data-neony-markdown] .hljs-name {
  color: var(--color-text-primary); font-weight: 700;
}
[data-neony-markdown] .hljs-attr,
[data-neony-markdown] .hljs-attribute,
[data-neony-markdown] .hljs-variable,
[data-neony-markdown] .hljs-property,
[data-neony-markdown] .hljs-params,
[data-neony-markdown] .hljs-operator,
[data-neony-markdown] .hljs-punctuation {
  color: var(--color-text-primary);
}
[data-neony-markdown] .hljs-subst { color: var(--color-text-primary); }
[data-neony-markdown] .hljs-emphasis { font-style: italic; }
[data-neony-markdown] .hljs-strong { font-weight: 700; }
[data-neony-markdown] blockquote {
  margin: 8px 0; padding: 2px 12px;
  border-left: 3px solid var(--md-line);
  color: var(--md-muted);
}
[data-neony-markdown] ul, [data-neony-markdown] ol { margin: 6px 0; padding-left: 22px; }
[data-neony-markdown] li { margin: 2px 0; }
[data-neony-markdown] table { border-collapse: collapse; margin: 8px 0; }
[data-neony-markdown] th, [data-neony-markdown] td {
  border: 1px solid var(--md-line); padding: 4px 10px; color: var(--md-text);
}
[data-neony-markdown] th { background: var(--md-th-chip); font-weight: 700; }
[data-neony-markdown] tbody tr:nth-child(even) { background: var(--md-zebra); }
[data-neony-markdown] hr { border: none; border-top: 1px solid var(--md-line); margin: 12px 0; }
[data-neony-markdown] img { max-width: 100%; border-radius: 8px; }
""".strip()

#: The scoped Markdown stylesheet (injected once per window).
MARKDOWN_CSS: str = _MARKDOWN_CSS

__all__ = ["MARKDOWN_CSS"]
