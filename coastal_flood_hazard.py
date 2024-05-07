#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created in February 2024

description: Make coastal flood hazard layer 

@author: simonameiler
"""

import os
import numpy as np
import rasterio
from rasterio.merge import merge
from scipy import sparse

from climada.hazard import Hazard
from climada.hazard.centroids.centr import Centroids

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

# def generate_hazard_object(tiles, root_dir, selected_rcp, selected_year, HAZ_TYPE):
#     """
#     Generate a combined hazard object from raster files for the specified tiles and RCP/year combination,
#     by first creating a hazard object for each tile, then concatenating.

#     Args:
#     - tiles (list of str): List of tile identifiers.
#     - root_dir (str): The root directory containing the flood map data.
#     - selected_rcp (str): The RCP scenario to use.
#     - selected_year (str): The year to use.
#     - HAZ_TYPE (str): The type of hazard.

#     Returns:
#     - Combined Hazard object for the specified RCP/year across all tiles.
#     """
#     hazards = []
#     for tile in tiles:
#         tile_path = os.path.join(root_dir, tile, f"{selected_rcp}_{selected_year}")
#         # Check if the tile directory exists before processing
#         if os.path.exists(tile_path):
#             haz_files = [os.path.join(tile_path, file) for file in os.listdir(tile_path) if file.endswith('.tif')]
#             # Ensure there are files to process
#             if not haz_files:
#                 continue

#             rp_values = [int(file.split('RP')[-1].replace('.tif', '')) for file in haz_files]
#             rp_values_sorted, haz_files_sorted = zip(*sorted(zip(rp_values, haz_files)))

#             # Create Hazard object for the current tile
#             haz = Hazard.from_raster(
#                 haz_type=HAZ_TYPE, 
#                 files_intensity=list(haz_files_sorted), 
#                 src_crs='EPSG:4326',
#                 attrs={
#                     'unit': 'm', 
#                     'event_id': np.arange(len(haz_files_sorted)), 
#                     'frequency': 1 / np.array(rp_values_sorted)
#                 }
#             )
#             haz.centroids.set_meta_to_lat_lon()
#             hazards.append(haz)
#         #else:
#         #    print(f"Tile directory {tile_path} not found, skipping...")

#     # Concatenate all Hazard objects into a single combined Hazard object, if any were created
#     if hazards:
#         combined_hazard = Hazard.concat(hazards)
#         return combined_hazard
#     else:
#         print("No hazard files found for the specified tiles and RCP/year combination.")
#         return None

def get_coordinates_from_transform(width, height, transform):
    """
    Generate geographic coordinates (longitude, latitude) for the center of each pixel in a raster,
    given the raster dimensions and an affine transformation. This function calculates the geographic
    center coordinates for every pixel defined by the raster dimensions (width and height) and applies
    the provided affine transformation to convert from pixel coordinates to geographic coordinates.

    Args:
    - width (int): The width of the raster in pixels. This specifies the number of columns in the raster.
    - height (int): The height of the raster in pixels. This specifies the number of rows in the raster.
    - transform (Affine): An affine transformation matrix that provides the parameters necessary to convert
      pixel coordinates to geographic coordinates. The transform should include six coefficients:
      (a, b, c, d, e, f), which are used to convert pixel coordinates (col, row) to geographic coordinates (x, y).

    Returns:
    - tuple of lists: (lat_list, lon_list)
      - lat_list (list of float): A list of latitude coordinates for the center of each pixel.
      - lon_list (list of float): A list of longitude coordinates for the center of each pixel.

    Each returned list has a length equal to the total number of pixels in the raster (width * height),
    with each entry corresponding to the latitude or longitude of the center of a pixel.
    """
    lat_list = []
    lon_list = []
    for row in range(height):
        for col in range(width):
            # Calculate the top-left corner of the pixel
            x, y = transform * (col, row)
            # Adjust to get the center of the pixel
            x_center = x + transform.a / 2
            y_center = y + transform.e / 2
            lat_list.append(x_center)
            lon_list.append(y_center)

    return lat_list, lon_list

def generate_hazard_object(tiles, root_dir, selected_rcp, selected_year, HAZ_TYPE):
    """
    Generate a combined hazard object from raster files for the specified tiles and RCP/year combination,
    by first creating a hazard object for each tile, then concatenating.

    Args:
    - tiles (list of str): List of tile identifiers.
    - root_dir (str): The root directory containing the flood map data.
    - selected_rcp (str): The RCP scenario to use.
    - selected_year (str): The year to use.
    - HAZ_TYPE (str): The type of hazard (assuming 'TC' for this example).

    Returns:
    - Combined Hazard object for the specified RCP/year across all tiles.
    """
    rp_dict = {}
    for tile in tiles:
        tile_path = os.path.join(root_dir, tile, f"{selected_rcp}_{selected_year}")
        if os.path.exists(tile_path):
            haz_files = [os.path.join(tile_path, file) for file in os.listdir(tile_path) if file.endswith('.tif')]
            for file in haz_files:
                rp_value = int(file.split('RP')[-1].replace('.tif', ''))
                if rp_value not in rp_dict:
                    rp_dict[rp_value] = []
                rp_dict[rp_value].append(file)
    
    # Now merge files horizontally for each rp_value
    intensity_arrays = []
    return_periods = sorted(rp_dict.keys())
    for rp in return_periods:
        files = rp_dict[rp]
        sources = [rasterio.open(file) for file in files]
        merged_raster, out_transform = merge(sources, method='max')
        # Convert the merged raster data to an array and store it for stacking
        intensity_arrays.append(merged_raster[0])
        for src in sources:
            src.close()
    
    # Stack arrays vertically and convert to sparse matrix
    intensity_matrix = np.vstack(intensity_arrays)
    intensity_sparse = sparse.csr_matrix(intensity_matrix)
    
    lat, lon = get_coordinates_from_transform(merged_raster[0][0].size, merged_raster[0][1].size, out_transform)
    centroids = Centroids(lat=np.unique(lat), lon=np.unique(lon), crs='EPSG:4326')    

    # Create the Hazard object
    hazard = Hazard(
        haz_type=HAZ_TYPE,
        units='m',
        event_id=np.arange(len(return_periods)),
        event_name=np.array(return_periods, dtype=str),
        centroids=centroids,
        date=np.array(return_periods, dtype=int),  # Placeholder for actual dates
        intensity=intensity_sparse,
        frequency=1 / np.array(return_periods, dtype=float)
    )

    return hazard