/* global Color, ListWidget, Font, Keychain, FileManager, Alert, SFSymbol, Size, config, args, Script */
// Chia Monitor for Scriptable — run once inside Scriptable to configure.

const SETTINGS_URL = "chia-monitor-agent-url";
const SETTINGS_TOKEN = "chia-monitor-api-token";
const ALERT_FINGERPRINT = "chia-monitor-alert-fingerprint";
const CACHE_FILE = "chia-monitor-widget-cache.json";
const STALE_AFTER_MINUTES = 30;

const palette = {
  background: "#07110D",
  panel: "#0E1914",
  text: "#F3F8F5",
  secondary: "#8D9B94",
  healthy: "#59DB87",
  warning: "#F2BD5E",
  critical: "#F06D66",
  stale: "#8D9B94",
};

function saved(key) {
  return Keychain.contains(key) ? Keychain.get(key) : "";
}

async function configure() {
  const form = new Alert();
  form.title = "Connect Chia Monitor";
  form.message = "Enter the private Tailscale HTTPS address and API token printed by the miner installer.";
  form.addTextField("https://miner.tailnet.ts.net", saved(SETTINGS_URL));
  form.addSecureTextField("API token", saved(SETTINGS_TOKEN));
  form.addAction("Test and save");
  form.addCancelAction("Cancel");
  const choice = await form.presentAlert();
  if (choice === -1) return false;

  const url = form.textFieldValue(0).trim().replace(/\/$/, "");
  const token = form.textFieldValue(1).trim();
  if (!url.startsWith("https://") || token.length < 16) {
    await showMessage("Invalid configuration", "Use the HTTPS address shown by Tailscale and the complete API token.");
    return configure();
  }

  try {
    await requestData(url, token);
    Keychain.set(SETTINGS_URL, url);
    Keychain.set(SETTINGS_TOKEN, token);
    await showMessage("Connected", "Chia Monitor is ready. Add this script as a Scriptable widget.");
    return true;
  } catch (error) {
    await showMessage("Connection failed", `${error.message}\n\nCheck Tailscale, the agent service, URL and token.`);
    return configure();
  }
}

async function showMessage(title, message) {
  const alert = new Alert();
  alert.title = title;
  alert.message = message;
  alert.addAction("OK");
  await alert.presentAlert();
}

async function requestData(url, token) {
  const request = new Request(`${url}/api/widget`);
  request.headers = { Authorization: `Bearer ${token}`, Accept: "application/json" };
  request.timeoutInterval = 10;
  return request.loadJSON();
}

function cachePath() {
  const fm = FileManager.local();
  return fm.joinPath(fm.documentsDirectory(), CACHE_FILE);
}

function writeCache(data) {
  FileManager.local().writeString(cachePath(), JSON.stringify(data));
}

function readCache() {
  const fm = FileManager.local();
  const path = cachePath();
  if (!fm.fileExists(path)) return null;
  try { return JSON.parse(fm.readString(path)); } catch { return null; }
}

async function loadFarm() {
  const url = saved(SETTINGS_URL);
  const token = saved(SETTINGS_TOKEN);
  if (!url || !token) return { data: null, stale: true, needsSetup: true };
  try {
    const data = await requestData(url, token);
    writeCache(data);
    return { data, stale: isOld(data.updated_at), needsSetup: false, live: true };
  } catch (error) {
    const cached = readCache();
    return { data: cached, stale: true, needsSetup: false, live: false, error: error.message };
  }
}

function isOld(timestamp) {
  const time = timestamp ? new Date(timestamp).getTime() : 0;
  return !time || Date.now() - time > STALE_AFTER_MINUTES * 60 * 1000;
}

function duration(seconds) {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

function statusInfo(data, stale) {
  const status = stale ? "stale" : (data?.status || "critical");
  const labels = { healthy: "HEALTHY", warning: "CHECK FARM", critical: "CRITICAL", stale: "STALE" };
  return { status, label: labels[status], color: new Color(palette[status]) };
}

function addSymbol(stack, name, color, size = 12) {
  const symbol = SFSymbol.named(name);
  symbol.applyFont(Font.systemFont(size));
  const image = stack.addImage(symbol.image);
  image.tintColor = color;
  image.imageSize = new Size(size, size);
  return image;
}

function addMetric(parent, label, value, good = true) {
  const stack = parent.addStack();
  stack.layoutVertically();
  const caption = stack.addText(label);
  caption.font = Font.semiboldMonospacedSystemFont(7);
  caption.textColor = new Color(palette.secondary);
  stack.addSpacer(2);
  const text = stack.addText(value);
  text.font = Font.semiboldSystemFont(11);
  text.textColor = good ? new Color(palette.text) : new Color(palette.critical);
  text.lineLimit = 1;
  text.minimumScaleFactor = 0.65;
  return stack;
}

function baseWidget(info) {
  const widget = new ListWidget();
  widget.backgroundColor = new Color(palette.background);
  widget.setPadding(14, 14, 12, 14);
  widget.url = `scriptable:///run?scriptName=${encodeURIComponent(Script.name())}&action=refresh`;
  widget.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);
  const top = widget.addStack();
  top.centerAlignContent();
  const title = top.addText("CHIA FARM");
  title.font = Font.semiboldMonospacedSystemFont(9);
  title.textColor = new Color(palette.secondary);
  top.addSpacer();
  const dot = top.addText("●");
  dot.font = Font.systemFont(8);
  dot.textColor = info.color;
  top.addSpacer(4);
  const status = top.addText(info.label);
  status.font = Font.semiboldMonospacedSystemFont(8);
  status.textColor = info.color;
  return widget;
}

function buildHomeWidget(data, stale, family) {
  const info = statusInfo(data, stale);
  const widget = baseWidget(info);
  widget.addSpacer(family === "small" ? 8 : 10);

  const scoreRow = widget.addStack();
  scoreRow.bottomAlignContent();
  const score = scoreRow.addText(String(data?.score ?? 0));
  score.font = Font.boldRoundedSystemFont(family === "small" ? 36 : 42);
  score.textColor = new Color(palette.text);
  score.minimumScaleFactor = 0.7;
  scoreRow.addSpacer(3);
  const suffix = scoreRow.addText("/100");
  suffix.font = Font.mediumMonospacedSystemFont(9);
  suffix.textColor = new Color(palette.secondary);
  scoreRow.addSpacer();
  addSymbol(scoreRow, stale ? "clock.badge.exclamationmark" : "leaf.fill", info.color, 18);

  const alert = data?.alerts?.[0]?.message || (stale ? "Last saved reading" : "Everything is farming normally");
  const alertText = widget.addText(alert);
  alertText.font = Font.systemFont(10);
  alertText.textColor = new Color(palette.secondary);
  alertText.lineLimit = family === "large" ? 2 : 1;
  widget.addSpacer();

  const row = widget.addStack();
  addMetric(row, "FARMER", data?.farmer ? "Online" : "Offline", Boolean(data?.farmer));
  row.addSpacer();
  addMetric(row, "PLOTS", String(data?.plots ?? 0));
  if (family !== "small") {
    row.addSpacer();
    addMetric(row, "SIZE", `${data?.tib ?? 0} TiB`);
  }

  if (family === "large") {
    widget.addSpacer(12);
    const divider = widget.addStack();
    divider.backgroundColor = new Color("#1D2C25");
    divider.size = new Size(0, 1);
    widget.addSpacer(12);
    const second = widget.addStack();
    addMetric(second, "NODE", data?.synced ? "Synced" : "Not synced", Boolean(data?.synced));
    second.addSpacer();
    addMetric(second, "HARVESTERS", `${data?.harvesters?.online ?? 0} / ${data?.harvesters?.total ?? 0}`, data?.harvesters?.online === data?.harvesters?.total);
    second.addSpacer();
    addMetric(second, "TIME TO WIN", `~${duration(data?.etw_seconds)}`);
    widget.addSpacer(12);
    const wallet = widget.addStack();
    wallet.backgroundColor = new Color(palette.panel);
    wallet.cornerRadius = 10;
    wallet.setPadding(9, 10, 9, 10);
    addSymbol(wallet, "wallet.bifold.fill", info.color, 13);
    wallet.addSpacer(8);
    const balance = wallet.addText(`${Number(data?.balance_xch ?? 0).toFixed(3)} XCH`);
    balance.font = Font.semiboldSystemFont(12);
    balance.textColor = new Color(palette.text);
  }

  const updated = widget.addText(stale ? "Tap to retry · cached data" : `Updated ${formatTime(data?.updated_at)}`);
  updated.font = Font.mediumMonospacedSystemFont(7);
  updated.textColor = new Color(palette.secondary);
  updated.minimumScaleFactor = 0.7;
  return widget;
}

function buildAccessory(data, stale, family) {
  const widget = new ListWidget();
  const info = statusInfo(data, stale);
  if (family === "accessoryInline") {
    const text = widget.addText(`Chia ${info.label} · ${data?.plots ?? 0} plots`);
    text.font = Font.mediumSystemFont(12);
  } else if (family === "accessoryCircular") {
    const text = widget.addText(String(data?.score ?? 0));
    text.font = Font.boldRoundedSystemFont(22);
    text.centerAlignText();
  } else {
    const title = widget.addText(`Chia · ${info.label}`);
    title.font = Font.semiboldSystemFont(12);
    const detail = widget.addText(`${data?.plots ?? 0} plots · ${data?.tib ?? 0} TiB`);
    detail.font = Font.systemFont(11);
  }
  widget.url = `scriptable:///run?scriptName=${encodeURIComponent(Script.name())}&action=refresh`;
  return widget;
}

function buildSetupWidget() {
  const widget = new ListWidget();
  widget.backgroundColor = new Color(palette.background);
  widget.setPadding(14, 14, 14, 14);
  const title = widget.addText("CHIA MONITOR");
  title.font = Font.semiboldMonospacedSystemFont(9);
  title.textColor = new Color(palette.healthy);
  widget.addSpacer();
  const text = widget.addText("Run this script once in Scriptable to connect your miner.");
  text.font = Font.semiboldSystemFont(13);
  text.textColor = new Color(palette.text);
  text.minimumScaleFactor = 0.7;
  widget.url = `scriptable:///run?scriptName=${encodeURIComponent(Script.name())}`;
  return widget;
}

function formatTime(timestamp) {
  if (!timestamp) return "—";
  try { return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
  catch { return "—"; }
}

async function notifyForAlerts(data, live) {
  if (!live) return;
  const alerts = data?.alerts || [];
  if (!alerts.length) {
    if (Keychain.contains(ALERT_FINGERPRINT)) Keychain.remove(ALERT_FINGERPRINT);
    return;
  }
  const fingerprint = alerts.map(item => item.message).join("|");
  if (saved(ALERT_FINGERPRINT) === fingerprint) return;
  const notification = new Notification();
  notification.identifier = "chia-monitor-farm-alert";
  notification.threadIdentifier = "chia-monitor";
  notification.title = "Chia farm needs attention";
  notification.body = alerts[0].message;
  notification.sound = "alert";
  notification.openURL = `scriptable:///run?scriptName=${encodeURIComponent(Script.name())}&action=refresh`;
  await notification.schedule();
  Keychain.set(ALERT_FINGERPRINT, fingerprint);
}

if (config.runsInApp && args.queryParameters?.action !== "refresh") {
  const menu = new Alert();
  menu.title = "Chia Monitor";
  menu.message = saved(SETTINGS_URL) ? "Preview the widget or change the miner connection." : "Connect the widget to your miner.";
  menu.addAction(saved(SETTINGS_URL) ? "Preview" : "Configure");
  if (saved(SETTINGS_URL)) menu.addAction("Change connection");
  menu.addCancelAction("Cancel");
  const choice = await menu.presentSheet();
  if (choice === -1) Script.complete();
  if (!saved(SETTINGS_URL) || choice === 1) await configure();
}

const result = await loadFarm();
const family = config.widgetFamily || "medium";
const widget = result.needsSetup
  ? buildSetupWidget()
  : family.startsWith("accessory")
    ? buildAccessory(result.data, result.stale, family)
    : buildHomeWidget(result.data, result.stale, family);

await notifyForAlerts(result.data, result.live);
if (config.runsInWidget) Script.setWidget(widget);
else if (family === "small") await widget.presentSmall();
else if (family === "large") await widget.presentLarge();
else await widget.presentMedium();
Script.complete();
