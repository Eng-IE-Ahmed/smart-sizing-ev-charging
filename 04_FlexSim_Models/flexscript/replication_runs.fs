//  stochastic mode with FlexSim's own random streams. For each growth m in {1.0, 1.3} (pooled weekday rates)
// and replication r = 1..30: after resetmodel() (streams reseeded), generate the cars of 65 weekdays (1,560 h) with
// stream 2r-1 for arrivals (NHPP by inversion of the cumulative rate, the engine's algorithm: L += -ln(1-U),
// day = floor(L / (D m)), rem = (L - day D m) / m, slot k with Lambda_k <= rem, t = 24 day + 0.5 k + 0.5 (rem -
// Lambda_k) / rate_k) and stream 2r for the stay (band = BandOfHour24[hour], stay = pool_band[max(1, ceil(U n))]).
// The same cars are then run for c = 44, 45, 46, 47, 52 (CRN across c). Streams used: 1..60 (stream 100 is defective).
// Per replication and c: N, mean wait (min), P(W>0) (w > 1e-9 min), P(W>15), W95 (linear interpolation as numpy).
// Verified (help / tests): Model.find, Table(name), Table.setSize/numRows/[][], Array push/sort/length, Math.log/floor/
// ceil/fmod, uniform(min, max, stream), resetmodel, Object.input.close/open, labelProperties, stoptime, runfunction,
// string.fromNum, fileopen/fpt/fpr/fileclose, cmdexit.
string LOG = "C:/ev/out/b4_runs_log.txt";
string RES = "C:/ev/out/flexsim_runs_reps.csv";
fileopen(LOG, "w"); fpt("start runs"); fpr(); fileclose();
fileopen(RES, "w"); fpt("m,profile,rep,stream_arr,stream_svc,c,N,Wq_min,P0,P15,W95_min,started,max_charger"); fpr(); fileclose();
Object src = Model.find("CarArrivals");
Object q = Model.find("ChargeQueue");
Table rt = Table("ArrRate48");
Table boh = Table("BandOfHour24");
Array ms = [1.0, 1.3];
Array cl = [44, 45, 46, 47, 52];
int NREP = 30;
double H = 1560;
Array rate = [];
Array cum = [0];
for (int k = 1; k <= 48; k++) {
	rate.push(rt[k][3]);
	cum.push(cum[k] + rt[k][3]);
}
double daytot = cum[49];
for (int mi = 1; mi <= ms.length; mi++) {
	double m = ms[mi];
	for (int r = 1; r <= NREP; r++) {
		int sa = 2 * r - 1;
		int ss = 2 * r;
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
			if (t >= H)
				break;
			arrA.push(t);
		}
		int n = arrA.length;
		Table cars = Table("Cars");
		cars.setSize(n, 6);
		for (int k = 1; k <= n; k++) {
			double t = arrA[k];
			int hr = Math.floor(Math.fmod(t, 24));
			int band = boh[hr + 1][2];
			Table sb = Table("ServiceBand" + string.fromNum(band));
			int nb = sb.numRows;
			int idx = Math.ceil(uniform(0, 1, ss) * nb);
			if (idx < 1)
				idx = 1;
			if (idx > nb)
				idx = nb;
			cars[k][1] = t;
			cars[k][2] = sb[idx][1];
			cars[k][3] = band;
		}
		for (int ci = 1; ci <= cl.length; ci++) {
			int nc = cl[ci];
			for (int k = 1; k <= n; k++) {
				cars[k][4] = -1;
				cars[k][5] = 0;
			}
			src.nextCar = 0;
			q.served = 0;
			resetmodel();
			for (int p = 1; p <= 52; p++) {
				string id = string.fromNum(p);
				if (p < 10)
					id = "0" + id;
				Object ch = Model.find("Charger" + id);
				if (p > nc)
					ch.input.close();
				else
					ch.input.open();
			}
			stoptime(2060);
			runfunction(1);
			Table cr = Table("Cars");
			double sw = 0;
			int n0 = 0;
			int n15 = 0;
			int started = 0;
			int maxch = 0;
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
				if (cr[k][5] > maxch)
					maxch = cr[k][5];
				ws.push(w);
			}
			ws.sort();
			double hq = (n - 1) * 0.95;
			int lo = Math.floor(hq);
			double w95 = ws[lo + 1] + (hq - lo) * (ws[lo + 2] - ws[lo + 1]);
			double dn = n;
			fileopen(RES, "a");
			fpt(string.fromNum(m, 2) + ",1," + string.fromNum(r) + "," + string.fromNum(sa) + "," + string.fromNum(ss) + "," + string.fromNum(nc)
				+ "," + string.fromNum(n) + "," + string.fromNum(sw / dn, 17) + "," + string.fromNum(n0 / dn, 17) + "," + string.fromNum(n15 / dn, 17)
				+ "," + string.fromNum(w95, 17) + "," + string.fromNum(started) + "," + string.fromNum(maxch));
			fpr();
			fileclose();
		}
		fileopen(LOG, "a"); fpt("m " + string.fromNum(m, 2) + " rep " + string.fromNum(r) + " done, N = " + string.fromNum(n)); fpr(); fileclose();
	}
}
cmdexit();
