// : M/M/3 check. Source -> Queue -> 3 Processors (maxcontent 1) -> Sink. Time unit = minutes (numbers only).
// Arrivals exponential mean 10 min, service exponential mean 25 min: rho = 0.1 * 25 / 3 = 0.833.
// Replication r (1..10) uses stream 2r-1 for arrivals and 2r for service (no seed command exists in the help; distinct
// streams give independent replications). Warm-up 200 h = 12000 min (resetstats), then 2000 h = 120000 min measured.
// Verified (help): Object.create, contextdragconnection, Object.setLocation, treenode.find/dataType/value, switch_flexscript,
// buildnodeflexscript, resetmodel, stoptime, runfunction, resetstats, Object.stats (staytime/content/input) + TrackedVariable
// average/value, string.fromNum, Array.push, Model.time, fileopen/fpt/fpr/fileclose, savebyname, model, cmdexit.
Object src = Object.create("Source");
Object q = Object.create("Queue");
Object snk = Object.create("Sink");
src.name = "Arrivals";
q.name = "WaitQueue";
snk.name = "Departures";
src.setLocation(0, 0, 0);
q.setLocation(6, 0, 0);
snk.setLocation(20, 0, 0);
contextdragconnection(src, q, "A");
Array procs = [];
for (int i = 1; i <= 3; i++) {
	Object p = Object.create("Processor");
	p.name = "Server" + string.fromNum(i);
	p.setLocation(13, (i - 2) * 4, 0);
	contextdragconnection(q, p, "A");
	contextdragconnection(p, snk, "A");
	procs.push(p);
}
treenode iat = src.find(">variables/interarrivaltime");

fileopen("C:/ev/out/mm3_check.csv", "w");
fpt("rep,stream_arrival,stream_service,Wq_min,Lq,busy_servers,L,departures,throughput_per_h,warmup_min,measured_min");
fpr();
for (int r = 1; r <= 10; r++) {
	int sa = 2 * r - 1;
	int ss = 2 * r;
	iat.value = "Object current = ownerobject(c);\nreturn exponential(0, 10, " + string.fromNum(sa) + ");";
	switch_flexscript(iat, 1);
	buildnodeflexscript(iat);
	for (int i = 1; i <= 3; i++) {
		Object p = procs[i];
		treenode ct = p.find(">variables/cycletime");
		ct.dataType = 2;
		ct.value = "Object current = ownerobject(c);\nObject item = param(1);\nreturn exponential(0, 25, " + string.fromNum(ss) + ");";
		switch_flexscript(ct, 1);
		buildnodeflexscript(ct);
	}
	resetmodel();
	stoptime(12000);
	runfunction(1);
	resetstats();
	stoptime(132000);
	runfunction(1);
	double wq = q.stats.staytime.average;
	double lq = q.stats.content.average;
	double busy = 0;
	for (int i = 1; i <= 3; i++) {
		Object p = procs[i];
		busy = busy + p.stats.content.average;
	}
	double dep = snk.stats.input.value;
	fpt(string.fromNum(r) + "," + string.fromNum(sa) + "," + string.fromNum(ss) + "," + string.fromNum(wq, 6) + ","
		+ string.fromNum(lq, 6) + "," + string.fromNum(busy, 6) + "," + string.fromNum(lq + busy, 6) + "," + string.fromNum(dep)
		+ "," + string.fromNum(dep / 2000, 6) + ",12000," + string.fromNum(Model.time - 12000, 3));
	fpr();
}
fileclose();
resetmodel();
savebyname(model(), "C:/ev/models/mm3.fsm");
savebyname(model(), "C:/ev/models/mm3.fsx");
cmdexit();
