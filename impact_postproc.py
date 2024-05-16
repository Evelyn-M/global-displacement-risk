"""
Functions to post-process impact matrices
"""
import numpy as np
import pandas as pd

def agg_sparse_rps(sparse_bool, exp_gdf, rps, scen_name, group_admin1=True):
    """
    Aggregate a sparse boolean impact matrix (displacement True/False) obtained from various tiles and RP maps
    into the full exposure format per RP.
    
    Parameters
    -----------
    sparse_bool: sparse.csr_matrix
        imp_mat with types bool (contrasted against dmg threshold)
    rps : np.array 
        unique return periods to group by (1/frequ of hazard events)
    exp_gdf : gpd.GeoDataFrame
        exposure geodataframe to append impacts to
    scen_name : str 
        scenario name to differentiate various impact matrices by(suggestion {impfsource}_{thresh})
    group_admin1 : bool
        whether to group results by admin1 (default: True), else full exp_gdf returned
        
    Returns
    -------
    DataFrame with columns imp_{rps}_{scen_name}, either full exposure or grouped by admin1
    """
    full_bool = sparse_bool.toarray()
    
    # get indices to sum over for each of the 7 RPs(rows)
    ix_rps = {}
    for ix, rp in enumerate(rps):
        ix_rps[rp] = np.arange(0+ix,full_bool.shape[0],7)
    
    # save impacts to exposure gdf
    for rp in rps:
        exp_gdf[f'imp_rp_{rp}_{scen_name}'] = full_bool[ix_rps[rp],:].astype(int).sum(axis=0)
    
    # groupe exposure gdf by admin1 and sum over impacts (keep only these)
    if group_admin1:
        return exp_gdf.groupby('admin1').sum()[[f'imp_rp_{rp}_{scen_name}' for rp in rps]]
    
    return exp_gdf[[f'imp_rp_{rp}_{scen_name}' for rp in rps]]

def compute_aeds(df_imps, rps, scen_name):
    """
    Manually compute average anually expected displacement, as 
    sum(displacement(rpx)/(rpx)) forall rpx
    
    Parameters
    ----------
    df_imps, 
    rps, 
    scen_name
    
    
    Returns
    --------
    df_imps with additional column aed
    """
    df_imps[f'aed_{scen_name}'] = 0
    for rp in rps:
        df_imps[f'aed_{scen_name}']+= df_imps[f'imp_rp_{rp}_{scen_name}']/rp 
    return df_imps

def compute_impstats(list_dfimps, rps):
    """
    Given a list of X impact scenario-dfs, compute min, median and max impact per RP and for AED, for all exposures.
    
    Parameters
    ----------
    list_dfimps
    rps
    
    Returns
    -------
    imp_stats : pd.DataFrame
    """
    imp_all_scens = pd.concat(list_dfimps, axis=1)
    for rp in rps:
        imp_stats[f'rp_{rp}_min'] = np.min(imp_all_scens[[col for col in imp_all_scens.columns if str(rp) in col ]], axis=1)
        imp_stats[f'rp_{rp}_med'] = np.median(imp_all_scens[[col for col in imp_all_scens.columns if str(rp) in col ]], axis=1)
        imp_stats[f'rp_{rp}_max'] = np.min(imp_all_scens[[col for col in imp_all_scens.columns if str(rp) in col ]], axis=1)
    imp_stats[f'aed_min'] = np.min(imp_all_scens[[col for col in imp_all_scens.columns if 'aed' in col ]], axis=1)
    imp_stats[f'aed_med'] = np.median(imp_all_scens[[col for col in imp_all_scens.columns if 'aed' in col ]], axis=1)
    imp_stats[f'aed_max'] = np.max(imp_all_scens[[col for col in imp_all_scens.columns if 'aed' in col ]], axis=1)
    
    return imp_stats
