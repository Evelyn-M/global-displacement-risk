{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "5297ebf7",
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "import pandas as pd\n",
    "\n",
    "\n",
    "path_gpkg = '/cluster/work/climate/evelynm/IDMC_UNU/centroids/gadm_410-levels.gpkg'\n",
    "path_results = '/cluster/work/climate/evelynm/IDMC_UNU/results/risk_cf/'\n",
    "\n",
    "gadm_attrs = pd.read_csv('/cluster/work/climate/evelynm/IDMC_UNU/centroids/attribute_table_gadm41.csv')\n",
    "gadm_attrs_map = dict(zip(gadm_attrs.fid, gadm_attrs.GID_1))\n",
    "gadm_attrs_map[-999] = 'admin0'\n",
    "    \n",
    "cntry_paths = os.listdir(path_bem)\n",
    "for cntry_path in cntry_paths:\n",
    "    result_paths = os.listdir(path_cntry_path)\n",
    "    for path_result_df in result_paths:\n",
    "        \n",
    "        df_results = pd.read_csv(path_result_df)\n",
    "        df_results.replace({'admin0':-999}, inplace=True)\n",
    "        df_results['admin1'] = df_results_chl.admin1.astype(float)\n",
    "        df_results['admin1'] = df_results_chl.admin1.astype(int)\n",
    "        df_results['GID_1'] = df_results_chl.admin1.map(gadm_attrs_map)\n",
    "        df_results.to_csv(path_result_df)"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python3.9 (climada_venv)",
   "language": "python",
   "name": "climada_venv"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.7.6"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
