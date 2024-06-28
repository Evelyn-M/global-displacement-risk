"""
Functions to post-process impact matrices
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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
        scenario name to differentiate various impact matrices by(suggestion {impfsource}_{thresh} or {thresh})
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
        exp_gdf[f'imp_rp_{rp}_{scen_name}'] = full_bool[ix_rps[rp],:].astype(int).sum(axis=0)*exp_gdf['valhum']
    
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

def compute_admin0(df_imps):
    """
    sum over all exposures to get admin0 impacts.
    """
    imps_admin_0 = df_imps.sum(axis=0)
    imps_admin_0.name = 'admin0'
    return df_imps.append(imps_admin_0)
    
def compute_impstats(list_dfimps, rps):
    """
    Given a list of X impact scenario-dfs, compute min, median and max impact per RP and for AED, for all exposures.
    Note: Only makes sense if various impfs sources in scenarios. 
    
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


def plot_aeds_admin0(df_rcp26, df_rcp45, df_rcp85, cntry_iso):
    fig, ax = plt.subplots()
    x = [2020, 2050, 2100]

    ax.plot(x, df_rcp26['aed_med'], label='RCP2.6', color='b')
    ax.fill_between(x,
       df_rcp26['aed_low'], df_rcp26['aed_high'], color='b', alpha=.15)

    ax.plot(x, df_rcp45['aed_med'], label='RCP4.5',  color='g')
    ax.fill_between(x,
       df_rcp45['aed_low'], df_rcp45['aed_high'], color='g', alpha=.15)

    ax.plot(x, df_rcp85['aed_med'], label='RCP8.5', color='r', )
    ax.fill_between(x,
       df_rcp85['aed_low'], df_rcp85['aed_high'], color='r', alpha=.15)

    ax.legend(loc=4)
    ax.set_ylim(ymin=0)
    ax.set_title(f'Avg. annual expected displacement, {cntry_iso}')
    plt.show()

def _load_format_aed_results(base_path_start, base_path_end):
    years = [2020, 2050, 2100]
    df = pd.concat([pd.read_csv(base_path_start+str(year)+base_path_end).iloc[-1][['aed_low', 'aed_med', 'aed_high']]
                    for year in years], axis=1)
    df.columns = years
    df = df.T
    df = df.astype(float)
    return df
    

# load admin0 AEDs from all rcps
def load_aeds_admin0(cntry_iso, source, path_results='/cluster/work/climate/evelynm/IDMC_UNU/results/risk_cf'):
    
    base_path_end = f'_{source}.csv'
    
    rcp=26
    base_path_start = f'{path_results}/{cntry_iso}/{cntry_iso}_RCP{rcp}_'
    df_rcp26 = _load_format_aed_results(base_path_start, base_path_end)
    
    rcp=45
    base_path_start = f'{path_results}/{cntry_iso}/{cntry_iso}_RCP{rcp}_'
    df_rcp45 = _load_format_aed_results(base_path_start, base_path_end)

    rcp=85
    base_path_start = f'{path_results}/{cntry_iso}/{cntry_iso}_RCP{rcp}_'
    df_rcp85 = _load_format_aed_results(base_path_start, base_path_end)

    return df_rcp26, df_rcp45, df_rcp85
