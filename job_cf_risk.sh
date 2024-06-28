
for cntry in USA IND RUS
do
        for rcp in RCP26 RCP45 RCP85
	do
		for year in 2020 2050 2100
		do
        		echo $cntry $rcp $year
			sbatch --parsable -J cf_risk_$cntry_$rcp_$yer --time=48:00:00 --nodes=1 --mem=400000 --mail-type=FAIL --wrap="python /cluster/project/climate/evelynm/global-displacement-risk/displacement_risk_coastalflood_lrg.py $cntry $rcp $year"
       
		done
       done
       
done