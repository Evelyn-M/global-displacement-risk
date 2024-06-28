"""
Created in February 2024

description: Load TC hazard chunks from the MIT model and concatenate them to
            entire hazard set.
            Apply frequency correction.
            Store as hdf5 files.

@author: simonameiler
"""

import sys
import os
import re
import numpy as np
from scipy.io import loadmat
import datetime as dt

# import CLIMADA modules:
from climada.hazard import TropCyclone
from climada.util.constants import SYSTEM_DIR

############################################################################

def main(region):
    
    region = str(region)
        
    res = 150
    
    tracks_dir = SYSTEM_DIR/"tracks"/"Kerry"/"ERA5"
    fname = tracks_dir.joinpath(f"temp_{region}_era5_reanalcal.mat")
    
    haz_in = SYSTEM_DIR/"hazard"/"present"/"MIT_chunks"
    haz_out = SYSTEM_DIR/"hazard"/"present"
    haz_str = f"TC_{region}_0{res}as_MIT_H08.hdf5"
    
    # load all hazard files and append to list
    pattern = re.compile(f'TC_{region}_0{res}as_MIT_H08_(\d+)\.hdf5')
    
    file_list = []
    
    # Iterate over filenames in the specified directory
    for filename in os.listdir(haz_in):
        match = re.match(pattern, filename)
        if match:
            # Filename matches, append it to the list
            file_list.append(filename)
    
    def extract_number(filename):
        return int(filename.split('_')[-1].split('.')[0])

    # Sort the list by the extracted number
    sorted_file_list = sorted(file_list, key=extract_number)
    
    # make hazard object from the list of files
    MIT_hazard = TropCyclone()
    for fl in sorted_file_list:
        tc_hazard = TropCyclone.from_hdf5(haz_in/fl)
        MIT_hazard.append(tc_hazard)

    
    # apply frequency correction according to the freq scalar provided with the
    # event sets
    freq_year = loadmat(fname)['freqyear'][0].tolist()
    
    event_year = np.array([
        dt.datetime.fromordinal(d).year 
        for d in MIT_hazard.date.astype(int)])
    
    yrs_total = event_year[-1]-event_year[0]+1

    for i, yr in enumerate(np.unique(event_year)):
        yr_mask = (event_year == yr)
        yr_event_count = yr_mask.sum()
        MIT_hazard.frequency[yr_mask] = (
        np.ones(yr_event_count) * freq_year[i] /
        (yr_event_count * yrs_total)
        )    
    MIT_hazard.write_hdf5(haz_out.joinpath(haz_str))
    MIT_hazard.check()

if __name__ == "__main__":
    main(*sys.argv[1:])
