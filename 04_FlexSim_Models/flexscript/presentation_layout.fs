//  presentation layout on the scripted 52-charger model (no dashboard, so the 3D view fills the window):
// 4 x 13 parking grid fitted to the default camera: 4 columns (x = -13, -8.5 | aisle | 8.5, 13) of 13 chargers 2.2 m apart (y = 0..26.4),
// CarArrivals -> ChargeQueue at the entrance on the aisle line (y = -4), Departed beside the far end (18, 28),
// connectors and charger labels hidden, closed chargers 46..52 grey and closed with input.close(). Logic and connections
// unchanged. Cars = engine replication 1 (+30%), hours. KPI check after a full run (must equal the engine: 3,254 cars,
// P(wait > 15 min) = 0.001229), then the model is reset and run to day 9, 09:30 (201.5 h) so that cars are visible at
// the chargers; FlexSim is left open for the window capture (capture_window.py closes it).
// Verified (help / tests): Model.find, Tools.get, importtable(…, ",", "."), Table(name), Table.setSize, [][],
// Object.setLocation, Object.color + Color.gray, switch_hideconnectors, switch_hidelabel, Object.input.close/open,
// labelProperties, stoptime, resetmodel, runfunction, savebyname, fileopen/fpt/fpr/fileclose, string.fromNum.
string LOG = "C:/ev/out/b8_layout_kpi.txt";
fileopen(LOG, "w"); fpt("start layout"); fpr(); fileclose();
Object src = Model.find("CarArrivals");
Object q = Model.find("ChargeQueue");
Object snk = Model.find("Departed");
treenode carsData = Tools.get("GlobalTable", "Cars").find(">variables/data");
importtable(carsData, "C:/ev/in/trace_rep1_c42_m1.3.csv", 1, 0, ",", ".");
Table cars = Table("Cars");
int n = cars.numRows;
cars.setSize(n, 6);
src.setLocation(-5, -4, 0);
q.setLocation(0, -4, 0);
snk.setLocation(18, 28, 0);
switch_hideconnectors(src, 1);
switch_hideconnectors(q, 1);
switch_hideconnectors(snk, 1);
Array colsX = [-13, -8.5, 8.5, 13];
for (int p = 1; p <= 52; p++) {
	string id = string.fromNum(p);
	if (p < 10)
		id = "0" + id;
	Object ch = Model.find("Charger" + id);
	int col = (p - 1) % 13;
	int row = Math.floor((p - 1) / 13);
	ch.setLocation(colsX[row + 1], col * 2.2, 0);
	switch_hideconnectors(ch, 1);
	switch_hidelabel(ch, 1);
	if (p > 45)
		ch.color = Color.gray;
}
for (int pass = 1; pass <= 2; pass++) {
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
		if (p > 45)
			ch.input.close();
		else
			ch.input.open();
	}
	if (pass == 1) {
		stoptime(2060);
		runfunction(1);
		int started = 0;
		int n15 = 0;
		for (int k = 1; k <= n; k++) {
			if (cars[k][4] >= 0) {
				started++;
				if ((cars[k][4] - cars[k][1]) * 60 > 15)
					n15++;
			}
		}
		double dn = started;
		fileopen(LOG, "a");
		fpt("KPI after layout change (hours, c = 45, 46-52 closed): cars = " + string.fromNum(n) + ", started = " + string.fromNum(started)
			+ ", P(wait > 15 min) = " + string.fromNum(n15 / dn, 6));
		fpr();
		fileclose();
		savebyname(model(), "C:/ev/models/ev_d4b_present_c45.fsm");
		savebyname(model(), "C:/ev/models/ev_d4b_present_c45.fsx");
	} else {
		stoptime(201.5);
		runfunction(1);
		fileopen(LOG, "a"); fpt("stopped at " + string.fromNum(Model.time, 2) + " h for the 3D capture; cars served so far " + string.fromNum(q.served)); fpr(); fileclose();
	}
}


repaintall();
fileopen("C:/ev/out/b8_ready.txt", "w"); fpt("ready"); fpr(); fileclose();

