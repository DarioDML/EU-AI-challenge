"""Regenerate the four reference charts and, with --include-map, the fifth map."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter


REPO = Path(__file__).resolve().parents[1]
REFERENCE = REPO / "data" / "reference"
OUTPUT = REPO / "figures" / "generated"
BLUE, TEAL, ORANGE, GRAY = "#164b71", "#167d8d", "#dc8437", "#aeb9c6"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "savefig.facecolor": "white",
    }
)


def save(fig, name: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "svg"):
        fig.savefig(OUTPUT / f"{name}.{suffix}", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Created {OUTPUT / name}.png/.svg")


def charts(metrics: pd.DataFrame) -> None:
    by_id = metrics.set_index("aoi_id")
    chosen = by_id.loc[["de_15", "de_18", "de_07"]]
    names = ["Bad Neuenahr-Ahrweiler", "Schleiden", "Erftstadt"]
    y = np.arange(3)

    fig, ax = plt.subplots(figsize=(10.5, 4.3))
    ax.barh(y - .18, chosen.residential_water_only, .32, color=BLUE, label="Water only")
    ax.barh(y + .18, chosen.residential_event, .32, color=ORANGE, label="Water plus flood traces")
    for i, (_, row) in enumerate(chosen.iterrows()):
        for offset, key in ((-.18, "residential_water_only"), (.18, "residential_event")):
            ax.text(row[key] + 80, i + offset, f"{int(row[key]):,}", va="center", fontsize=10)
    ax.set_yticks(y, names)
    ax.invert_yaxis()
    ax.set_xlim(0, 8000)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
    ax.set_xlabel("Residential-labelled OBAT building points intersecting the event evidence")
    ax.set_title("Flood traces change the exposure result")
    ax.legend(loc="lower right", frameon=False)
    fig.text(.015, -.03, "Source: supplied EMS products and OBAT 2020. Union across supplied dates in each AOI; exposure, not damage or households.", fontsize=9, color="#48505b")
    fig.tight_layout()
    save(fig, "01_water_and_traces")

    selected = by_id.loc[["de_15", "be_01", "nl_01", "de_07"]]
    labels = ["Bad Neuenahr-Ahrweiler", "Liege AOI", "Venlo AOI", "Erftstadt"]
    y = np.arange(4)
    fig, ax = plt.subplots(figsize=(10.5, 4.7))
    ax.barh(y - .18, selected.pop2020_fractional, .32, color=TEAL, label="Fractional cell weighting")
    ax.barh(y + .18, selected.pop2020_all_touched, .32, color=GRAY, label="Whole touched-cell total")
    for i, (_, row) in enumerate(selected.iterrows()):
        ax.text(row.pop2020_fractional + 500, i - .18, f"{row.pop2020_fractional:,.0f}", va="center", fontsize=9)
        ax.text(row.pop2020_all_touched + 500, i + .18, f"{row.pop2020_all_touched:,.0f}", va="center", fontsize=9)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 62000)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
    ax.set_xlabel("Residents allocated to the event envelope under two assumptions")
    ax.set_title("Whole-cell counting can dominate the population estimate")
    ax.legend(frameon=False, loc="lower right")
    fig.text(.015, -.03, "Source: GHS-POP 2020 and EMS water plus trace unions. Fractional weighting assumes uniform residents within each cell.", fontsize=9, color="#48505b")
    fig.tight_layout()
    save(fig, "02_population_method")

    y = np.arange(3)
    area = 100 * chosen.rp500_positive_fraction
    points = 100 * chosen.rp500_positive_residential / chosen.residential_event
    fig, ax = plt.subplots(figsize=(10.5, 4.4))
    ax.barh(y - .18, area, .32, color=GRAY, label="Share of event area")
    ax.barh(y + .18, points, .32, color=TEAL, label="Share of exposed residential points")
    for i, (area_value, point_value) in enumerate(zip(area, points)):
        ax.text(area_value + 1, i - .18, f"{area_value:.1f}%", va="center")
        ax.text(point_value + 1, i + .18, f"{point_value:.1f}%", va="center")
    ax.set_yticks(y, names)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Overlap with positive values in the supplied RP500 raster")
    ax.set_title("Area overlap and building overlap answer different questions")
    ax.legend(frameon=False, loc="lower right")
    fig.text(.015, -.03, "No positive value is not proof of safety, lack of model coverage, or model failure. The two bars have different denominators.", fontsize=9, color="#48505b")
    fig.tight_layout()
    save(fig, "03_overlap_denominators")

    selected = by_id.loc[["de_15", "de_18", "de_07", "be_01"]]
    y = np.arange(4)
    low = 100 * selected["residential_buffer_-10m"] / selected.residential_event
    high = 100 * selected["residential_buffer_10m"] / selected.residential_event
    fig, ax = plt.subplots(figsize=(10.5, 4.3))
    ax.hlines(y, low, high, color=TEAL, linewidth=6, alpha=.65)
    ax.scatter([100] * 4, y, color=BLUE, s=55, zorder=3)
    ax.axvline(100, color="#555", linewidth=.8, linestyle="--")
    for i, (low_value, high_value) in enumerate(zip(low, high)):
        ax.text(high_value + 3, i, f"{low_value:.0f}-{high_value:.0f}% of baseline", va="center", fontsize=10)
    ax.set_yticks(y, ["Bad Neuenahr-Ahrweiler", "Schleiden", "Erftstadt", "Liege AOI"])
    ax.invert_yaxis()
    ax.set_xlim(0, 250)
    ax.set_xlabel("Residential point exposure relative to the unmodified envelope (100%)")
    ax.set_title("A 10 m boundary change matters much more in some AOIs")
    fig.text(.015, -.03, "Geometric erosion/dilation sensitivity, clipped to AOI. These intervals are not statistical confidence intervals.", fontsize=9, color="#48505b")
    fig.tight_layout()
    save(fig, "04_boundary_sensitivity")


def event_map() -> None:
    import geopandas as gpd
    import rasterio
    from matplotlib.patches import Patch
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    from rasterio.windows import from_bounds

    source_root = Path(
        os.environ.get("CHALLENGE_DATA_ROOT", REPO / "data" / "raw" / "working_data")
    ).expanduser()
    raster_path = source_root / "cems-efas" / "Europe_RP500_filled_depth.tif"
    if not raster_path.is_file():
        raise SystemExit(f"Map needs the RP500 raster. See data/README.md. Missing: {raster_path}")
    unions = gpd.read_parquet(REFERENCE / "aoi_event_unions.parquet")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    with rasterio.open(raster_path) as raster:
        for ax, aid, label in zip(
            axes,
            ("de_15", "de_18"),
            ("Bad Neuenahr-Ahrweiler AOI", "Schleiden AOI"),
        ):
            event = unions.loc[unions.aoi_id.eq(aid) & unions.kind.eq("event"), "geometry"].iloc[0]
            water = unions.loc[unions.aoi_id.eq(aid) & unions.kind.eq("water"), "geometry"].iloc[0]
            box = gpd.GeoSeries([event.envelope.buffer(900)], crs=3035)
            bounds = box.total_bounds
            native = box.to_crs(raster.crs).total_bounds
            window = from_bounds(*native, raster.transform).round_offsets().round_lengths()
            source_values = raster.read(1, window=window)
            resolution = 70
            width = int(np.ceil((bounds[2] - bounds[0]) / resolution))
            height = int(np.ceil((bounds[3] - bounds[1]) / resolution))
            display = np.zeros((height, width), dtype=np.uint8)
            transform = from_origin(bounds[0], bounds[3], resolution, resolution)
            reproject(
                (source_values > 0).astype("uint8"),
                display,
                src_transform=raster.window_transform(window),
                src_crs=raster.crs,
                dst_transform=transform,
                dst_crs="EPSG:3035",
                resampling=Resampling.nearest,
            )
            ax.imshow(
                np.ma.masked_equal(display, 0),
                extent=[bounds[0], bounds[0] + width * resolution, bounds[3] - height * resolution, bounds[3]],
                cmap=matplotlib.colors.ListedColormap(["#bfcbd6"]),
                vmin=1,
                vmax=1,
                origin="upper",
                interpolation="nearest",
            )
            gpd.GeoSeries([event.difference(water)], crs=3035).plot(ax=ax, color=ORANGE, edgecolor="none")
            gpd.GeoSeries([water], crs=3035).plot(ax=ax, color=BLUE, edgecolor="none")
            ax.set_xlim(bounds[[0, 2]])
            ax.set_ylim(bounds[[1, 3]])
            ax.set_aspect("equal")
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(label, fontsize=12)
            ax.set_facecolor("#f7f8fa")
            x = bounds[0] + .07 * (bounds[2] - bounds[0])
            y = bounds[1] + .08 * (bounds[3] - bounds[1])
            ax.plot([x, x + 2000], [y, y], color="#263541", lw=3)
            ax.text(x + 1000, y + .02 * (bounds[3] - bounds[1]), "2 km", ha="center", fontsize=9)
            ax.annotate("N", xy=(.94, .93), xytext=(.94, .78), xycoords="axes fraction", ha="center", arrowprops=dict(arrowstyle="->", color="#263541"))
    fig.legend(
        handles=[
            Patch(color=BLUE, label="Observed water"),
            Patch(color=ORANGE, label="Flood trace beyond water"),
            Patch(color="#bfcbd6", label="Positive RP500 cells"),
        ],
        loc="lower center",
        bbox_to_anchor=(.5, -.02),
        ncol=3,
        frameon=False,
    )
    fig.suptitle("Read water and flood traces as distinct event evidence", fontsize=16, fontweight="bold")
    fig.text(
        .02, -.07,
        "Supplied observation unions, EPSG:3035. Blank background has no positive hazard value; it is not a safe-area classification.\n"
        "Hazard raster reprojected for display only; all calculations use its native grid. Map panels have different extents.",
        fontsize=9, color="#48505b",
    )
    fig.tight_layout(rect=[0, .03, 1, .93])
    save(fig, "05_event_maps")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-map", action="store_true", help="Also draw map 05 using local RP500 raster")
    args = parser.parse_args()
    charts(pd.read_csv(REFERENCE / "aoi_metrics.csv"))
    if args.include_map:
        event_map()


if __name__ == "__main__":
    main()
