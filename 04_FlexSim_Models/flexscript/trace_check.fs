//  trace mode: feed FlexSim the engine's exact arrival and stay times of replication 1 (band_long, m = 1.3) and
// record every car's start time and charger, for c = 42 and c = 45 (chargers above c closed with input.close()).
// Output per car (17 significant digits): k, arr_h, svc_h, start_h, charger, wait_min = (start - arr) * 60.
// Verified (help / tests): Model.find, Tools.get, treenode.find, importtable(…, ",", "."), Table(name), Table.setSize/
// numRows/[][], labelProperties, resetmodel, Object.input.close/open, stoptime, runfunction, string.fromNum,
// fileopen/fpt/fpr/fileclose, cmdexit.
string LOG = "C:/ev/out/b3_trace_log.txt";
fileopen(LOG, "w"); fpt("start trace"); fpr(); fileclose();
Object src = Model.find("CarArrivals");
Object q = Model.find("ChargeQueue");
Object dep = Model.find("Departed");
treenode carsData = Tools.get("GlobalTable", "Cars").find(">variables/data");
importtable(carsData, "C:/ev/in/trace_rep1_c42_m1.3.csv", 1, 0, ",", ".");
Table cars = Table("Cars");
int n = cars.numRows;
cars.setSize(n, 6);
fileopen(LOG, "a"); fpt("trace imported: " + string.fromNum(n) + " cars x " + string.fromNum(cars.numCols) + " cols; first arr "
	+ string.fromNum(cars[1][1], 17)); fpr(); fileclose();
Array cs = [42, 45];
for (int j = 1; j <= cs.length; j++) {
	int nc = cs[j];
	for (int k = 1; k <= n; k++) {
		cars[k][4] = -1;
		cars[k][5] = 0;
	}
	src.nextCar = 0;
	q.served = 0;
	resetmodel();
	fileopen(LOG, "a"); fpt("c = " + string.fromNum(nc) + ": after resetmodel rows " + string.fromNum(Table("Cars").numRows) + ", cars[1][1] = "
		+ string.fromNum(Table("Cars")[1][1], 17) + ", nextCar = " + string.fromNum(src.nextCar)); fpr(); fileclose();
	for (int i = 1; i <= 52; i++) {
		string id = string.fromNum(i);
		if (i < 10)
			id = "0" + id;
		Object p = Model.find("Charger" + id);
		if (i > nc)
			p.input.close();
		else
			p.input.open();
	}
	stoptime(2060);
	runfunction(1);
	Table cr = Table("Cars");
	int started = 0;
	fileopen("C:/ev/out/flexsim_trace_rep1_m1.3_c" + string.fromNum(nc) + ".csv", "w");
	fpt("k,arr_h,svc_h,start_h,charger,wait_min");
	fpr();
	for (int k = 1; k <= n; k++) {
		if (cr[k][4] >= 0)
			started++;
		fpt(string.fromNum(k) + "," + string.fromNum(cr[k][1], 17) + "," + string.fromNum(cr[k][2], 17) + "," + string.fromNum(cr[k][4], 17)
			+ "," + string.fromNum(cr[k][5]) + "," + string.fromNum((cr[k][4] - cr[k][1]) * 60, 17));
		fpr();
	}
	fileclose();
	fileopen(LOG, "a"); fpt("c = " + string.fromNum(nc) + ": run to " + string.fromNum(Model.time, 3) + " h, served " + string.fromNum(q.served)
		+ ", started " + string.fromNum(started) + " of " + string.fromNum(n) + ", departed " + string.fromNum(dep.stats.input.value)); fpr(); fileclose();
}
cmdexit();
