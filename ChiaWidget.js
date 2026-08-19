/* global Color, ListWidget, Font, Keychain, config, Script */
// Chia Monitor widget for Scriptable. Edit these two values.
const AGENT_URL = "http://100.x.y.z:8926";
const API_TOKEN = "replace-with-your-api-token";

const req = new Request(`${AGENT_URL}/api/widget`);
req.headers = { Authorization: `Bearer ${API_TOKEN}` };
req.timeoutInterval = 8;

let data;
try { data = await req.loadJSON(); }
catch { data = { score: 0, status: "offline", farmer: false, synced: false, plots: 0, tib: 0, harvesters: { online: 0, total: 0 }, alerts: [{ message: "Agent unreachable" }] }; }

const colors = { healthy: "#59DB87", warning: "#F2BD5E", critical: "#F06D66", offline: "#F06D66" };
const accent = new Color(colors[data.status] || colors.critical);
const widget = new ListWidget();
widget.backgroundColor = new Color("#08110D");
widget.setPadding(14, 14, 12, 14);

const top = widget.addStack(); top.centerAlignContent();
const title = top.addText("CHIA FARM"); title.font = Font.semiboldMonospacedSystemFont(10); title.textColor = new Color("#8D9B94");
top.addSpacer();
const badge = top.addText(`● ${String(data.status).toUpperCase()}`); badge.font = Font.semiboldSystemFont(9); badge.textColor = accent;
widget.addSpacer(8);
const score = widget.addText(`${data.score}`); score.font = Font.boldRoundedSystemFont(38); score.textColor = Color.white(); score.minimumScaleFactor = 0.7;
const label = widget.addText("HEALTH SCORE"); label.font = Font.mediumMonospacedSystemFont(8); label.textColor = new Color("#708078");
widget.addSpacer();
const row = widget.addStack(); row.layoutHorizontally();
for (const [name, value, ok] of [["FARMER", data.farmer ? "Online" : "Offline", data.farmer], ["PLOTS", String(data.plots), true], ["SIZE", `${data.tib} TiB`, true]]) {
  const cell = row.addStack(); cell.layoutVertically();
  const l = cell.addText(name); l.font = Font.mediumMonospacedSystemFont(7); l.textColor = new Color("#66756D");
  const v = cell.addText(value); v.font = Font.semiboldSystemFont(11); v.textColor = ok ? Color.white() : accent;
  row.addSpacer();
}

if (data.alerts?.length) {
  const key = `chia-alert-${data.alerts[0].message}`;
  if (!Keychain.contains(key)) { const n = new Notification(); n.title = "Chia farm needs attention"; n.body = data.alerts[0].message; await n.schedule(); Keychain.set(key, new Date().toISOString()); }
}
widget.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);
if (config.runsInWidget) Script.setWidget(widget); else await widget.presentMedium();
Script.complete();
