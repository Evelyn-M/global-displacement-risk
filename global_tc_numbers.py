#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 12 14:23:22 2024

@author: simonameiler
"""

import os
import pandas as pd
import numpy as np

# Define the path to the folder
folder_path = '/cluster/work/climate/evelynm/IDMC_UNU/results/risk_tc'

# Define the scenarios and thresholds
scenarios = ['ssp245', 'ssp370', 'ssp585']
thresholds = [0.3, 0.55, 0.7]

# Initialize columns of interest
columns = ['AAD', 'RP_10', 'RP_25', 'RP_50', 'RP_100', 'RP_250']

# Initialize dictionaries to store the results
global_sums = {scenario: {thresh: {period: {col: 0 for col in columns} for period in ['hist', '2050', '2100']} for thresh in thresholds} for scenario in scenarios}
relative_changes = {scenario: {thresh: {period: {col: 0 for col in columns} for period in ['2050', '2100']} for thresh in thresholds} for scenario in scenarios}

# Function to process each CSV file
def process_csv(file_path):
    df = pd.read_csv(file_path)
    # Get the top three rows (admin0 level)
    admin0_data = df[df['Exposure'] == 'admin0'].head(3)
    return admin0_data

# Loop through all subfolders
for country in os.listdir(folder_path):
    country_path = os.path.join(folder_path, country)
    if os.path.isdir(country_path):
        for file in os.listdir(country_path):
            if file.endswith('.csv'):
                # Extract parameters from filename
                parts = file.split('_')
                iso3 = parts[0]
                ssp = parts[1]
                thresh = float(parts[2])
                if ssp in scenarios and thresh in thresholds:
                    file_path = os.path.join(country_path, file)
                    admin0_data = process_csv(file_path)
                    # Sum up values for each Period
                    for index, row in admin0_data.iterrows():
                        period = row['Period']
                        if period in ['hist', '2050', '2100']:
                            for col in columns:
                                global_sums[ssp][thresh][period][col] += row[col]
                    
                    # Calculate relative changes
                    hist_data = admin0_data[admin0_data['Period'] == 'hist']
                    future_data = admin0_data[admin0_data['Period'] != 'hist']
                    for _, future_row in future_data.iterrows():
                        period = future_row['Period']
                        if period in ['2050', '2100']:
                            for col in columns:
                                if not hist_data.empty:
                                    hist_value = hist_data[col].values[0]
                                    if not np.isnan(hist_value) and hist_value != 0:
                                        relative_change = (future_row[col] - hist_value) / hist_value
                                        relative_changes[ssp][thresh][period][col] += relative_change

# Convert the results to DataFrames for better readability and save them to CSV files
for scenario in scenarios:
    for thresh in thresholds:
        global_sums_df = pd.DataFrame(global_sums[scenario][thresh]).T
        relative_changes_df = pd.DataFrame(relative_changes[scenario][thresh]).T
        
        global_sums_filename = f'global_sums_{scenario}_{thresh}.csv'
        relative_changes_filename = f'relative_changes_{scenario}_{thresh}.csv'
        
        global_sums_df.to_csv(global_sums_filename)
        relative_changes_df.to_csv(relative_changes_filename)
