//  presentation copy (user request 15 Nov): start from the user's dashboard model ev_d4b_gui_c45.fsm and
// (1) convert the model to SECONDS (FlexSim's model time unit; no command exists to change the unit - getmodelunit only
//     reads it): Cars arrival and stay columns x 3600, stop time 2060 h x 3600 s, KPI wait = (start - arrival) / 60 min;
// (2) re-lay the chargers as a 4 x 13 parking grid with a central aisle (rows y = -9, -5 | aisle | 5, 9; 3.2 m spacing),
//     CarArrivals -> ChargeQueue at the entrance (aisle line), Departed at the exit; NO change to logic or connections;
// (3) hide connection lines (switch_hideconnectors) and charger name labels (switch_hidelabel);
// (4) closed chargers are grey: for c = 45 the seven removed chargers 46..52 are re-created as grey, UNCONNECTED
//     placeholders (no ports, so they never receive a car); for c = 42 the connected chargers 43..45 are closed with
//     input.close() and coloured grey (plus the 46..52 placeholders).
// Parameter: -ncharge 45 | 42 (commandlineparam). Output: out/b7_kpi_c<n>.txt; models/ev_d4b_gui_c<n>_dash_s.fsm/.fsx.
// FlexSim is left open (no cmdexit) so that capture_window.py can photograph the window; it then closes FlexSim.
// Verified (help / tests): commandlineparam, string.toNum/fromNum, Model.find, Table(name), [][], Object.create,
// Object.setLocation, Object.color + Color.gray, switch_hideconnectors, switch_hidelabel, Object.input.close/open,
// stoptime, resetmodel, runfunction, labelProperties, savebyname, fileopen/fpt/fpr/fileclose.
string ncs = commandlineparam("ncharge");
int NC = ncs.toNum();
string LOG = "C:/ev/out/b7_kpi_c" + string.fromNum(NC) + ".txt";
fileopen(LOG, "w"); fpt("start, ncharge = " + string.fromNum(NC)); fpr(); fileclose();

Table cars = Table("Cars");
int n = cars.numRows;
double firstArrH = cars[1][1];
for (int k = 1; k <= n; k++) {
	cars[k][1] = cars[k][1] * 3600;
	cars[k][2] = cars[k][2] * 3600;
	cars[k][4] = -1;
	cars[k][5] = 0;
}
fileopen(LOG, "a"); fpt("converted to seconds: " + string.fromNum(n) + " cars; first arrival " + string.fromNum(firstArrH, 6) + " h -> "
	+ string.fromNum(cars[1][1], 3) + " s"); fpr(); fileclose();

Object src = Model.find("CarArrivals");
Object q = Model.find("ChargeQueue");
Object snk = Model.find("Departed");
src.setLocation(-2, 0, 0);
q.setLocation(4, 0, 0);
snk.setLocation(56, 0, 0);
switch_hideconnectors(src, 1);
switch_hideconnectors(q, 1);
switch_hideconnectors(snk, 1);
Array rowsY = [-9, -5, 5, 9];
for (int p = 1; p <= 52; p++) {
	string id = string.fromNum(p);
	if (p < 10)
		id = "0" + id;
	Object ch = Model.find("Charger" + id);
	if (!ch) {
		ch = Object.create("Processor");
		ch.name = "Charger" + id;
		ch.chargerId = p;
		ch.closedPlaceholder = 1;
	}
	int col = (p - 1) % 13;
	int row = Math.floor((p - 1) / 13);
	ch.setLocation(12 + col * 3.2, rowsY[row + 1], 0);
	switch_hideconnectors(ch, 1);
	switch_hidelabel(ch, 1);
	if (p > NC)
		ch.color = Color.gray;
}
fileopen(LOG, "a"); fpt("layout: 4 x 13 grid, connectors and charger labels hidden, chargers > " + string.fromNum(NC) + " grey"); fpr(); fileclose();

stoptime(2060 * 3600);
resetmodel();
for (int p = 1; p <= 45; p++) {
	string id = string.fromNum(p);
	if (p < 10)
		id = "0" + id;
	Object ch = Model.find("Charger" + id);
	if (p > NC)
		ch.input.close();
	else
		ch.input.open();
}
runfunction(1);
Table cr = Table("Cars");
int started = 0;
int n15 = 0;
int n0 = 0;
double sw = 0;
int maxch = 0;
for (int k = 1; k <= n; k++) {
	if (cr[k][4] >= 0) {
		started++;
		double w = (cr[k][4] - cr[k][1]) / 60;
		sw = sw + w;
		if (w > 0.000000001)
			n0++;
		if (w > 15)
			n15++;
		if (cr[k][5] > maxch)
			maxch = cr[k][5];
	}
}
double dn = started;
fileopen(LOG, "a");
fpt("KPI (seconds model, c = " + string.fromNum(NC) + "): run to " + string.fromNum(Model.time, 1) + " s = " + string.fromNum(Model.time / 3600, 2)
	+ " h; cars = " + string.fromNum(n) + ", started = " + string.fromNum(started) + ", Wq = " + string.fromNum(sw / dn, 6)
	+ " min, P(wait>0) = " + string.fromNum(n0 / dn, 6) + ", P(wait > 15 min) = " + string.fromNum(n15 / dn, 6) + ", max charger id = "
	+ string.fromNum(maxch));
fpr();
fileclose();
savebyname(model(), "C:/ev/models/ev_d4b_gui_c" + string.fromNum(NC) + "_dash_s.fsm");
savebyname(model(), "C:/ev/models/ev_d4b_gui_c" + string.fromNum(NC) + "_dash_s.fsx");
fileopen(LOG, "a"); fpt("saved ev_d4b_gui_c" + string.fromNum(NC) + "_dash_s.fsm/.fsx; window left open for capture"); fpr(); fileclose();
