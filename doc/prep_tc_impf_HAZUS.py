#%% load libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
#%% import data
DP = Path('/Users/sam/Library/CloudStorage/OneDrive-ETHZurich/UNU/Data/')
# load excel file
funcs = pd.read_excel(DP.joinpath('huDamLossFun.xlsx'), sheet_name='huDamLossFun')
tags = pd.read_excel(DP.joinpath('huDamLossFun.xlsx'), sheet_name='wbID')

# only keep rows with open terrain (id=1) & building damage (id=5)
funcs = funcs[(funcs['TERRAINID'] == 1) & (funcs['DamLossDescID'] == 5)]
funcs = funcs.merge(tags, on='wbID')
bbkp = funcs.copy()
# drop TERAINID and DamLossDescID columns, insert aggregation id
funcs.drop(columns=['TERRAINID', 'DamLossDescID', 'charDescription', 'nWindChar', 'CaseID'], inplace=True)
# move sbtName column to the front
funcs = funcs[['sbtName'] + [col for col in funcs.columns if col != 'sbtName']]

#%% reproduce curves
def sig_emanuel(x, v_thresh, v_half):
    v_temp = (x - v_thresh) / (v_half - v_thresh)
    v_temp[v_temp < 0] = 0
    y = v_temp**3 / (1 + v_temp**3)
    return y
#%%
uni_agg = funcs['aggregation'].unique()
knots_vec = np.arange(50, 251, 5)
v_halfs_agg_median = np.zeros(len(uni_agg))
v_threshs_agg_median = np.zeros(len(uni_agg))
v_halfs_agg_max = np.zeros(len(uni_agg))
v_threshs_agg_max = np.zeros(len(uni_agg))
v_halfs_agg_min = np.zeros(len(uni_agg))
v_threshs_agg_min = np.zeros(len(uni_agg))

fig, ax = plt.subplots(figsize=(20,4))
grid = plt.GridSpec(1, 5) # create a grid for the subplots

for i in range(len(uni_agg)):
    # make pandas df with all impfs for aggregation level
    cc = funcs[funcs['aggregation'] == uni_agg[i]]
    n_funcs = cc.shape[0]
    # drop non-used columns
    cc.drop(columns=['wbID', 'aggregation', 'sbtName'], inplace=True)
    # transpose df
    cc = cc.T
    # add knots_vec as column to the front
    cc.insert(0, 'inten', knots_vec)

    # make viridis color scale with number of tags
    cols = plt.cm.viridis(np.linspace(0, 1, n_funcs))
    v_halfs = np.zeros(n_funcs)
    v_threshs = np.zeros(n_funcs)
    xx = np.arange(25, 300, 1)

    ax = plt.subplot(grid[0,i])

    for t in range(n_funcs):
        mdd = cc.iloc[:,t+1].values
        v_halfs[t] = knots_vec[np.argmin(np.abs(mdd - 0.5))]
        v_threshs[t] = knots_vec[np.argmax(mdd > 0.01)]

        plt.plot(knots_vec, mdd, color=cols[t])

        yy = sig_emanuel(xx, v_threshs[t], v_halfs[t])
        ax.plot(xx,yy, color=cols[t], linestyle='dashed')

    v_halfs_agg_median[i] = np.median(v_halfs)
    v_threshs_agg_median[i] = np.median(v_threshs)
    v_halfs_agg_max[i] = np.max(v_halfs)
    v_threshs_agg_max[i] = np.max(v_threshs)
    v_halfs_agg_min[i] = np.min(v_halfs)
    v_threshs_agg_min[i] = np.min(v_threshs)

    y_main = sig_emanuel(xx, np.median(v_threshs), np.median(v_halfs))



    ax.plot(xx, y_main, color='black', linestyle='dashed', linewidth=5)
    ax.set_title(uni_agg[i])
plt.show()


# %%
# express everything as m/s instead of km/h
v_halfs_agg_median_ms = v_halfs_agg_median * 0.51444
v_threshs_agg_median_ms = v_threshs_agg_median * 0.51444
v_halfs_agg_max_ms = v_halfs_agg_max * 0.51444
v_threshs_agg_max_ms = v_threshs_agg_max * 0.51444
v_halfs_agg_min_ms = v_halfs_agg_min * 0.51444
v_threshs_agg_min_ms = v_threshs_agg_min * 0.51444

# plot all main curves in one plot
fig, ax = plt.subplots(figsize=(12,8))
xx = np.arange(0, 175, 1)
cols = plt.cm.Dark2(np.linspace(0, 1, len(uni_agg)))
fontsize = 18

for i in range(len(uni_agg)):
    y_main = sig_emanuel(xx, v_threshs_agg_median_ms[i], v_halfs_agg_median_ms[i])
    ax.plot(xx, y_main, label=uni_agg[i], color=cols[i], linewidth=3)
# add legend
ax.legend(fontsize=fontsize)
ax.set_xlabel('Intensity (m/s)', fontsize=fontsize)
ax.set_ylabel('Damage Fraction', fontsize=fontsize)
ax.tick_params(axis='both', which='major', labelsize=fontsize*0.8)
plt.show()
# %%
# same but with uncertainty bounds
fig, ax = plt.subplots(figsize=(20,5))
grid = plt.GridSpec(1, 5) # create a grid for the subplots
for i in range(len(uni_agg)):
    ax = plt.subplot(grid[0,i])

    y_main = sig_emanuel(xx, v_threshs_agg_median_ms[i], v_halfs_agg_median_ms[i])
    y_low = sig_emanuel(xx, v_threshs_agg_min_ms[i], v_halfs_agg_min_ms[i])
    y_high = sig_emanuel(xx, v_threshs_agg_max_ms[i], v_halfs_agg_max_ms[i])
    ax.plot(xx, y_main, label=uni_agg[i], color=cols[i], linewidth=3)
    ax.fill_between(xx, y_low, y_high, color=cols[i], alpha=0.3)
    ax.set_title(uni_agg[i], fontsize=fontsize*1.1)
    ax.set_xlabel('Intensity (m/s)', fontsize=fontsize)
    ax.set_ylabel('Damage Fraction', fontsize=fontsize)
    ax.tick_params(axis='both', which='major', labelsize=fontsize*0.8)
# arange for enough space between subplots
plt.tight_layout()
plt.show()
# %%
# make pandas dataframe
df = pd.DataFrame({'building_type':uni_agg,
                    'v_half_median':v_halfs_agg_median_ms,
                    'v_thresh_median':v_threshs_agg_median_ms,
                    'v_half_max':v_halfs_agg_max_ms,
                    'v_thresh_max':v_threshs_agg_max_ms,
                    'v_half_min':v_halfs_agg_min_ms,
                    'v_thresh_min':v_threshs_agg_min_ms})
df.to_csv(DP.joinpath('IF_TC_agg_HAZUS.csv'))
# %%
# compare to capra
capra = pd.read_csv(DP.joinpath('CAPRA_TC_impf/IF_TC_agg.csv'))

fig, ax = plt.subplots(figsize=(12,8))
grid = plt.GridSpec(1, 2) 
xx = np.arange(0, 175, 1)
cols = plt.cm.Dark2(np.linspace(0, 1, len(uni_agg)))
fontsize = 18
ax = plt.subplot(grid[0,0])

for i in range(len(uni_agg)):
    y_main = sig_emanuel(xx, v_threshs_agg_median_ms[i], v_halfs_agg_median_ms[i])
    ax.plot(xx, y_main, label=uni_agg[i], color=cols[i], linewidth=3)

# add legend
ax.legend(fontsize=fontsize)
ax.set_xlabel('Intensity (m/s)', fontsize=fontsize)
ax.set_ylabel('Damage Fraction', fontsize=fontsize)
ax.tick_params(axis='both', which='major', labelsize=fontsize*0.8)


ax = plt.subplot(grid[0,1])
cols = plt.cm.Dark2(np.linspace(0, 1, capra.shape[0]))

for i in range(capra.shape[0]):
    y_main = sig_emanuel(xx, capra['v_thresh_median'][i], capra['v_half_median'][i])
    ax.plot(xx, y_main, label=capra['building_type'][i], color=cols[i], linewidth=3)

# add legend
ax.legend(fontsize=fontsize)
ax.set_xlabel('Intensity (m/s)', fontsize=fontsize)
ax.set_ylabel('Damage Fraction', fontsize=fontsize)
ax.tick_params(axis='both', which='major', labelsize=fontsize*0.8)


plt.show()
# %%
fig, ax = plt.subplots(figsize=(12,8))
xx = np.arange(0, 175, 1)
cols = plt.cm.Dark2(np.linspace(0, 1, len(uni_agg)))
fontsize = 18

for i in range(len(uni_agg)):
    y_main = sig_emanuel(xx, v_threshs_agg_median_ms[i], v_halfs_agg_median_ms[i])
    ax.plot(xx, y_main, label=uni_agg[i], color=cols[i], linewidth=3)

i=3 # wood
y_main = sig_emanuel(xx, capra['v_thresh_median'][i], capra['v_half_median'][i])
ax.plot(xx, y_main, label=capra['building_type'][i]+'_capra', color=cols[0], linewidth=3, linestyle='dashed')

i=1 # Masonry
y_main = sig_emanuel(xx, capra['v_thresh_median'][i], capra['v_half_median'][i])
ax.plot(xx, y_main, label=capra['building_type'][i]+'_capra', color=cols[1], linewidth=3, linestyle='dashed')

i=0 # Concrete
y_main = sig_emanuel(xx, capra['v_thresh_median'][i], capra['v_half_median'][i])
ax.plot(xx, y_main, label=capra['building_type'][i]+'_capra', color=cols[2], linewidth=3, linestyle='dashed')

i=2 # Steel
y_main = sig_emanuel(xx, capra['v_thresh_median'][i], capra['v_half_median'][i])
ax.plot(xx, y_main, label=capra['building_type'][i]+'_capra', color=cols[3], linewidth=3, linestyle='dashed')

# add legend
ax.legend(fontsize=fontsize*0.8)
ax.set_xlabel('Intensity (m/s)', fontsize=fontsize)
ax.set_ylabel('Damage Fraction', fontsize=fontsize)
ax.tick_params(axis='both', which='major', labelsize=fontsize*0.7)
plt.show()
# %%
