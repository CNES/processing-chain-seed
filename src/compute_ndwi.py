#!/usr/bin/env python3
"""Computes the NDWI (Normalized Difference Water Index, McFeeters 1996)
from two Sentinel-2 bands (green B03 and near-infrared B08) in GeoTIFF
format, used to delineate water surfaces (e.g. lake outline).

NDWI = (GREEN - NIR) / (GREEN + NIR)
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import zipfile

import numpy as np
import rasterio
from rasterio.warp import transform_bounds

STAC_VERSION = "1.1.0"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Compute NDWI from a Sentinel-2 L2A ZIP product")
    parser.add_argument("--product",
                        required=True,
                        help="Sentinel-2 L2A ZIP product")
    parser.add_argument("--output", required=True,
                        help="Directory for the generated NDWI and STAC Item files")
    parser.add_argument("--config", required=True,
                        help="JSON configuration file")
    return parser.parse_args(argv)


def load_config(config_path: str) -> dict:
    with open(config_path, encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict) or not isinstance(config.get("driver"), str):
        raise ValueError("Configuration must define a string 'driver'")
    return config


def extract_bands(product_path: str, extract_dir: str) -> tuple[str, str]:
    with zipfile.ZipFile(product_path) as product:
        band_members = {
            "green": [member for member in product.namelist()
                      if member.lower().endswith("_b3.tif")],
            "nir": [member for member in product.namelist()
                    if member.lower().endswith("_b8.tif")],
        }
        missing = [band for band, members in band_members.items()
                   if not members]
        if missing:
            raise ValueError(
                f"Product does not contain required band(s): {', '.join(missing)}")

        extracted_paths = {}
        for band, members in band_members.items():
            member = sorted(members)[0]
            target = Path(extract_dir) / f"{band}.tif"
            with product.open(member) as source, target.open("wb") as destination:
                destination.write(source.read())
            extracted_paths[band] = str(target)

    return extracted_paths["green"], extracted_paths["nir"]


def compute_ndwi(green_path: str, nir_path: str, output_path: str,
                 driver: str = "GTiff") -> None:
    with rasterio.open(green_path) as green_src, rasterio.open(nir_path) as nir_src:
        if green_src.shape != nir_src.shape:
            raise ValueError(
                f"Green band {green_src.shape} and nir band {nir_src.shape} have different shapes"
            )

        profile = green_src.profile
        profile.update(driver=driver, dtype="float32", count=1, nodata=0)

        with rasterio.open(output_path, "w", **profile) as dst:
            for _, window in green_src.block_windows(1):
                green = green_src.read(1, window=window).astype("float32")
                nir = nir_src.read(1, window=window).astype("float32")
                denominator = green + nir
                np.divide(green - nir, denominator, out=green,
                          where=denominator != 0)
                green[denominator == 0] = 0
                dst.write(green, 1, window=window)


def build_stac_item(ndwi_path: str, product_path: str, item_id: str) -> dict:
    with rasterio.open(ndwi_path) as ndwi_src:
        bbox = transform_bounds(ndwi_src.crs, "EPSG:4326", *ndwi_src.bounds)
        west, south, east, north = bbox
        geometry = {
            "type": "Polygon",
            "coordinates": [[
                [west, south],
                [east, south],
                [east, north],
                [west, north],
                [west, south],
            ]],
        }
        epsg_code = ndwi_src.crs.to_epsg() if ndwi_src.crs else None

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "type": "Feature",
        "stac_version": STAC_VERSION,
        "stac_extensions": [
            "https://stac-extensions.github.io/processing/v1.2.0/schema.json",
            "https://stac-extensions.github.io/projection/v2.0.0/schema.json",
        ],
        "id": item_id,
        "geometry": geometry,
        "bbox": list(bbox),
        "properties": {
            "datetime": now,
            "processing:datetime": now,
            "processing:lineage": f"NDWI computed from {Path(product_path).name}",
            "processing:facility": "processing-chain-example",
            "proj:code": f"EPSG:{epsg_code}" if epsg_code else None,
        },
        "links": [],
        "assets": {
            "ndwi": {
                "href": Path(ndwi_path).name,
                "type": "image/tiff; application=geotiff",
                "title": "NDWI",
                "roles": ["data"],
            }
        },
    }


def output_paths(product_path: str, output_dir: str) -> tuple[Path, Path]:
    output_name = Path(product_path).stem.replace("L2A", "L2B")
    ndwi_path = Path(output_dir) / f"{output_name}.tif"
    return ndwi_path, ndwi_path.with_suffix(".json")


def main(argv=None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    ndwi_output, stac_output = output_paths(args.product, args.output)
    with tempfile.TemporaryDirectory() as extract_dir:
        green_path, nir_path = extract_bands(args.product, extract_dir)
        compute_ndwi(green_path, nir_path, str(ndwi_output), config["driver"])

    item_id = ndwi_output.stem
    stac_item = build_stac_item(str(ndwi_output), args.product, item_id)
    with open(stac_output, "w", encoding="utf-8") as stac_file:
        json.dump(stac_item, stac_file, indent=2)

    print(f"NDWI generated: {ndwi_output}")
    print(f"STAC item generated: {stac_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
