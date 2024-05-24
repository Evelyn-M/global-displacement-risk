for cntry in PHL MEX
do
    for rcp in ssp245 ssp370 ssp585
    do
        for building_thresh in 0.3 0.55 0.7
        do
            echo $cntry $rcp $building_thresh
            sbatch --parsable -J risk_tc_${cntry}_${rcp}_${building_thresh} --time=8:00:00 --nodes=1 -n 8 --mem-per-cpu=250000 --mail-type=END,FAIL --wrap="python displacement_risk_tc.py $cntry $rcp $building_thresh"
        done
    done
done
