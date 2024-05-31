"""
End-to-end computation chain for displacement risk from coastal flood, per country, rcp and reference year.
To be called by bash script on cluster.
"""

# =============================================================================
# Function definitions and package loading here
# =============================================================================

import copy
import numpy as np
import os
from pathlib import Path
import pandas as pd
import sys

from climada.hazard import TropCyclone, Hazard
from climada.entity.exposures import Exposures
from climada.engine import ImpactCalc

os.chdir('/cluster/project/climate/evelynm/global-displacement-risk') 
import exposure
import vulnerability
import impact_postproc
import coastal_flood_hazard

# Constants
PATH_CF_TILES = Path('/cluster/work/climate/evelynm/IDMC_UNU/hazard/coastal_flood/venDEM_scaled_1km')
PATH_RESULTS = Path('/cluster/work/climate/evelynm/IDMC_UNU/results/risk_cf')
DMG_THRESHS = {'low' : 0.3, 'med' : 0.5, 'high': 0.7}


# =============================================================================
# Execution
# =============================================================================
if __name__ == '__main__': 
    cntry_iso = sys.argv[1]
    rcp = sys.argv[2]
    ref_year = sys.argv[3]
    path_save = PATH_RESULTS / cntry_iso
    
    if not path_save.is_dir():
        os.mkdir(path_save)
    
    # for logging purposes
    print(cntry_iso, rcp, ref_year)
    
    # load bem, make exp
    gdf_bem_subcomps = exposure.gdf_from_bem_subcomps(cntry_iso, opt='full')
    gdf_bem_subcomps = gdf_bem_subcomps[gdf_bem_subcomps.valhum>1] # filter out rows with basically no population
    gdf_bem_subcomps = exposure.assign_admin1_attr(gdf_bem_subcomps, exposure.path_admin1_attrs, source='gadm')
    
    exp = Exposures(gdf_bem_subcomps.copy())
    exp.value_unit = 'building_unit'
    exp.gdf['longitude'] = exp.gdf.geometry.x
    exp.gdf['latitude'] = exp.gdf.geometry.y
    exp.gdf['value'] = 1
    
    # load hazard
    tiles = coastal_flood_hazard.find_tiles(
        exp.gdf['latitude'].min(), exp.gdf['latitude'].max(), exp.gdf['longitude'].min(), exp.gdf['longitude'].max())
    CF = coastal_flood_hazard.generate_hazard_object(tiles, PATH_CF_TILES, rcp, ref_year, 'FL')
    rps = 1/CF.frequency[:7]
    
    # compute physical impact and save for future postproc
    dict_imp_bldg = {}
    dict_bools_displ = {}
    dict_df_imps_admin1 = {}
    
    # scenario 1: capra/cima impfs
    try:
        exp.gdf['impf_FL'] = exp.gdf['se_seismo'].map(vulnerability.DICT_PAGER_FLIMPF_CIMA)
        dict_imp_bldg['cima'] = ImpactCalc(exp, vulnerability.IMPF_SET_FL_CIMA, CF).impact(save_mat=True)
        dict_bools_displ['cima'] = {}
        dict_df_imps_admin1['cima'] = {}

    except:
        print('Missing building types in cima-impf')
    
    # scenario 2: ivm impfs
    try:
        exp.gdf['impf_FL'] = exp.gdf['se_seismo'].map(vulnerability.DICT_PAGER_FLIMPF_IVM)
        dict_imp_bldg['ivm'] = ImpactCalc(exp, vulnerability.IMPF_SET_FL_IVM, CF).impact(save_mat=True)
        dict_bools_displ['ivm'] = {}
        dict_df_imps_admin1['ivm'] = {}
    except:
        print('Missing building types in ivm-impf')
    
    # displacement postprocessing (thresholds)
    for source in dict_imp_bldg.keys():
        for thresh in DMG_THRESHS.keys():
            dict_bools_displ[source][thresh] = dict_imp_bldg[source].imp_mat > DMG_THRESHS[thresh]
    
    # impact df per scenario & rp + aed
    for source, dict_threshs in dict_bools_displ.items():
        for thresh, sparse_bool in dict_threshs.items():
            dict_df_imps_admin1[source][thresh] = impact_postproc.agg_sparse_rps(sparse_bool, exp.gdf, rps, thresh, group_admin1=True)
            dict_df_imps_admin1[source][thresh] = impact_postproc.compute_aeds(dict_df_imps_admin1[source][thresh], rps, thresh)
            dict_df_imps_admin1[source][thresh] = impact_postproc.compute_admin0(dict_df_imps_admin1[source][thresh])
    
    
    #save all necessary outputs
    for source in dict_df_imps_admin1.keys():
        pd.concat(dict_df_imps_admin1[source].values(), axis=1).to_csv(path_save / f'{cntry_iso}_{rcp}_{ref_year}_{source}.csv')

    # for now, do not save imp matrices.
    #for source, imp in dict_imp_bldg.items():
    #    imp.write_sparse_csr(path_save / f'{cntry_iso}_{rcp}_{ref_year}_{source}.npz')
        