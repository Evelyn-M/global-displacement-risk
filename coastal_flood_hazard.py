#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created in February 2024

description: Make flood hazard layer 

@author: simonameiler
"""

import os
import numpy as np

from climada.hazard import Hazard
from climada.entity import ImpactFunc, ImpactFuncSet, LitPop
from climada.engine import ImpactCalc
from climada.util.constants import SYSTEM_DIR

def generate_flood_map_list(root_dir):
    """
    Generate a list of file paths for each RCP/year/RP combination within the given directory.

    Args:
    - root_dir (str): The root directory containing the flood map data.

    Returns:
    - dict: A nested dictionary with RCP, year, and RP as keys, leading to lists of file paths.
    """
    flood_maps = {}
    # Walk through the directory structure
    for root, dirs, files in os.walk(root_dir):
        # Filter out the relevant directories and files based on naming conventions
        for file in files:
            if file.endswith('.tif'):
                # Extract details from the folder and file names
                path_parts = root.split(os.sep)
                # Assuming the structure is always consistent and the relevant parts are always present
                rcp_year = path_parts[-1]
                rcp, year = rcp_year.split('_')
                rp = file.replace('.tif', '').upper()
                
                # Initialize the dictionary structure if necessary
                if rcp not in flood_maps:
                    flood_maps[rcp] = {}
                if year not in flood_maps[rcp]:
                    flood_maps[rcp][year] = {}
                if rp not in flood_maps[rcp][year]:
                    flood_maps[rcp][year][rp] = []

                # Add the file path to the list
                flood_maps[rcp][year][rp].append(os.path.join(root, file))
    
    return flood_maps

def process_and_combine_by_combination(file_dict, selected_rcp=None, selected_year=None, selected_rp=None):
    """
    Processes and combines coastal flood hazard tiles into single Hazard objects for each specified 
    RCP, year, and RP combination. If no specific RCP, year, or RP is provided, it processes all available 
    combinations within the provided file dictionary.
    
    Parameters:
    - file_dict (dict): A nested dictionary with structure {rcp: {year: {rp: [file_paths]}}} containing 
      paths to raster files for each RCP, year, and RP combination.
    - selected_rcp (str or list of str, optional): A specific RCP or list of RCPs to process. If None, 
      all RCPs in the file_dict are processed.
    - selected_year (str or list of str, optional): A specific year or list of years to process. If None, 
      all years in the file_dict for the selected RCPs are processed.
    - selected_rp (str or list of str, optional): A specific return period or list of return periods to 
      process. If None, all RPs in the file_dict for the selected RCPs and years are processed.
    
    Returns:
    - dict: A nested dictionary with the same structure as the input file_dict, where each list of file 
      paths is replaced with a combined Hazard object for that RCP, year, and RP combination.
    """
    combined_hazards = {}
    for rcp, years in file_dict.items():
        if selected_rcp and rcp not in np.atleast_1d(selected_rcp):
            continue
        combined_hazards[rcp] = {}

        for year, rps in years.items():
            if selected_year and year not in np.atleast_1d(selected_year):
                continue
            combined_hazards[rcp][year] = {}

            for rp, files in rps.items():
                if selected_rp and rp not in np.atleast_1d(selected_rp):
                    continue
                hazards = []
                for file_path in files:
                    hazard = Hazard.from_raster(file_path, haz_type='FL')
                    hazard.units = 'm'
                    hazard.centroids.set_meta_to_lat_lon()
                    hazards.append(hazard)
                
                combined_hazard = Hazard.concat(hazards)
                combined_hazards[rcp][year][rp] = combined_hazard

    return combined_hazards


# Usage example
hazard_dir = SYSTEM_DIR/"hazard"/"coastal_flood"
root_directory = hazard_dir/"Somalia_1k"
flood_map_files = generate_flood_map_list(root_directory)

combined_hazards = process_and_combine_by_combination(flood_map_files, selected_rcp='RCP85', selected_year='2050', selected_rp='RP100')

coastal_flood = combined_hazards['RCP85']['2050']['RP100']


#%% load GHSL exp and perform quick impact calculation

os.chdir('/Users/simonameiler/Documents/WCR/Displacement/global-displacement-risk') # change back to root folder, not "~/doc"
import exposure

cntry_name = 'Somalia'

# import exposure from GHSL
exp_ghsl = exposure.exp_from_ghsl(cntry_name)

# get centroids from exp_ghsl
cent_som = exp_ghsl.gdf.centroid

# get step function
inten = (0, 0.5, 10)
imp_fun = ImpactFunc.from_step_impf(intensity=inten, haz_type='FL', impf_id=1)

impfuncSet = ImpactFuncSet([imp_fun])
#impfuncSet.append(imp_fun)

# Get the hazard type and hazard id
[haz_type] = impfuncSet.get_hazard_types()
[haz_id] = impfuncSet.get_ids()[haz_type]
# Exposures: rename column and assign id
exp_ghsl.gdf.rename(columns={"impf_": "impf_" + haz_type}, inplace=True)
exp_ghsl.gdf['impf_' + haz_type] = haz_id

# calc impact
impact = ImpactCalc(exp_ghsl, impfuncSet, coastal_flood).impact(save_mat=True)

