"""Utility for visualising Abaqus report files.

The script discovers ``.rpt`` files in a data directory, parses the
tabulated output and generates individual as well as comparative plots.
Figures follow the styling requested by the user:

* Figure size: 8 cm × 6 cm (converted to inches for Matplotlib).
* Fonts: Times New Roman for latin characters and SimSun for Chinese.
* Output format: SVG.

Run the script from the repository root, for example::

    python plot_reports.py --data-dir data_report --output-dir figures

The resulting SVG figures are written to ``figures/`` by default.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties


CM_TO_INCH = 1 / 2.54
FIGURE_SIZE = (8 * CM_TO_INCH, 6 * CM_TO_INCH)


@dataclass
class ReportSeries:
    """Container holding the numeric data extracted from a report."""

    name: str
    x: List[float]
    y: List[float]
    x_label: str
    y_label: str
    title: str

    @property
    def safe_name(self) -> str:
        """Return a filesystem friendly name for the series."""

        return self.name.replace(" ", "_")


def discover_font(family: str) -> FontProperties | None:
    """Return font properties if the requested family exists.

    If the font cannot be found, ``None`` is returned so that callers can fall
    back to a default font.
    """

    try:
        font_path = font_manager.findfont(family, fallback_to_default=False)
    except (ValueError, RuntimeError):
        return None
    return FontProperties(fname=font_path)


def configure_fonts() -> tuple[FontProperties, FontProperties]:
    """Configure Matplotlib defaults and return font properties.

    The function attempts to use SimSun for Chinese text and Times New Roman
    for latin characters.  When SimSun is unavailable on the system the
    function keeps Times New Roman for all text while printing an informative
    message.
    """

    english_font = discover_font("Times New Roman")
    if english_font is None:
        # Fall back to Matplotlib's default font but keep the style consistent.
        english_font = FontProperties()

    chinese_font = discover_font("SimSun")
    if chinese_font is None:
        print(
            "[plot_reports] SimSun font not found on this system. "
            "Falling back to Times New Roman for all text."
        )
        chinese_font = english_font

    plt.rcParams["font.family"] = english_font.get_name()
    plt.rcParams["axes.unicode_minus"] = False

    # Register SimSun as a fallback font when it is present.
    if chinese_font is not english_font:
        plt.rcParams.setdefault("font.sans-serif", [])
        current_sans = list(plt.rcParams["font.sans-serif"])
        if chinese_font.get_name() not in current_sans:
            plt.rcParams["font.sans-serif"] = [
                chinese_font.get_name(),
                *current_sans,
            ]

    return english_font, chinese_font


def is_data_line(tokens: List[str]) -> bool:
    """Return ``True`` if the tokens represent numeric data."""

    if len(tokens) < 2:
        return False
    try:
        for value in tokens[:2]:
            float(value)
    except ValueError:
        return False
    return True


def load_report(path: Path) -> ReportSeries:
    """Parse a two-column Abaqus ``.rpt`` file into a :class:`ReportSeries`."""

    header: List[str] = []
    x_values: List[float] = []
    y_values: List[float] = []
    x_label = "X"
    y_label = "Y"

    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            tokens = line.split()
            if is_data_line(tokens):
                x_values.append(float(tokens[0]))
                y_values.append(float(tokens[1]))
            else:
                header.append(line)
                if len(tokens) >= 2:
                    x_label = tokens[0]
                    y_label = tokens[1]

    title = header[0] if header else path.stem
    name = path.stem
    return ReportSeries(name=name, x=x_values, y=y_values, x_label=x_label, y_label=y_label, title=title)


def plot_series(series: ReportSeries, output_dir: Path, fonts: tuple[FontProperties, FontProperties]) -> None:
    """Create an individual plot for a single data series."""

    english_font, chinese_font = fonts
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)
    ax.plot(series.x, series.y, linewidth=1.2, marker="o", markersize=2.4, label=series.title)
    ax.set_xlabel(series.x_label, fontproperties=english_font)
    ax.set_ylabel(series.y_label, fontproperties=english_font)
    ax.set_title(series.title, fontproperties=english_font, fontsize=10)
    ax.grid(True, linewidth=0.4, linestyle="--", alpha=0.5)

    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(english_font)

    legend = ax.legend(loc="best", frameon=False, prop=english_font)
    if legend is not None:
        for text in legend.get_texts():
            text.set_fontproperties(chinese_font)

    fig.tight_layout()
    output_path = output_dir / f"{series.safe_name}.svg"
    fig.savefig(output_path, format="svg")
    plt.close(fig)


def plot_group(
    series_list: Iterable[ReportSeries],
    output_path: Path,
    fonts: tuple[FontProperties, FontProperties],
    title: str,
) -> None:
    """Plot multiple series together for comparison."""

    english_font, chinese_font = fonts
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    for series in series_list:
        linewidth = 1.4 if "base" in series.name.lower() else 1.0
        ax.plot(series.x, series.y, label=series.name, linewidth=linewidth)

    reference_series = next(iter(series_list))
    ax.set_xlabel(reference_series.x_label, fontproperties=english_font)
    ax.set_ylabel(reference_series.y_label, fontproperties=english_font)
    ax.set_title(title, fontproperties=english_font, fontsize=10)
    ax.grid(True, linewidth=0.4, linestyle="--", alpha=0.5)

    legend = ax.legend(loc="best", frameon=False)
    if legend is not None:
        for text in legend.get_texts():
            text.set_fontproperties(chinese_font)

    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(english_font)

    fig.tight_layout()
    fig.savefig(output_path, format="svg")
    plt.close(fig)


def collect_series(data_dir: Path) -> List[ReportSeries]:
    """Load all ``.rpt`` files from ``data_dir``."""

    series_collection: List[ReportSeries] = []
    for path in sorted(data_dir.glob("*.rpt")):
        series_collection.append(load_report(path))
    if not series_collection:
        raise FileNotFoundError(f"No .rpt files found in {data_dir}")
    return series_collection


def group_series(series_collection: Iterable[ReportSeries]) -> dict[str, List[ReportSeries]]:
    """Group report series using the file name prefix before the first dash."""

    grouped: dict[str, List[ReportSeries]] = {}
    for series in series_collection:
        group_key = series.name.split("-")[0]
        grouped.setdefault(group_key, []).append(series)
    return grouped


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Abaqus .rpt files as SVG figures.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data_report"),
        help="Directory that contains the .rpt files (default: data_report)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("figures"),
        help="Directory where SVG figures are written (default: figures)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    data_dir: Path = args.data_dir
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    fonts = configure_fonts()

    series_collection = collect_series(data_dir)
    for series in series_collection:
        plot_series(series, output_dir, fonts)

    group_map = group_series(series_collection)
    for group_name, group_series_list in group_map.items():
        if len(group_series_list) <= 1:
            continue
        output_path = output_dir / f"comparison_{group_name}.svg"
        title = f"Comparison – {group_name}"
        plot_group(group_series_list, output_path, fonts, title)

    if len(series_collection) > 1:
        output_path = output_dir / "comparison_all.svg"
        plot_group(series_collection, output_path, fonts, "All Series Comparison")


if __name__ == "__main__":
    main()
