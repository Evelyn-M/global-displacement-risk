#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created in February 2024

description: Make coastal flood hazard layer 

@author: simonameiler
"""

import os
import numpy as np

from climada.hazard import Hazard

def find_tiles(lat_min, lat_max, lon_min, lon_max):
    """
    Find all the latitude-longitude tile names that cover the specified extent.

    Parameters:
    - lat_min: Minimum latitude of the extent
    - lat_max: Maximum latitude of the extent
    - lon_min: Minimum longitude of the extent
    - lon_max: Maximum longitude of the extent

    Returns:
    - List of tile names covering the specified extent.
    """
    tile_names = []

    # Convert lat and lon to integers and adjust ranges for iteration
    lat_start = int(lat_min) - (1 if lat_min < -1 else 0)
    lat_end = int(lat_max) + (1 if lat_max % 1 != 0 else 0)
    lon_start = int(lon_min)
    lon_end = int(lon_max) + (1 if lon_max % 1 != 0 else 0)

    for lat in range(lat_start, lat_end):
        for lon in range(lon_start, lon_end):
            # Determine latitude direction and format
            lat_dir = 'N' if lat >= 0 else 'S'
            lat_name = f"{abs(lat):02d}"

            # Determine longitude direction and format
            lon_dir = 'E' if lon >= 0 else 'W'
            lon_name = f"{abs(lon):03d}"

            # Construct tile name and add to the list
            tile_name = f"{lat_dir}{lat_name}{lon_dir}{lon_name}"
            tile_names.append(tile_name)

    return tile_names

def generate_hazard_object(tiles, root_dir, selected_rcp, selected_year, HAZ_TYPE):
    """
    Generate a combined hazard object from raster files for the specified tiles and RCP/year combination,
    by first creating a hazard object for each tile, then concatenating.

    Args:
    - tiles (list of str): List of tile identifiers.
    - root_dir (str): The root directory containing the flood map data.
    - selected_rcp (str): The RCP scenario to use.
    - selected_year (str): The year to use.
    - HAZ_TYPE (str): The type of hazard.

    Returns:
    - Combined Hazard object for the specified RCP/year across all tiles.
    """
    hazards = []
    for tile in tiles:
        tile_path = os.path.join(root_dir, tile, f"{selected_rcp}_{selected_year}")
        # Check if the tile directory exists before processing
        if os.path.exists(tile_path):
            haz_files = [os.path.join(tile_path, file) for file in os.listdir(tile_path) if file.endswith('.tif')]
            # Ensure there are files to process
            if not haz_files:
                continue

            rp_values = [int(file.split('RP')[-1].replace('.tif', '')) for file in haz_files]
            rp_values_sorted, haz_files_sorted = zip(*sorted(zip(rp_values, haz_files)))

            # Create Hazard object for the current tile
            haz = Hazard.from_raster(
                haz_type=HAZ_TYPE, 
                files_intensity=list(haz_files_sorted), 
                src_crs='EPSG:4326',
                attrs={
                    'unit': 'm', 
                    'event_id': np.arange(len(haz_files_sorted)), 
                    'frequency': 1 / np.array(rp_values_sorted)
                }
            )
            haz.centroids.set_meta_to_lat_lon()
            hazards.append(haz)
        #else:
        #    print(f"Tile directory {tile_path} not found, skipping...")

    # Concatenate all Hazard objects into a single combined Hazard object, if any were created
    if hazards:
        combined_hazard = Hazard.concat(hazards)
        return combined_hazard
    else:
        print("No hazard files found for the specified tiles and RCP/year combination.")
        return None

