"""report(): figures and tables in order, numbered in the locale ("Abbildung 1", "Tabelle 2"), written as one
self-contained Markdown or HTML file with the images embedded. The rest of the document belongs to the document
tool; this only keeps the numbering and captions right."""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass, field
from pathlib import Path

from hairline.figure import HairlineFigure
from hairline.numbers import word


def escaped(content: str) -> str:
    return content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


@dataclass
class Report:
    """Items in the order added: (figure, caption). Tables (from `table()`) and figures are numbered apart."""

    title: str | None = None
    items: list[tuple[HairlineFigure, str | None]] = field(default_factory=list)
    dpi: int = 200

    def add(self, figure: HairlineFigure, caption: str | None = None) -> Report:
        """Add a figure or a table; `caption` is the sentence after its number (default: its title)."""
        if not isinstance(figure, HairlineFigure):
            raise ValueError(f"hairline: report: add() takes a hairline figure or table; got {type(figure).__name__}")
        self.items.append((figure, caption))
        return self

    def numbered(self) -> list[tuple[HairlineFigure, str, str]]:
        """Each item with its label ("Figure 2", "Tabelle 1") and caption, in the figure's own locale."""
        counts, found = {"figure": 0, "table": 0}, []
        for figure, caption in self.items:
            kind = "table" if figure.table_data is not None else "figure"
            counts[kind] += 1
            label = f"{word(kind, figure.settings.locale)} {counts[kind]}"
            found.append((figure, label, caption or figure.title))
        return found

    def write(self, path: str | os.PathLike) -> Path:
        """Write `path` as Markdown (.md) or HTML (.html): every image embedded, so the file stands alone."""
        target = Path(path)
        kind = target.suffix.lower()
        if kind not in (".md", ".html"):
            raise ValueError(f"hairline: report: write() makes .md or .html files; got {target.name!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.markdown() if kind == ".md" else self.html(), encoding="utf-8")
        return target

    def image(self, figure: HairlineFigure) -> str:
        buffer = io.BytesIO()
        figure.figure.savefig(buffer, format="png", dpi=self.dpi, metadata={"Software": None})
        return base64.b64encode(buffer.getvalue()).decode()

    def markdown(self) -> str:
        lines = [f"# {self.title}", ""] if self.title else []
        for figure, label, caption in self.numbered():
            lines += [f"![{escaped(label)}](data:image/png;base64,{self.image(figure)})", "",
                      f"**{label}.** {caption}", ""]
        return "\n".join(lines)

    def html(self) -> str:
        from hairline.charts.table import table_html
        parts = [f"<h1>{escaped(self.title)}</h1>"] if self.title else []
        for figure, label, caption in self.numbered():
            caption_html = f"<figcaption><b>{escaped(label)}.</b> {escaped(caption)}</figcaption>"
            if figure.table_data is not None:
                parts.append(f'<section class="hl-item">{caption_html}{table_html(figure)}</section>')
            else:
                parts.append(f'<figure class="hl-item"><img alt="{escaped(figure.title)}" style="max-width:100%" '
                             f'src="data:image/png;base64,{self.image(figure)}">{caption_html}</figure>')
        title = escaped(self.title or "Report")
        return (f'<!doctype html>\n<html><head><meta charset="utf-8"><title>{title}</title>'
                f'<style>body{{margin:0 auto;max-width:760px;padding:24px;font-family:sans-serif}}'
                f'.hl-item{{margin:0 0 32px}}figcaption{{font-size:0.9em;margin-top:6px}}</style></head>'
                f'<body>{"".join(parts)}</body></html>\n')


def report(title: str | None = None, dpi: int = 200) -> Report:
    """A report that numbers figures and tables in the order added, in each figure's locale:
    `hl.report("Quality report").add(fig).add(tab).write("report.html")`."""
    return Report(title=title, dpi=dpi)
