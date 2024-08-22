for cntry in "USA"

do
    echo $cntry
	myjobid=$(sbatch --parsable -J cf_risk_$cntry --time=120:00:00 -n 1 --cpus-per-task=12 --mem-per-cpu=50000 --mail-type=FAIL --wrap="python /cluster/project/climate/evelynm/global-displacement-risk/main_scripts/displacement_risk_coastalflood_lrg_mod.py $cntry")
done
