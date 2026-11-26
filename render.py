"""Turns the grouped items into an HTML email and a plain-text fallback."""

from html import escape


def _sorted(items):
    return sorted(items, key=lambda i: not i.highlight)  # highlights first


def render_html(title, categories, by_cat, errors):
    parts = [
        '<div style="font-family:-apple-system,Segoe UI,Arial,sans-serif;max-width:640px;margin:auto;color:#222">',
        f'<h1 style="font-size:22px;margin:0 0 16px">{escape(title)}</h1>',
    ]
    for key, meta in categories.items():
        items = by_cat.get(key)
        if not items:
            continue
        label = f"{meta.get('emoji', '')} {meta.get('title', key)}".strip()
        parts.append(f'<h2 style="font-size:17px;border-bottom:2px solid #eee;padding-bottom:4px;margin:24px 0 8px">{escape(label)} ({len(items)})</h2>')
        for it in _sorted(items):
            star = "★ " if it.highlight else ""
            name = escape(it.title)
            if it.link.startswith(("https://", "http://")):
                name = f'<a href="{escape(it.link)}" style="color:#0b57d0;text-decoration:none">{name}</a>'
            meta_line = " · ".join(escape(x) for x in (it.when, it.source) if x)
            parts.append('<div style="margin:0 0 12px">')
            parts.append(f'<div style="font-weight:600">{star}{name}</div>')
            parts.append(f'<div style="font-size:12px;color:#777">{meta_line}</div>')
            if it.summary:
                parts.append(f'<div style="font-size:14px;color:#444;margin-top:2px">{escape(it.summary)}</div>')
            parts.append("</div>")
    if errors:
        parts.append('<h2 style="font-size:15px;color:#a50e0e;margin-top:28px">Sources that failed this run</h2><ul style="font-size:13px;color:#666">')
        parts += [f"<li><b>{escape(n)}</b>: {escape(msg)}</li>" for n, msg in errors]
        parts.append("</ul>")
    parts.append("</div>")
    return "\n".join(parts)


def render_text(title, categories, by_cat, errors):
    lines = [title, "=" * len(title), ""]
    for key, meta in categories.items():
        items = by_cat.get(key)
        if not items:
            continue
        lines += [f"{meta.get('title', key).upper()} ({len(items)})", ""]
        for it in _sorted(items):
            lines.append(f"{'* ' if it.highlight else '- '}{it.title}")
            extra = " · ".join(x for x in (it.when, it.source) if x)
            if extra:
                lines.append(f"  {extra}")
            if it.link:
                lines.append(f"  {it.link}")
        lines.append("")
    if errors:
        lines.append("FAILED SOURCES")
        lines += [f"- {n}: {msg}" for n, msg in errors]
    return "\n".join(lines)
