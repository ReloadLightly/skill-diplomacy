"""A small SVG plotting layer, standard library only.

Why not matplotlib. This repository's strongest practical claim is that every
deterministic result reproduces from a bare interpreter with nothing installed.
A figure pipeline that needs a 40MB numerical stack would quietly retire that
claim at exactly the point a reviewer goes looking for it — "reproduce the
figures" is the one instruction an artifact evaluator always runs. SVG is
vector, is accepted by every journal, and is a few hundred lines of string
formatting away, so the promise survives.

Scope is deliberately narrow: grouped bars with error bars, and lines with
markers. That is what the argument needs; anything more is scope creep in a
plotting library that exists to serve four figures.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

# A colourblind-safe qualitative set (Okabe–Ito), which matters here because
# the figures that carry the argument are two-condition comparisons and a
# reader who cannot separate the conditions cannot read the result.
INK = "#1a1a1a"
MUTED = "#6b7280"
GRID = "#e5e7eb"
SERIES = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]


def _fmt(x: float) -> str:
    return f"{x:.2f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))


@dataclass
class Axes:
    """A linear y-axis over a categorical or linear x-axis, in pixel space."""
    width: int = 760
    height: int = 420
    pad_left: int = 72
    pad_right: int = 24
    pad_top: int = 56
    pad_bottom: int = 76
    ymin: float = 0.0
    ymax: float = 1.0
    title: str = ""
    ylabel: str = ""
    xlabel: str = ""
    subtitle: str = ""
    parts: list[str] = field(default_factory=list)

    # -- geometry ----------------------------------------------------------
    @property
    def x0(self) -> int: return self.pad_left

    @property
    def x1(self) -> int: return self.width - self.pad_right

    @property
    def y0(self) -> int: return self.height - self.pad_bottom

    @property
    def y1(self) -> int: return self.pad_top

    def sy(self, v: float) -> float:
        span = (self.ymax - self.ymin) or 1.0
        return self.y0 - (v - self.ymin) / span * (self.y0 - self.y1)

    def sx_linear(self, v: float, lo: float, hi: float) -> float:
        span = (hi - lo) or 1.0
        return self.x0 + (v - lo) / span * (self.x1 - self.x0)

    # -- primitives --------------------------------------------------------
    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def text(self, x: float, y: float, s: str, size: int = 12, anchor: str = "middle",
             fill: str = INK, weight: str = "normal", italic: bool = False) -> None:
        style = f' font-style="italic"' if italic else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
                 f'text-anchor="{anchor}" fill="{fill}" font-weight="{weight}"{style}>'
                 f'{escape(s)}</text>')

    def gridlines(self, ticks: list[float]) -> None:
        for t in ticks:
            y = self.sy(t)
            self.add(f'<line x1="{self.x0}" y1="{y:.1f}" x2="{self.x1}" y2="{y:.1f}" '
                     f'stroke="{GRID}" stroke-width="1"/>')
            self.text(self.x0 - 10, y + 4, _fmt(t), size=11, anchor="end", fill=MUTED)

    def frame(self) -> None:
        self.add(f'<line x1="{self.x0}" y1="{self.y0}" x2="{self.x1}" y2="{self.y0}" '
                 f'stroke="{INK}" stroke-width="1.2"/>')

    def errorbar(self, x: float, lo: float, hi: float, colour: str = INK,
                 cap: float = 5.0, width: float = 1.6) -> None:
        ylo, yhi = self.sy(lo), self.sy(hi)
        self.add(f'<line x1="{x:.1f}" y1="{ylo:.1f}" x2="{x:.1f}" y2="{yhi:.1f}" '
                 f'stroke="{colour}" stroke-width="{width}"/>')
        for y in (ylo, yhi):
            self.add(f'<line x1="{x-cap:.1f}" y1="{y:.1f}" x2="{x+cap:.1f}" y2="{y:.1f}" '
                     f'stroke="{colour}" stroke-width="{width}"/>')

    def legend(self, entries: list[tuple[str, str]], x: float | None = None,
               y: float | None = None) -> None:
        x = self.x0 if x is None else x
        y = self.y1 - 22 if y is None else y
        cx = x
        for label, colour in entries:
            self.add(f'<rect x="{cx:.1f}" y="{y-9:.1f}" width="11" height="11" '
                     f'rx="2" fill="{colour}"/>')
            self.text(cx + 16, y, label, size=11.5, anchor="start", fill=INK)
            cx += 20 + 7.2 * len(label)

    # -- output ------------------------------------------------------------
    def render(self) -> str:
        head = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{self.height}" viewBox="0 0 {self.width} {self.height}" '
            f'font-family="Inter, Helvetica Neue, Helvetica, Arial, sans-serif">',
            f'<rect width="{self.width}" height="{self.height}" fill="#ffffff"/>',
        ]
        if self.title:
            head.append(f'<text x="{self.x0}" y="26" font-size="15.5" font-weight="600" '
                        f'fill="{INK}">{escape(self.title)}</text>')
        if self.subtitle:
            head.append(f'<text x="{self.x0}" y="44" font-size="11.5" '
                        f'fill="{MUTED}">{escape(self.subtitle)}</text>')
        if self.ylabel:
            cy = (self.y0 + self.y1) / 2
            head.append(f'<text x="18" y="{cy:.1f}" font-size="12" fill="{MUTED}" '
                        f'text-anchor="middle" transform="rotate(-90 18 {cy:.1f})">'
                        f'{escape(self.ylabel)}</text>')
        if self.xlabel:
            head.append(f'<text x="{(self.x0+self.x1)/2:.1f}" y="{self.height-16}" '
                        f'font-size="12" fill="{MUTED}" text-anchor="middle">'
                        f'{escape(self.xlabel)}</text>')
        return "\n".join(head + self.parts + ["</svg>"]) + "\n"


def grouped_bars(ax: Axes, categories: list[str], series: list[tuple[str, list[float]]],
                 errors: list[list[tuple[float, float]]] | None = None,
                 annotations: list[str] | None = None) -> None:
    """`series` is [(label, values_per_category), ...]; `errors` matches it as
    [(lo, hi), ...] per category. Error bars are drawn whenever supplied, and
    they are supplied everywhere in this paper — a bare bar for a three-seed
    mean is the figure equivalent of the missing uncertainty layer."""
    n_cat, n_ser = len(categories), len(series)
    band = (ax.x1 - ax.x0) / max(1, n_cat)
    bar_w = min(58.0, band * 0.72 / max(1, n_ser))
    for ci, cat in enumerate(categories):
        centre = ax.x0 + band * (ci + 0.5)
        start = centre - (n_ser * bar_w) / 2
        for si, (label, vals) in enumerate(series):
            v = vals[ci]
            x = start + si * bar_w
            y = ax.sy(v)
            ax.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w-4:.1f}" '
                   f'height="{max(0.0, ax.y0-y):.1f}" fill="{SERIES[si % len(SERIES)]}" '
                   f'rx="2" opacity="0.92"/>')
            if errors:
                lo, hi = errors[si][ci]
                ax.errorbar(x + (bar_w - 4) / 2, lo, hi, colour=INK)
        ax.text(centre, ax.y0 + 20, cat, size=12)
        if annotations and annotations[ci]:
            ax.text(centre, ax.y0 + 38, annotations[ci], size=10.5, fill=MUTED)
    ax.legend([(lab, SERIES[i % len(SERIES)]) for i, (lab, _) in enumerate(series)])


def line(ax: Axes, xs: list[float], ys: list[float], colour: str, label: str = "",
         xlo: float | None = None, xhi: float | None = None, marker: bool = True) -> None:
    xlo = min(xs) if xlo is None else xlo
    xhi = max(xs) if xhi is None else xhi
    pts = [(ax.sx_linear(x, xlo, xhi), ax.sy(y)) for x, y in zip(xs, ys)]
    d = " ".join(("M" if i == 0 else "L") + f"{px:.1f},{py:.1f}"
                 for i, (px, py) in enumerate(pts))
    ax.add(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="2.2" '
           f'stroke-linejoin="round"/>')
    if marker:
        for px, py in pts:
            ax.add(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.1" fill="{colour}"/>')
    if label:
        px, py = pts[-1]
        ax.text(px + 8, py + 4, label, size=11.5, anchor="start", fill=colour)


def xticks_linear(ax: Axes, values: list[float], xlo: float, xhi: float,
                  fmt=_fmt) -> None:
    for v in values:
        x = ax.sx_linear(v, xlo, xhi)
        ax.add(f'<line x1="{x:.1f}" y1="{ax.y0}" x2="{x:.1f}" y2="{ax.y0+5}" '
               f'stroke="{MUTED}" stroke-width="1"/>')
        ax.text(x, ax.y0 + 19, fmt(v), size=11, fill=MUTED)


def hrule(ax: Axes, y: float, label: str = "", colour: str = MUTED,
          dash: str = "4 3") -> None:
    py = ax.sy(y)
    ax.add(f'<line x1="{ax.x0}" y1="{py:.1f}" x2="{ax.x1}" y2="{py:.1f}" '
           f'stroke="{colour}" stroke-width="1.2" stroke-dasharray="{dash}"/>')
    if label:
        ax.text(ax.x1 - 4, py - 6, label, size=10.5, anchor="end", fill=colour)
