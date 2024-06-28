"""
Created in February 2024

description: Load TC tracks from the MIT model and calculate the 2D windfield
            after Holland (2008) at 150as resolution on land - store in chunks of k 
            number of tracks.

@author: simonameiler
"""

import sys
import copy
from pathos.pools import ProcessPool as Pool

# import CLIMADA modules:
from climada.hazard import Centroids, TCTracks, TropCyclone
from climada.util.constants import SYSTEM_DIR

############################################################################

def main(region):
    
    region = str(region)
        
    res = 150
    
    tracks_dir = SYSTEM_DIR.joinpath('tracks','Kerry','ERA5')
    fname = tracks_dir.joinpath(f"temp_{region}_era5_reanalcal.mat")
    haz_dir = SYSTEM_DIR.joinpath('hazard','present','MIT_chunks')
    
    cent_str = SYSTEM_DIR.joinpath("earth_centroids_150asland_1800asoceans_distcoast_region.hdf5")
    
    # Initiate MIT tracks
    def init_MIT_tracks(region):
        if region == 'SH':
            tracks_MIT = TCTracks.from_simulations_emanuel(fname, hemisphere='S')
        else:
            tracks_MIT = TCTracks.from_simulations_emanuel(fname, hemisphere='N')
        tracks_MIT.equal_timestep(time_step_h=.5)
        return tracks_MIT
    
    # call functions
    tc_tracks = init_MIT_tracks(region)
    
    # load centroids from this source
    cent = Centroids.from_hdf5(cent_str)
    # limit centroids to extent of track set
    cent_tracks = cent.select(extent=tc_tracks.get_extent(5))
    
    # caluclate windfields in chunks of k number of tracks
    pool = Pool()
    k = 1000
    for n in range(0, tc_tracks.size, k):
        tracks = copy.deepcopy(tc_tracks)
        tracks.data = tracks.data[n:n+k]
        tracks.equal_timestep(time_step_h=.5)
        tc = TropCyclone.from_tracks(tracks, centroids=cent_tracks, pool=pool)
        haz_str = f"TC_{region}_0{res}as_MIT_H08_{n}.hdf5"
        tc.write_hdf5(haz_dir.joinpath(haz_str))
    pool.close()
    pool.join()

if __name__ == "__main__":
    main(*sys.argv[1:])
