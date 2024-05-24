
for cntry in LKA BGD MOZ #PHL ETH SOM
do
        for rcp in RCP26 RCP45 RCP85
	do
		for year in 2020 2050 2100
		do
        		echo $cntry $rcp $year
			sbatch --parsable -J cf_risk_$cntry_$rcp_$yer --time=8:00:00 --nodes=1 -n 1 --mem-per-cpu=100000 --mail-type=END,FAIL --wrap="python displacement_risk_coastalflood.py $cntry $rcp $year"
       
		done
       done
       
done