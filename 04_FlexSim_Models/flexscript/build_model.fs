// : build the EV-charging model by FlexScript. Model time unit = 1 hour (same numbers as the engine).
// Global Tables: ArrRate48, BandOfHour24, ServiceBand1..6, Scenario (importtable from CSV with explicit "," / "."
// separators - tested bit-exact in B0c), Cars (filled per replication: 1 arr_h, 2 svc_h, 3 band, 4 start_h, 5 charger,
// 6 spare). Objects: Source CarArrivals -> Queue ChargeQueue (FIFO, capacity 1e6) -> 52 Processors Charger01..52
// (maxcontent 1, separate) -> Sink Departed. Chargers above c are closed with input.close() by the run scripts.
// Code nodes: Source interarrivaltime reads the next arrival from Cars; Processor cycletime records start time and
// charger id of the next car in FIFO order and returns its stay. Their exact text is written to out/code_*.txt.
// Verified (help / tests): Tools.create, treenode.name/find/value/dataType, importtable(…, ",", "."), Table(name),
// Table.setSize/numRows/numCols, Object.create, Object.setLocation, contextdragconnection, labelProperties,
// switch_flexscript, buildnodeflexscript, savebyname, string.fromNum, fileopen/fpt/fpr/fileclose, cmdexit.
string LOG = "C:/ev/out/b2_build_log.txt";
fileopen(LOG, "w"); fpt("start build"); fpr(); fileclose();

Array names = ["ArrRate48", "BandOfHour24", "ServiceBand1", "ServiceBand2", "ServiceBand3", "ServiceBand4", "ServiceBand5",
	"ServiceBand6", "Scenario", "Cars"];
for (int i = 1; i <= names.length; i++) {
	treenode gt = Tools.create("GlobalTable");
	gt.name = names[i];
	treenode d = gt.find(">variables/data");
	if (names[i] != "Cars")
		importtable(d, "C:/ev/in/" + names[i] + ".csv", 1, 0, ",", ".");
	Table t = Table(names[i]);
	if (names[i] == "Cars")
		t.setSize(1, 6);
	fileopen(LOG, "a"); fpt("table " + names[i] + ": " + string.fromNum(t.numRows) + " x " + string.fromNum(t.numCols)); fpr(); fileclose();
}

Object src = Object.create("Source");
src.name = "CarArrivals";
src.setLocation(0, 0, 0);
Object q = Object.create("Queue");
q.name = "ChargeQueue";
q.setLocation(6, 0, 0);
q.find(">variables/maxcontent").value = 1000000;
Object snk = Object.create("Sink");
snk.name = "Departed";
snk.setLocation(56, 0, 0);
contextdragconnection(src, q, "A");
src.nextCar = 0;
q.served = 0;
fileopen(LOG, "a"); fpt("source, queue, sink created"); fpr(); fileclose();

string ct_code = "Object current = ownerobject(c);\nObject item = param(1);\n"
	+ "/* : next car in FIFO order; record start time and charger id; return its stay (h) */\n"
	+ "Object q = Model.find(\"ChargeQueue\");\nint k = q.served + 1;\nq.served = k;\nTable cars = Table(\"Cars\");\n"
	+ "cars[k][4] = Model.time;\ncars[k][5] = current.chargerId;\nreturn cars[k][2];";
for (int i = 1; i <= 52; i++) {
	Object p = Object.create("Processor");
	string id = string.fromNum(i);
	if (i < 10)
		id = "0" + id;
	p.name = "Charger" + id;
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
fileopen(LOG, "a"); fpt("52 chargers created, connected, cycletime code set"); fpr(); fileclose();

treenode iat = src.find(">variables/interarrivaltime");
iat.value = "Object current = ownerobject(c);\n"
	+ "/* : next arrival time from the Cars table (engine inversion or engine trace); none after the last car */\n"
	+ "Table cars = Table(\"Cars\");\nint k = current.nextCar + 1;\nif (k > cars.numRows)\n\treturn 1000000000;\n"
	+ "current.nextCar = k;\nreturn cars[k][1] - Model.time;";
switch_flexscript(iat, 1);
buildnodeflexscript(iat);
fileopen(LOG, "a"); fpt("interarrival code set"); fpr(); fileclose();

fileopen("C:/ev/out/code_source_interarrivaltime.txt", "w"); fpt(iat.value); fpr(); fileclose();
fileopen("C:/ev/out/code_processor_cycletime.txt", "w"); fpt(Model.find("Charger01").find(">variables/cycletime").value); fpr(); fileclose();

resetmodel();
savebyname(model(), "C:/ev/models/ev_d4b.fsm");
savebyname(model(), "C:/ev/models/ev_d4b.fsx");
fileopen(LOG, "a"); fpt("saved ev_d4b.fsm and ev_d4b.fsx"); fpr(); fileclose();
cmdexit();
