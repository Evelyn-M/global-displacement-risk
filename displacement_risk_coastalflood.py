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
DMG_THRESHS = {'low' : 0.3, 'med' : 0.45, 'high': 0.6}


# =============================================================================
# Execution
# =============================================================================
if __name__ == '__main__': 
    cntry_iso = sys.argv[1]
    rcp = sys.argv[2]
    ref_year = sys.argv[3]
    path_save = PATH_RESULTS / cntry_iso
    
    if not path_save.is_dir():
        os.mkdir()
       
    # load bem, make exp
    gdf_bem_subcomps = exposure.gdf_from_bem_subcomps(cntry, opt='full')
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
    CF = coastal_flood_hazard.generate_hazard_object(tiles, haz_CF_dir, rcp, ref_year, 'FL')
    rps = 1/CF.frequency[:7]
    
    # compute physical impact and save for future postproc
    # scenario 1: capra/cima impfs
    dict_imp_bldg = {}
    exp.gdf['impf_FL'] = exp.gdf['se_seismo'].map(vulnerability.DICT_PAGER_FLIMPF_CIMA)
    dict_imp_bldg['cima'] = ImpactCalc(exp, vulnerability.IMPF_SET_FL_CIMA, CF).impact(save_mat=True)
    # scenario 2: ivm impfs
    exp.gdf['impf_FL'] = exp.gdf['se_seismo'].map(vulnerability.DICT_PAGER_FLIMPF_IVM)
    dict_imp_bldg['ivm'] = ImpactCalc(exp, vulnerability.IMPF_SET_FL_IVM, CF).impact(save_mat=True)
    
    # displacement postprocessing (thresholds)
    dict_bools_displ = {}
    for source in dict_imp_bldg.keys():
        for thresh in DMG_THRESHS.keys():
            dict_bools_displ[f'{source}_{thresh}'] = dict_imp_bldg[source].imp_mat > DMG_THRESHS[thresh]
    
    # impact df per scenario & rp + aed
    dict_df_imps_admin1 = {}
    for scen, sparse_bool in dict_bools_displ.items():
        dict_df_imps_admin1[scen] = impact_postproc.agg_sparse_rps(sparse_bool, exp.gdf, rps, scen, group_admin1=True)
        dict_df_imps_admin1[scen] = impact_postproc.compute_aeds(dict_df_imps_admin1[scen], rps, scen)
    
    # min, median & max stats
    df_impstats = compute_impstats(list(dict_df_imps_admin1.values()), rps)
    
    #save all necessary outputs
    df_impstats.to_csv(path_save / f'{cntry_iso}_{rcp}_{ref_year}.csv')
    for source, imp in dict_imp_bldg.items():
        imp.write_sparse_csr(path_save / f'{cntry_iso}_{rcp}_{ref_year}_{source}.npz')
        
    # TODO: save cntry stats to dict
    # imp_stats[[col for col in imp_stats.columns if 'aed' in col]].sum()