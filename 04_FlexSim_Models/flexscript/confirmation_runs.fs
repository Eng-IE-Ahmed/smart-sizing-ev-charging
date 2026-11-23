//  FlexSim confirmation runs (30 reps) on the scripted model (hours). Parameters (commandlineparam):
//   -set front|policy|peak  -growth <m> -c1 -c2 -c3 <chargers>  [-pol P1|P2|P3 -par <g min | cap h | p>]
// front : base model band_long, pooled weekdays (same generator as b4_runs.fs).
// policy: stay = occupancy from (charge, dwell) PAIRS of the arrival band (tables PairBand1..6, imported with explicit
//         separators): P1 min(dwell, charge + g/60); P2 min(dwell, cap); P3 complier (stream 60 + r < p) uses P1-60.
// peak  : 20% of 08:00-09:30 arrivals moved to 09:30-11:00 the same day (stream 60 + r: decision and new time), arrivals
//         sorted again, stay by the NEW arrival band (variant a).
// Streams: arrivals 2r-1, stays 2r, policy/peak 60 + r (r = 1..30, all <= 90; stream 100 is defective).
// Output: C:/ev/out/d5_<set>_m<m>_reps.csv (set, m, rep, c, N, Wq_min, P0, P15, W95_min, started); FlexSim stays open.
// Verified (help / tests): as b4_runs.fs plus Tools.create, importtable(…, ",", "."), commandlineparam, string.toNum;
// charger creation as b2_build.fs (Object.create, contextdragconnection, switch_flexscript, buildnodeflexscript);
// display as b8_layout.fs (switch_hideconnectors, switch_hidelabel, Object.color + Color.gray, repaintall).
string SET = commandlineparam("set");
string ms_ = commandlineparam("growth");      // not "m": commandlineparam("m") returned "maintenance" (/maintenance token)
double m = ms_.toNum();
if (m <= 0) {
	fileopen("C:/ev/out/d5_param_error.txt", "w"); fpt("bad -growth value: " + ms_); fpr(); fileclose();
	return 0;
}
string c1s = commandlineparam("c1");
string c2s = commandlineparam("c2");
string c3s = commandlineparam("c3");
Array cl = [c1s.toNum(), c2s.toNum(), c3s.toNum()];
string POL = commandlineparam("pol");
string pars = commandlineparam("par");
double PAR = 0;
if (pars != "")
	PAR = pars.toNum();
string TAG = SET + "_m" + ms_;
string RES = "C:/ev/out/d5_" + TAG + "_reps.csv";
string LOG = "C:/ev/out/d5_" + TAG + "_log.txt";
fileopen(LOG, "w"); fpt("start set " + SET + " m " + ms_ + " pol " + POL + " par " + pars); fpr(); fileclose();
fileopen(RES, "w"); fpt("set,m,rep,c,N,Wq_min,P0,P15,W95_min,started"); fpr(); fileclose();
if (SET == "policy") {
	for (int b = 1; b <= 6; b++) {
		treenode gt = Tools.create("GlobalTable");
		gt.name = "PairBand" + string.fromNum(b);
		importtable(gt.find(">variables/data"), "C:/ev/in/PairBand" + string.fromNum(b) + ".csv", 1, 0, ",", ".");
	}
}
Object src = Model.find("CarArrivals");
Object q = Model.find("ChargeQueue");
// c > 52 (frontier at m = 1.6): add chargers 53..NCH exactly as b2_build.fs built 1..52 (same cycletime code, same
// Queue -> Processor -> Sink connections; the model file is reloaded at each launch, so they never pre-exist).
int NCH = 52;
for (int ci = 1; ci <= 3; ci++) {
	if (cl[ci] > NCH)
		NCH = cl[ci];
}
if (NCH > 52) {
	Object snk = Model.find("Departed");
	string ct_code = "Object current = ownerobject(c);\nObject item = param(1);\n"
		+ "/* : next car in FIFO order; record start time and charger id; return its stay (h) */\n"
		+ "Object q = Model.find(\"ChargeQueue\");\nint k = q.served + 1;\nq.served = k;\nTable cars = Table(\"Cars\");\n"
		+ "cars[k][4] = Model.time;\ncars[k][5] = current.chargerId;\nreturn cars[k][2];";
	for (int i = 53; i <= NCH; i++) {
		Object p = Object.create("Processor");
		p.name = "Charger" + string.fromNum(i);
		int col = (i - 1) % 13;
		int row = Math.floor((i - 1) / 13);
		p.setLocation(14 + col * 3, -6 + row * 4, 0);
		p.chargerId = i;
		contextdragconnection(q, p, "A");
		contextdragconnection(p, snk, "A");
		treenode ct = p.find(">variables/cycletime");
		ct.dataType = 2;
		ct.value = ct_code;
		switch_flexscript(ct, 1);
		buildnodeflexscript(ct);
	}
	fileopen(LOG, "a"); fpt("added chargers 53.." + string.fromNum(NCH)); fpr(); fileclose();
}
Table rt = Table("ArrRate48");
Table boh = Table("BandOfHour24");
Array rate = [];
Array cum = [0];
for (int k = 1; k <= 48; k++) {
	rate.push(rt[k][3]);
	cum.push(cum[k] + rt[k][3]);
}
double daytot = cum[49];
for (int r = 1; r <= 30; r++) {
	int sa = 2 * r - 1;
	int ss = 2 * r;
	int sx = 60 + r;
	resetmodel();
	Array arrA = [];
	double L = 0;
	while (1) {
		L = L - Math.log(1 - uniform(0, 1, sa));
		int day = Math.floor(L / (daytot * m));
		double rem = (L - day * daytot * m) / m;
		int k = 1;
		while (k < 48 && cum[k + 1] <= rem)
			k++;
		double t = day * 24 + (k - 1) * 0.5 + (rem - cum[k]) / rate[k] * 0.5;
		if (t >= 1560)
			break;
		arrA.push(t);
	}
	int n = arrA.length;
	if (SET == "peak") {
		for (int k = 1; k <= n; k++) {
			double t = arrA[k];
			double hod = Math.fmod(t, 24);
			double usel = uniform(0, 1, sx);
			double unew = uniform(0, 1, sx);
			if (hod >= 8 && hod < 9.5 && usel < 0.2)
				arrA[k] = Math.floor(t / 24) * 24 + 9.5 + 1.5 * unew;
		}
		arrA.sort();
	}
	Table cars = Table("Cars");
	cars.setSize(n, 6);
	for (int k = 1; k <= n; k++) {
		double t = arrA[k];
		int hr = Math.floor(Math.fmod(t, 24));
		int band = boh[hr + 1][2];
		double u2 = uniform(0, 1, ss);
		double occ = 0;
		if (SET == "policy") {
			Table pb = Table("PairBand" + string.fromNum(band));
			int np = pb.numRows;
			int idx = Math.ceil(u2 * np);
			if (idx < 1)
				idx = 1;
			if (idx > np)
				idx = np;
			double ch = pb[idx][1];
			double dw = pb[idx][2];
			occ = dw;
			if (POL == "P1")
				occ = Math.min(dw, ch + PAR / 60);
			if (POL == "P2")
				occ = Math.min(dw, PAR);
			if (POL == "P3") {
				if (uniform(0, 1, sx) < PAR)
					occ = Math.min(dw, ch + 1);
			}
		} else {
			Table sb = Table("ServiceBand" + string.fromNum(band));
			int nb = sb.numRows;
			int idx = Math.ceil(u2 * nb);
			if (idx < 1)
				idx = 1;
			if (idx > nb)
				idx = nb;
			occ = sb[idx][1];
		}
		cars[k][1] = t;
		cars[k][2] = occ;
		cars[k][3] = band;
	}
	for (int ci = 1; ci <= 3; ci++) {
		int nc = cl[ci];
		for (int k = 1; k <= n; k++) {
			cars[k][4] = -1;
			cars[k][5] = 0;
		}
		src.nextCar = 0;
		q.served = 0;
		resetmodel();
		for (int p = 1; p <= NCH; p++) {
			string id = string.fromNum(p);
			if (p < 10)
				id = "0" + id;
			Object chg = Model.find("Charger" + id);
			if (p > nc)
				chg.input.close();
			else
				chg.input.open();
		}
		stoptime(2160);
		runfunction(1);
		Table cr = Table("Cars");
		double sw = 0;
		int n0 = 0;
		int n15 = 0;
		int started = 0;
		Array ws = [];
		for (int k = 1; k <= n; k++) {
			if (cr[k][4] >= 0)
				started++;
			double w = (cr[k][4] - cr[k][1]) * 60;
			sw = sw + w;
			if (w > 0.000000001)
				n0++;
			if (w > 15)
				n15++;
			ws.push(w);
		}
		ws.sort();
		double hq = (n - 1) * 0.95;
		int lo = Math.floor(hq);
		double w95 = ws[lo + 1] + (hq - lo) * (ws[lo + 2] - ws[lo + 1]);
		double dn = n;
		fileopen(RES, "a");
		fpt(SET + "," + ms_ + "," + string.fromNum(r) + "," + string.fromNum(nc) + "," + string.fromNum(n) + "," + string.fromNum(sw / dn, 17)
			+ "," + string.fromNum(n0 / dn, 17) + "," + string.fromNum(n15 / dn, 17) + "," + string.fromNum(w95, 17) + "," + string.fromNum(started));
		fpr();
		fileclose();
	}
	fileopen(LOG, "a"); fpt("rep " + string.fromNum(r) + " done, N = " + string.fromNum(n)); fpr(); fileclose();
}
// Display pass for the window capture (no effect on the results above): rep 30's cars, c = c2 (the middle value),
// chargers above c2 grey and closed, connectors/labels hidden, run stopped at 201.5 h (day 9, 09:30 = morning peak).
Table cd = Table("Cars");
int nd = cd.numRows;
for (int k = 1; k <= nd; k++) {
	cd[k][4] = -1;
	cd[k][5] = 0;
}
src.nextCar = 0;
q.served = 0;
resetmodel();
// layout of b8_layout.fs (fits FlexSim's default camera): columns x = -13, -8.5 | aisle | 8.5, 13 (+17.5 for 53..65),
// 13 chargers 2.2 m apart per column; positions only, no change to connections or logic.
Array colsX = [-13, -8.5, 8.5, 13, 17.5];
src.setLocation(-5, -4, 0);
q.setLocation(0, -4, 0);
Object snkd = Model.find("Departed");
snkd.setLocation(22, 28, 0);
switch_hideconnectors(src, 1);
switch_hideconnectors(q, 1);
switch_hideconnectors(snkd, 1);
for (int p = 1; p <= NCH; p++) {
	string id = string.fromNum(p);
	if (p < 10)
		id = "0" + id;
	Object chg = Model.find("Charger" + id);
	chg.setLocation(colsX[Math.floor((p - 1) / 13) + 1], ((p - 1) % 13) * 2.2, 0);
	switch_hideconnectors(chg, 1);
	switch_hidelabel(chg, 1);
	if (p > cl[2]) {
		chg.input.close();
		chg.color = Color.gray;
	} else
		chg.input.open();
}
stoptime(201.5);
runfunction(1);
repaintall();
fileopen(LOG, "a"); fpt("display pass: rep 30, c = " + string.fromNum(cl[2]) + ", stopped at " + string.fromNum(Model.time, 2) + " h, cars served " + string.fromNum(q.served) + ", in queue " + string.fromNum(q.subnodes.length)); fpr(); fileclose();
fileopen("C:/ev/out/d5_" + TAG + "_ready.txt", "w"); fpt("ready"); fpr(); fileclose();
