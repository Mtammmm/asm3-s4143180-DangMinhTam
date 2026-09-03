const MAX_FILE_SIZE = 10 * 1024 * 1024;
const MAX_PREVIEW_ROWS = 100;

const elements = {
  authCloseButton: document.querySelector("#authCloseButton"),
  authDialog: document.querySelector("#authDialog"),
  avatarChooseButton: document.querySelector("#avatarChooseButton"),
  avatarFileInput: document.querySelector("#avatarFileInput"),
  avatarMessage: document.querySelector("#avatarMessage"),
  browseButton: document.querySelector("#browseButton"),
  dataTable: document.querySelector("#dataTable"),
  datasetCount: document.querySelector("#datasetCount"),
  datasetDetailContent: document.querySelector("#datasetDetailContent"),
  datasetDetailLoading: document.querySelector("#datasetDetailLoading"),
  datasetDetailStats: document.querySelector("#datasetDetailStats"),
  datasetDetailTable: document.querySelector("#datasetDetailTable"),
  datasetDialog: document.querySelector("#datasetDialog"),
  datasetDialogClose: document.querySelector("#datasetDialogClose"),
  datasetDialogMeta: document.querySelector("#datasetDialogMeta"),
  datasetDialogTitle: document.querySelector("#datasetDialogTitle"),
  datasetEmpty: document.querySelector("#datasetEmpty"),
  datasetError: document.querySelector("#datasetError"),
  datasetErrorMessage: document.querySelector("#datasetErrorMessage"),
  datasetList: document.querySelector("#datasetList"),
  datasetLoading: document.querySelector("#datasetLoading"),
  datasetSearchInput: document.querySelector("#datasetSearchInput"),
  deleteDialog: document.querySelector("#deleteDialog"),
  deleteDialogMessage: document.querySelector("#deleteDialogMessage"),
  deleteForm: document.querySelector("#deleteForm"),
  emptyState: document.querySelector("#emptyState"),
  fileInput: document.querySelector("#fileInput"),
  fileMeta: document.querySelector("#fileMeta"),
  forgotForm: document.querySelector("#forgotForm"),
  guestAuth: document.querySelector("#guestAuth"),
  heroSampleButton: document.querySelector("#heroSampleButton"),
  loginForm: document.querySelector("#loginForm"),
  loadSampleButton: document.querySelector("#loadSampleButton"),
  mainContent: document.querySelector("#main-content"),
  message: document.querySelector("#message"),
  memberAnalyzeButton: document.querySelector("#memberAnalyzeButton"),
  memberAnalyzeNavButton: document.querySelector("#memberAnalyzeNavButton"),
  memberApp: document.querySelector("#memberApp"),
  memberAvatar: document.querySelector("#memberAvatar"),
  memberDashboardButton: document.querySelector("#memberDashboardButton"),
  memberDashboardView: document.querySelector("#memberDashboardView"),
  memberGreetingName: document.querySelector("#memberGreetingName"),
  memberNav: document.querySelector("#memberNav"),
  memberProfileEmail: document.querySelector("#memberProfileEmail"),
  memberProfileName: document.querySelector("#memberProfileName"),
  memberProfileNavButton: document.querySelector("#memberProfileNavButton"),
  memberProfileView: document.querySelector("#memberProfileView"),
  memberSampleButton: document.querySelector("#memberSampleButton"),
  memberUploadButton: document.querySelector("#memberUploadButton"),
  primaryNav: document.querySelector(".primary-nav"),
  profileAvatarPreview: document.querySelector("#profileAvatarPreview"),
  profileBackButton: document.querySelector("#profileBackButton"),
  profileEmail: document.querySelector("#profileEmail"),
  profileFullName: document.querySelector("#profileFullName"),
  profileNameForm: document.querySelector("#profileNameForm"),
  profileNameMessage: document.querySelector("#profileNameMessage"),
  queryColumn: document.querySelector("#queryColumn"),
  queryForm: document.querySelector("#queryForm"),
  queryMessage: document.querySelector("#queryMessage"),
  queryOperator: document.querySelector("#queryOperator"),
  queryValue: document.querySelector("#queryValue"),
  queryValueField: document.querySelector("#queryValueField"),
  recentAnalyzeButton: document.querySelector("#recentAnalyzeButton"),
  refreshDatasetsButton: document.querySelector("#refreshDatasetsButton"),
  retryDatasetsButton: document.querySelector("#retryDatasetsButton"),
  resetButton: document.querySelector("#resetButton"),
  results: document.querySelector("#results"),
  rowSummary: document.querySelector("#rowSummary"),
  passwordForm: document.querySelector("#passwordForm"),
  passwordMessage: document.querySelector("#passwordMessage"),
  searchInput: document.querySelector("#searchInput"),
  signOutButton: document.querySelector("#signOutButton"),
  skipLink: document.querySelector("#skipLink"),
  signupForm: document.querySelector("#signupForm"),
  statsGrid: document.querySelector("#statsGrid"),
  themeToggle: document.querySelector("#themeToggle"),
  toast: document.querySelector("#toast"),
  uploadZone: document.querySelector("#uploadZone"),
  userAuth: document.querySelector("#userAuth"),
  guestFooter: document.querySelector("#guestFooter"),
  userInitials: document.querySelector("#userInitials"),
  userName: document.querySelector("#userName")
};

let currentDataset = { headers: [], rows: [] };
let currentUser = null;
let datasetSummaries = [];
let selectedDataset = null;
let pendingDeleteDataset = null;

elements.browseButton.addEventListener("click", () => elements.fileInput.click());
elements.fileInput.addEventListener("change", (event) => handleFile(event.target.files[0]));
elements.loadSampleButton.addEventListener("click", loadSampleData);
elements.heroSampleButton.addEventListener("click", loadSampleData);
elements.resetButton.addEventListener("click", resetWorkspace);
elements.searchInput.addEventListener("input", filterRows);
elements.themeToggle.addEventListener("click", toggleTheme);
elements.authCloseButton.addEventListener("click", closeAuthDialog);
elements.authDialog.addEventListener("click", handleDialogBackdropClick);
elements.loginForm.addEventListener("submit", handleLogin);
elements.signupForm.addEventListener("submit", handleSignup);
elements.forgotForm.addEventListener("submit", handleForgotPassword);
elements.signOutButton.addEventListener("click", signOut);
elements.datasetDialogClose.addEventListener("click", () => elements.datasetDialog.close());
elements.datasetSearchInput.addEventListener("input", renderDatasetLibrary);
elements.deleteForm.addEventListener("submit", confirmDeleteDataset);
document.querySelector("#cancelDeleteButton").addEventListener("click", () => elements.deleteDialog.close());
elements.queryForm.addEventListener("submit", runDatasetQuery);
elements.queryOperator.addEventListener("change", updateQueryValueVisibility);
elements.refreshDatasetsButton.addEventListener("click", loadDatasetLibrary);
elements.retryDatasetsButton.addEventListener("click", loadDatasetLibrary);
elements.memberAnalyzeButton.addEventListener("click", showMemberAnalyzer);
elements.memberAnalyzeNavButton.addEventListener("click", showMemberAnalyzer);
elements.memberDashboardButton.addEventListener("click", showMemberDashboard);
elements.memberProfileNavButton.addEventListener("click", showMemberProfile);
elements.profileBackButton.addEventListener("click", showMemberDashboard);
elements.profileNameForm.addEventListener("submit", handleProfileNameUpdate);
elements.passwordForm.addEventListener("submit", handlePasswordChange);
elements.avatarChooseButton.addEventListener("click", () => elements.avatarFileInput.click());
elements.avatarFileInput.addEventListener("change", handleAvatarUpload);
elements.memberUploadButton.addEventListener("click", () => {
  showMemberAnalyzer();
  elements.fileInput.click();
});
elements.memberSampleButton.addEventListener("click", () => {
  showMemberAnalyzer();
  window.setTimeout(loadSampleData, 50);
});
elements.recentAnalyzeButton.addEventListener("click", showMemberAnalyzer);
document.querySelectorAll("[data-member-view]").forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.memberView === "analyzer") showMemberAnalyzer();
    else if (button.dataset.memberView === "profile") showMemberProfile();
    else showMemberDashboard();
  });
});
document.querySelectorAll("[data-auth-view]").forEach((button) => {
  button.addEventListener("click", () => openAuthDialog(button.dataset.authView));
});

initializeTheme();
initializeAuth();

["dragenter", "dragover"].forEach((eventName) => {
  elements.uploadZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.uploadZone.classList.add("is-dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  elements.uploadZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    elements.uploadZone.classList.remove("is-dragging");
  });
});

elements.uploadZone.addEventListener("drop", (event) => handleFile(event.dataTransfer.files[0]));

function handleFile(file) {
  clearMessage();

  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".csv")) {
    showMessage("Please choose a file with a .csv extension.", "error");
    return;
  }
  if (file.size > MAX_FILE_SIZE) {
    showMessage("The file exceeds the 10 MB limit.", "error");
    return;
  }
  showMessage(`Reading ${file.name} and preparing its analysis.`, "loading");

  const reader = new FileReader();
  reader.addEventListener("load", async () => {
    try {
      const dataset = parseCSV(String(reader.result));
      if (!dataset.headers.length || !dataset.rows.length) throw new Error("The file does not contain valid data.");
      displayDataset(dataset, file.name, file.size);
      if (currentUser) {
        await DatasetApi.createDataset({ owner: currentUser.email, name: file.name, size: file.size, headers: dataset.headers, rows: dataset.rows, file, contentType: file.type || "text/csv" });
        await loadDatasetLibrary({ silent: true });
      }
      showMessage(`${file.name} was loaded successfully.`, "success");
    } catch (error) {
      showMessage(error.message || "This CSV file could not be read.", "error");
    }
  });
  reader.addEventListener("error", () => showMessage("The file could not be read. Please try again.", "error"));
  reader.readAsText(file, "UTF-8");
}

function parseCSV(text) {
  const source = text.replace(/^\uFEFF/, "");
  const delimiter = detectDelimiter(source);
  const lines = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1];

    if (char === '"' && quoted && next === '"') {
      field += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === delimiter && !quoted) {
      row.push(field.trim());
      field = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(field.trim());
      if (row.some((value) => value !== "")) lines.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }

  row.push(field.trim());
  if (row.some((value) => value !== "")) lines.push(row);
  if (!lines.length) return { headers: [], rows: [] };

  const [headers, ...rows] = lines;
  const normalizedHeaders = headers.map((header, index) => header || `Column ${index + 1}`);
  return {
    headers: normalizedHeaders,
    rows: rows.map((values) => normalizedHeaders.map((_, index) => values[index] ?? ""))
  };
}

function detectDelimiter(text) {
  const candidates = [",", ";", "\t", "|"];
  const counts = new Map(candidates.map((candidate) => [candidate, 0]));
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    const next = text[index + 1];
    if (character === '"' && quoted && next === '"') {
      index += 1;
      continue;
    }
    if (character === '"') {
      quoted = !quoted;
      continue;
    }
    if (!quoted && (character === "\n" || character === "\r")) break;
    if (!quoted && counts.has(character)) counts.set(character, counts.get(character) + 1);
  }

  return candidates.reduce((best, candidate) => counts.get(candidate) > counts.get(best) ? candidate : best, ",");
}

function displayDataset(dataset, fileName, fileSize) {
  currentDataset = dataset;
  elements.searchInput.value = "";
  elements.fileMeta.textContent = `${fileName} · ${formatBytes(fileSize)}`;
  renderStats(dataset);
  renderTable(dataset.rows.slice(0, MAX_PREVIEW_ROWS));
  elements.results.hidden = false;
  elements.emptyState.hidden = true;
  elements.results.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderStats(dataset) {
  const totalCells = dataset.headers.length * dataset.rows.length;
  const emptyCells = dataset.rows.flat().filter((value) => value === "").length;
  const completePercent = totalCells ? Math.round(((totalCells - emptyCells) / totalCells) * 100) : 0;
  const stats = [
    ["Rows", dataset.rows.length.toLocaleString("en-US"), "records detected", "rows"],
    ["Columns", dataset.headers.length.toLocaleString("en-US"), "fields available", "columns"],
    ["Empty cells", emptyCells.toLocaleString("en-US"), emptyCells ? "review recommended" : "nothing missing", "empty"],
    ["Completeness", `${completePercent}%`, completePercent >= 90 ? "healthy dataset" : "needs attention", "complete"]
  ];

  elements.statsGrid.replaceChildren(...stats.map(([label, value, hint, type]) => {
    const card = document.createElement("article");
    card.className = `stat-card stat-${type}`;
    const top = document.createElement("div");
    const labelElement = document.createElement("span");
    const valueElement = document.createElement("strong");
    const hintElement = document.createElement("small");
    labelElement.textContent = label;
    valueElement.textContent = value;
    hintElement.textContent = hint;
    top.append(labelElement);
    card.append(top, valueElement, hintElement);
    return card;
  }));
}

function renderTable(rows) {
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  currentDataset.headers.forEach((header) => {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = header;
    headerRow.append(th);
  });
  thead.append(headerRow);

  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    row.forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value || "Empty";
      if (!value) td.className = "is-empty";
      tr.append(td);
    });
    tbody.append(tr);
  });

  elements.dataTable.replaceChildren(thead, tbody);
  const shown = Math.min(rows.length, MAX_PREVIEW_ROWS);
  elements.rowSummary.textContent = rows.length
    ? `Showing ${shown} of ${currentDataset.rows.length} rows`
    : "No matching rows found";
}

function filterRows(event) {
  const query = event.target.value.trim().toLocaleLowerCase("en");
  const filtered = query
    ? currentDataset.rows.filter((row) => row.some((value) => value.toLocaleLowerCase("en").includes(query)))
    : currentDataset.rows;
  renderTable(filtered.slice(0, MAX_PREVIEW_ROWS));
}

async function loadSampleData() {
  const sample = [
    ["order_id", "customer", "city", "amount", "status"],
    ["ORD-1001", "Alex Morgan", "Melbourne", "1250000", "Completed"],
    ["ORD-1002", "Taylor Lee", "Sydney", "890000", "Processing"],
    ["ORD-1003", "Jordan Smith", "Brisbane", "", "Pending"],
    ["ORD-1004", "Casey Brown", "Perth", "2140000", "Completed"],
    ["ORD-1005", "Jamie Wilson", "Adelaide", "760000", "Completed"]
  ];
  const [headers, ...rows] = sample;
  displayDataset({ headers, rows }, "sample-orders.csv", 348);
  if (currentUser) {
    try {
      const sampleSource = [headers, ...rows].map((record) => record.join(",")).join("\n");
      const sampleFile = new Blob([sampleSource], { type: "text/csv" });
      await DatasetApi.createDataset({ owner: currentUser.email, name: "sample-orders.csv", size: sampleFile.size, headers, rows, file: sampleFile, contentType: "text/csv" });
      await loadDatasetLibrary({ silent: true });
    } catch (error) {
      showMessage(error.message, "error");
      return;
    }
  }
  showMessage("Sample data is ready for you to explore.", "success");
}

function resetWorkspace() {
  currentDataset = { headers: [], rows: [] };
  elements.fileInput.value = "";
  elements.results.hidden = true;
  elements.emptyState.hidden = false;
  clearMessage();
  elements.uploadZone.scrollIntoView({ behavior: "smooth", block: "center" });
}

function showMessage(text, type) {
  elements.message.textContent = text;
  elements.message.className = `message ${type}`;
  elements.message.hidden = false;
}

function clearMessage() {
  elements.message.hidden = true;
  elements.message.textContent = "";
  elements.message.className = "message";
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB"];
  const unitIndex = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / (1024 ** unitIndex)).toFixed(unitIndex ? 1 : 0)} ${units[unitIndex]}`;
}

async function loadDatasetLibrary(options = {}) {
  if (!currentUser) return;
  const silent = options && options.silent === true;
  if (!silent) {
    elements.datasetLoading.hidden = false;
    elements.datasetList.hidden = true;
    elements.datasetEmpty.hidden = true;
    elements.datasetError.hidden = true;
  }
  try {
    datasetSummaries = await DatasetApi.listDatasets(currentUser.email);
    elements.datasetError.hidden = true;
    renderDatasetLibrary();
  } catch (error) {
    elements.datasetErrorMessage.textContent = error.message || "Please try again.";
    elements.datasetError.hidden = false;
    elements.datasetList.hidden = true;
    elements.datasetEmpty.hidden = true;
  } finally {
    elements.datasetLoading.hidden = true;
  }
}

function renderDatasetLibrary() {
  const query = elements.datasetSearchInput.value.trim().toLocaleLowerCase("en");
  const datasets = query
    ? datasetSummaries.filter((dataset) => dataset.name.toLocaleLowerCase("en").includes(query))
    : datasetSummaries;
  elements.datasetCount.textContent = `${datasets.length} ${datasets.length === 1 ? "dataset" : "datasets"}`;
  elements.datasetList.hidden = datasets.length === 0;
  elements.datasetEmpty.hidden = datasets.length > 0;
  if (!datasets.length) {
    elements.datasetEmpty.querySelector("strong").textContent = query ? "No matching datasets" : "No recent files yet";
    elements.datasetEmpty.querySelector("p").textContent = query
      ? "Try a different file name or clear the search field."
      : "Analyze your first CSV to populate this workspace.";
    return;
  }

  elements.datasetList.replaceChildren(...datasets.map((dataset) => {
    const row = document.createElement("article");
    row.className = "dataset-row";
    const identity = document.createElement("div");
    identity.className = "dataset-identity";
    const mark = document.createElement("span");
    mark.textContent = "CSV";
    const copy = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = dataset.name;
    const meta = document.createElement("small");
    meta.textContent = `${formatBytes(dataset.size)} / ${formatDate(dataset.createdAt)}`;
    const status = document.createElement("span");
    status.className = `dataset-status ${dataset.status || "processing"}`;
    status.textContent = dataset.status || "processing";
    copy.append(name, meta, status);
    identity.append(mark, copy);

    const metrics = document.createElement("div");
    metrics.className = "dataset-row-metrics";
    if (dataset.status === "ready" && dataset.stats) {
      metrics.innerHTML = `<span><strong>${dataset.stats.rows.toLocaleString("en-US")}</strong> rows</span><span><strong>${dataset.stats.columns}</strong> columns</span><span><strong>${dataset.stats.completeness}%</strong> complete</span>`;
    } else {
      metrics.classList.add("dataset-processing-copy");
      metrics.textContent = dataset.status === "failed" ? "Processing failed. Delete the dataset or upload it again." : "Statistics are being prepared.";
    }

    const actions = document.createElement("div");
    actions.className = "dataset-row-actions";
    const viewButton = document.createElement("button");
    viewButton.className = "button button-secondary compact-button";
    viewButton.type = "button";
    viewButton.textContent = "View and query";
    viewButton.disabled = dataset.status !== "ready";
    viewButton.addEventListener("click", () => openDatasetDetails(dataset.id));
    const deleteButton = document.createElement("button");
    deleteButton.className = "dataset-delete-button";
    deleteButton.type = "button";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", () => openDeleteDialog(dataset));
    actions.append(viewButton, deleteButton);
    row.append(identity, metrics, actions);
    return row;
  }));
}

async function openDatasetDetails(datasetId) {
  elements.datasetDialog.showModal();
  elements.datasetDetailLoading.textContent = "Loading dataset details";
  elements.datasetDetailLoading.hidden = false;
  elements.datasetDetailContent.hidden = true;
  elements.queryMessage.textContent = "";
  try {
    selectedDataset = await DatasetApi.getDataset(datasetId, currentUser.email);
    elements.datasetDialogTitle.textContent = selectedDataset.name;
    elements.datasetDialogMeta.textContent = `${formatBytes(selectedDataset.size)} / ${formatDate(selectedDataset.createdAt)}`;
    renderDatasetDetailStats(selectedDataset.stats);
    elements.queryColumn.replaceChildren(...selectedDataset.headers.map((header) => new Option(header, header)));
    renderDataTable(elements.datasetDetailTable, selectedDataset.headers, selectedDataset.rows.slice(0, MAX_PREVIEW_ROWS));
    elements.datasetDetailContent.hidden = false;
  } catch (error) {
    elements.datasetDetailLoading.textContent = error.message || "Dataset details could not be loaded.";
    return;
  }
  elements.datasetDetailLoading.hidden = true;
}

function renderDatasetDetailStats(stats) {
  const values = [["Rows", stats.rows], ["Columns", stats.columns], ["Missing", stats.missingValues], ["Complete", `${stats.completeness}%`]];
  elements.datasetDetailStats.replaceChildren(...values.map(([label, value]) => {
    const item = document.createElement("div");
    const labelElement = document.createElement("span");
    const valueElement = document.createElement("strong");
    labelElement.textContent = label;
    valueElement.textContent = value;
    item.append(labelElement, valueElement);
    return item;
  }));
}

function renderDataTable(table, headers, rows) {
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  headers.forEach((header) => {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = header;
    headerRow.append(cell);
  });
  thead.append(headerRow);
  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tableRow = document.createElement("tr");
    row.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value || "Empty";
      if (!value) cell.className = "is-empty";
      tableRow.append(cell);
    });
    tbody.append(tableRow);
  });
  table.replaceChildren(thead, tbody);
}

function updateQueryValueVisibility() {
  const isEmptyQuery = elements.queryOperator.value === "empty";
  elements.queryValueField.hidden = isEmptyQuery;
  elements.queryValue.required = !isEmptyQuery;
}

async function runDatasetQuery(event) {
  event.preventDefault();
  if (!selectedDataset) return;
  updateQueryValueVisibility();
  if (!elements.queryForm.reportValidity()) return;
  const submitButton = elements.queryForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  submitButton.textContent = "Running query";
  elements.queryMessage.textContent = "";
  elements.queryMessage.classList.remove("error");
  try {
    const result = await DatasetApi.queryDataset(selectedDataset.id, currentUser.email, {
      column: elements.queryColumn.value,
      operator: elements.queryOperator.value,
      value: elements.queryValue.value.trim()
    });
    renderDataTable(elements.datasetDetailTable, result.headers, result.rows.slice(0, MAX_PREVIEW_ROWS));
    elements.queryMessage.textContent = `${result.count.toLocaleString("en-US")} matching rows found.`;
  } catch (error) {
    elements.queryMessage.textContent = error.message || "The query could not be completed.";
    elements.queryMessage.classList.add("error");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Run query";
  }
}

function openDeleteDialog(dataset) {
  pendingDeleteDataset = dataset;
  elements.deleteDialogMessage.textContent = `${dataset.name} will be permanently removed from your workspace.`;
  elements.deleteDialog.showModal();
}

async function confirmDeleteDataset(event) {
  event.preventDefault();
  if (!pendingDeleteDataset || !currentUser) return;
  const submitButton = elements.deleteForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  submitButton.textContent = "Deleting";
  try {
    await DatasetApi.deleteDataset(pendingDeleteDataset.id, currentUser.email);
    elements.deleteDialog.close();
    showToast(`${pendingDeleteDataset.name} was deleted.`);
    pendingDeleteDataset = null;
    await loadDatasetLibrary({ silent: true });
  } catch (error) {
    elements.deleteDialogMessage.textContent = error.message || "The dataset could not be deleted.";
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Delete dataset";
  }
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.hidden = false;
  window.clearTimeout(showToast.timeoutId);
  showToast.timeoutId = window.setTimeout(() => { elements.toast.hidden = true; }, 3200);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("en-AU", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
}

function initializeTheme() {
  const savedTheme = localStorage.getItem("csv-insight-theme");
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const theme = savedTheme || (systemDark ? "dark" : "light");
  applyTheme(theme);
}

function toggleTheme() {
  const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("csv-insight-theme", nextTheme);
  applyTheme(nextTheme);
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  elements.themeToggle.setAttribute("aria-label", `Switch to ${theme === "dark" ? "light" : "dark"} mode`);
  elements.themeToggle.setAttribute("aria-pressed", String(theme === "dark"));
  document.querySelector('meta[name="theme-color"]').content = theme === "dark" ? "#0d1117" : "#f4f6f8";
}

async function initializeAuth() {
  const savedUser = localStorage.getItem("csv-insight-user") || sessionStorage.getItem("csv-insight-user");
  const savedToken = localStorage.getItem("csv-insight-token") || sessionStorage.getItem("csv-insight-token");
  if (!savedUser || !savedToken) {
    clearAuthSession();
    renderAuthUser(null);
    return;
  }

  try {
    const cachedUser = JSON.parse(savedUser);
    renderAuthUser(cachedUser);
    const apiUser = await AuthApi.getProfile();
    const user = { ...apiUser, name: apiUser.fullName || cachedUser.name || formatNameFromEmail(apiUser.email) };
    const storage = localStorage.getItem("csv-insight-token") ? localStorage : sessionStorage;
    storage.setItem("csv-insight-user", JSON.stringify(user));
    renderAuthUser(user);
  } catch {
    clearAuthSession();
    renderAuthUser(null);
  }
}

function openAuthDialog(view = "login") {
  switchAuthView(view);
  if (!elements.authDialog.open) elements.authDialog.showModal();
  window.setTimeout(() => {
    const firstInput = elements.authDialog.querySelector(`[data-auth-panel="${view}"] input`);
    firstInput?.focus();
  }, 30);
}

function closeAuthDialog() {
  if (elements.authDialog.open) elements.authDialog.close();
}

function handleDialogBackdropClick(event) {
  if (event.target === elements.authDialog) closeAuthDialog();
}

function switchAuthView(view) {
  const validView = ["login", "signup", "forgot"].includes(view) ? view : "login";
  document.querySelectorAll("[data-auth-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.authPanel !== validView;
  });
  clearAuthFeedback();
}

function clearAuthFeedback() {
  document.querySelectorAll(".field-error").forEach((element) => {
    element.textContent = "";
  });
  document.querySelectorAll(".auth-form-message").forEach((element) => {
    element.textContent = "";
    element.className = "auth-form-message";
  });
  elements.authDialog.querySelectorAll("[aria-invalid]").forEach((input) => input.removeAttribute("aria-invalid"));
}

function setFieldError(input, message) {
  const errorElement = document.querySelector(`#${input.getAttribute("aria-describedby")}`);
  input.setAttribute("aria-invalid", String(Boolean(message)));
  if (errorElement) errorElement.textContent = message;
  return !message;
}

function validateEmail(input) {
  const email = input.value.trim();
  if (!email) return setFieldError(input, "Enter your email address.");
  if (!input.validity.valid) return setFieldError(input, "Enter a valid email address.");
  return setFieldError(input, "");
}

function validatePassword(input) {
  if (!input.value) return setFieldError(input, "Enter your password.");
  if (input.value.length < 8) return setFieldError(input, "Use at least 8 characters.");
  return setFieldError(input, "");
}

function setFormMessage(elementId, message, type = "") {
  const element = document.querySelector(`#${elementId}`);
  element.textContent = message;
  element.className = `auth-form-message${type ? ` ${type}` : ""}`;
}

function setSubmitState(form, loading, label) {
  const button = form.querySelector('button[type="submit"]');
  if (!button.dataset.defaultLabel) button.dataset.defaultLabel = button.textContent;
  button.disabled = loading;
  button.textContent = loading ? label : button.dataset.defaultLabel;
}

async function handleLogin(event) {
  event.preventDefault();
  clearAuthFeedback();
  const emailInput = elements.loginForm.elements.email;
  const passwordInput = elements.loginForm.elements.password;
  const emailValid = validateEmail(emailInput);
  const passwordValid = validatePassword(passwordInput);
  const isValid = emailValid && passwordValid;
  if (!isValid) {
    setFormMessage("loginMessage", "Check the highlighted fields and try again.", "error");
    elements.loginForm.querySelector('[aria-invalid="true"]')?.focus();
    return;
  }

  setSubmitState(elements.loginForm, true, "Signing in");
  try {
    const result = await AuthApi.login({
      email: emailInput.value.trim(),
      password: passwordInput.value
    });
    saveAuthSession(result.user, result.accessToken, elements.loginForm.elements.remember.checked);
    elements.loginForm.reset();
    setFormMessage("loginMessage", "Signed in successfully.", "success");
    window.setTimeout(closeAuthDialog, 650);
  } catch (error) {
    setFormMessage("loginMessage", error.message, "error");
  } finally {
    setSubmitState(elements.loginForm, false, "");
  }
}

async function handleSignup(event) {
  event.preventDefault();
  clearAuthFeedback();
  const { name, email, password, confirmPassword, terms } = elements.signupForm.elements;
  const nameValid = name.value.trim().length >= 2
    ? setFieldError(name, "")
    : setFieldError(name, "Enter at least 2 characters.");
  const emailValid = validateEmail(email);
  const passwordValid = validatePassword(password);
  const confirmValid = confirmPassword.value === password.value && confirmPassword.value
    ? setFieldError(confirmPassword, "")
    : setFieldError(confirmPassword, "Passwords must match.");

  if (!nameValid || !emailValid || !passwordValid || !confirmValid || !terms.checked) {
    setFormMessage("signupMessage", terms.checked ? "Check the highlighted fields and try again." : "Accept the terms to continue.", "error");
    elements.signupForm.querySelector('[aria-invalid="true"]')?.focus();
    return;
  }

  setSubmitState(elements.signupForm, true, "Creating account");
  try {
    const result = await AuthApi.register({
      fullName: name.value.trim(),
      email: email.value.trim(),
      password: password.value
    });
    saveAuthSession(result.user, result.accessToken, true);
    elements.signupForm.reset();
    setFormMessage("signupMessage", "Account created successfully.", "success");
    window.setTimeout(closeAuthDialog, 750);
  } catch (error) {
    setFormMessage("signupMessage", error.message, "error");
  } finally {
    setSubmitState(elements.signupForm, false, "");
  }
}

async function handleForgotPassword(event) {
  event.preventDefault();
  clearAuthFeedback();
  const emailInput = elements.forgotForm.elements.email;
  if (!validateEmail(emailInput)) {
    setFormMessage("forgotMessage", "Enter a valid email address to continue.", "error");
    emailInput.focus();
    return;
  }

  setSubmitState(elements.forgotForm, true, "Preparing request");
  try {
    const result = await AuthApi.forgotPassword(emailInput.value.trim());
    setFormMessage("forgotMessage", result.message, "success");
  } catch (error) {
    setFormMessage("forgotMessage", error.message, "error");
  } finally {
    setSubmitState(elements.forgotForm, false, "");
  }
}

function saveAuthSession(apiUser, accessToken, persist) {
  clearAuthSession();
  const storage = persist ? localStorage : sessionStorage;
  const user = { ...apiUser, name: apiUser.fullName || apiUser.name || formatNameFromEmail(apiUser.email) };
  storage.setItem("csv-insight-user", JSON.stringify(user));
  storage.setItem("csv-insight-token", accessToken);
  renderAuthUser(user);
}

function renderAuthUser(user) {
  currentUser = user;
  elements.guestAuth.hidden = Boolean(user);
  elements.userAuth.hidden = !user;
  elements.primaryNav.hidden = Boolean(user);
  elements.memberNav.hidden = !user;
  if (!user) {
    document.body.classList.remove("is-authenticated", "member-analysis-mode");
    elements.memberApp.hidden = true;
    elements.mainContent.hidden = false;
    elements.guestFooter.hidden = false;
    elements.skipLink.href = "#main-content";
    return;
  }
  renderUserIdentity(user);
  document.body.classList.add("is-authenticated");
  showMemberDashboard();
}

function renderUserIdentity(user) {
  const name = user.fullName || user.name || formatNameFromEmail(user.email);
  user.name = name;
  const initials = getInitials(name);
  const avatarImage = user.avatarUrl ? `url(${JSON.stringify(user.avatarUrl)})` : "";
  elements.userName.textContent = name;
  elements.memberProfileName.textContent = name;
  elements.memberProfileEmail.textContent = user.email;
  elements.memberGreetingName.textContent = name.split(/\s+/)[0];
  elements.profileFullName.value = name;
  elements.profileEmail.value = user.email;
  [elements.userInitials, elements.memberAvatar, elements.profileAvatarPreview].forEach((element) => {
    element.style.backgroundImage = avatarImage;
    element.textContent = user.avatarUrl ? "" : initials;
  });
}

function saveUpdatedUser(user) {
  const normalized = { ...currentUser, ...user, name: user.fullName || user.name || currentUser.name };
  currentUser = normalized;
  const storage = localStorage.getItem("csv-insight-token") ? localStorage : sessionStorage;
  storage.setItem("csv-insight-user", JSON.stringify(normalized));
  renderUserIdentity(normalized);
}

function setProfileMessage(element, message, type = "") {
  element.textContent = message;
  element.className = `profile-message${type ? ` ${type}` : ""}`;
}

function showMemberDashboard() {
  document.body.classList.remove("member-analysis-mode");
  elements.memberApp.hidden = false;
  elements.memberDashboardView.hidden = false;
  elements.memberProfileView.hidden = true;
  elements.mainContent.hidden = true;
  elements.guestFooter.hidden = true;
  elements.skipLink.href = "#memberApp";
  elements.memberDashboardButton.classList.add("is-active");
  elements.memberAnalyzeNavButton.classList.remove("is-active");
  elements.memberProfileNavButton.classList.remove("is-active");
  document.querySelectorAll("[data-member-view]").forEach((button) => button.classList.toggle("is-active", button.dataset.memberView === "dashboard"));
  window.scrollTo({ top: 0, behavior: "smooth" });
  loadDatasetLibrary();
}

function showMemberAnalyzer() {
  document.body.classList.add("member-analysis-mode");
  elements.memberApp.hidden = true;
  elements.mainContent.hidden = false;
  elements.guestFooter.hidden = true;
  elements.skipLink.href = "#workspace-title";
  elements.memberDashboardButton.classList.remove("is-active");
  elements.memberAnalyzeNavButton.classList.add("is-active");
  elements.memberProfileNavButton.classList.remove("is-active");
  document.querySelectorAll("[data-member-view]").forEach((button) => button.classList.toggle("is-active", button.dataset.memberView === "analyzer"));
  window.setTimeout(() => document.querySelector("#workspace-title")?.scrollIntoView({ behavior: "smooth", block: "start" }), 20);
}

function showMemberProfile() {
  document.body.classList.remove("member-analysis-mode");
  elements.memberApp.hidden = false;
  elements.memberDashboardView.hidden = true;
  elements.memberProfileView.hidden = false;
  elements.mainContent.hidden = true;
  elements.guestFooter.hidden = true;
  elements.skipLink.href = "#profile-title";
  elements.memberDashboardButton.classList.remove("is-active");
  elements.memberAnalyzeNavButton.classList.remove("is-active");
  elements.memberProfileNavButton.classList.add("is-active");
  document.querySelectorAll("[data-member-view]").forEach((button) => button.classList.toggle("is-active", button.dataset.memberView === "profile"));
  setProfileMessage(elements.profileNameMessage, "");
  setProfileMessage(elements.passwordMessage, "");
  setProfileMessage(elements.avatarMessage, "");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function handleProfileNameUpdate(event) {
  event.preventDefault();
  const fullName = elements.profileFullName.value.trim();
  if (fullName.length < 2 || fullName.length > 100) {
    setFieldError(elements.profileFullName, "Enter between 2 and 100 characters.");
    setProfileMessage(elements.profileNameMessage, "Check your full name and try again.", "error");
    return;
  }
  setFieldError(elements.profileFullName, "");
  setSubmitState(elements.profileNameForm, true, "Saving profile");
  try {
    const user = await AuthApi.updateProfile(fullName);
    saveUpdatedUser(user);
    setProfileMessage(elements.profileNameMessage, "Profile updated successfully.", "success");
  } catch (error) {
    setProfileMessage(elements.profileNameMessage, error.message, "error");
  } finally {
    setSubmitState(elements.profileNameForm, false, "");
  }
}

async function handlePasswordChange(event) {
  event.preventDefault();
  const { currentPassword, newPassword, confirmPassword } = elements.passwordForm.elements;
  const currentValid = currentPassword.value
    ? setFieldError(currentPassword, "")
    : setFieldError(currentPassword, "Enter your current password.");
  const newValid = newPassword.value.length >= 8
    ? setFieldError(newPassword, "")
    : setFieldError(newPassword, "Use at least 8 characters.");
  const confirmValid = confirmPassword.value === newPassword.value && confirmPassword.value
    ? setFieldError(confirmPassword, "")
    : setFieldError(confirmPassword, "Passwords must match.");
  if (!currentValid || !newValid || !confirmValid) {
    setProfileMessage(elements.passwordMessage, "Check the highlighted fields and try again.", "error");
    return;
  }
  setSubmitState(elements.passwordForm, true, "Updating password");
  try {
    const result = await AuthApi.changePassword(currentPassword.value, newPassword.value);
    elements.passwordForm.reset();
    setProfileMessage(elements.passwordMessage, result.message, "success");
  } catch (error) {
    setProfileMessage(elements.passwordMessage, error.message, "error");
  } finally {
    setSubmitState(elements.passwordForm, false, "");
  }
}

async function handleAvatarUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  const allowedTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
  if (!allowedTypes.has(file.type)) {
    setProfileMessage(elements.avatarMessage, "Choose a JPEG, PNG or WebP image.", "error");
    event.target.value = "";
    return;
  }
  if (file.size > 5 * 1024 * 1024) {
    setProfileMessage(elements.avatarMessage, "Choose an image smaller than 5 MB.", "error");
    event.target.value = "";
    return;
  }
  elements.avatarChooseButton.disabled = true;
  elements.avatarChooseButton.textContent = "Uploading image";
  setProfileMessage(elements.avatarMessage, "Uploading your profile picture.");
  try {
    const user = await AuthApi.uploadAvatar(file);
    saveUpdatedUser(user);
    setProfileMessage(elements.avatarMessage, "Profile picture updated successfully.", "success");
  } catch (error) {
    setProfileMessage(elements.avatarMessage, error.message, "error");
  } finally {
    elements.avatarChooseButton.disabled = false;
    elements.avatarChooseButton.textContent = "Choose image";
    event.target.value = "";
  }
}

function signOut() {
  clearAuthSession();
  closeAuthDialog();
  if (elements.datasetDialog.open) elements.datasetDialog.close();
  if (elements.deleteDialog.open) elements.deleteDialog.close();
  currentDataset = { headers: [], rows: [] };
  datasetSummaries = [];
  selectedDataset = null;
  pendingDeleteDataset = null;
  elements.fileInput.value = "";
  elements.searchInput.value = "";
  elements.datasetSearchInput.value = "";
  elements.results.hidden = true;
  elements.emptyState.hidden = false;
  elements.memberDashboardView.hidden = false;
  elements.memberProfileView.hidden = true;
  elements.profileNameForm.reset();
  elements.passwordForm.reset();
  clearMessage();
  renderAuthUser(null);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function clearAuthSession() {
  localStorage.removeItem("csv-insight-user");
  sessionStorage.removeItem("csv-insight-user");
  localStorage.removeItem("csv-insight-token");
  sessionStorage.removeItem("csv-insight-token");
}

function formatNameFromEmail(email) {
  const base = email.split("@")[0].replace(/[._-]+/g, " ").trim();
  if (!base) return "CSV user";
  return base.replace(/\b\w/g, (character) => character.toUpperCase());
}

function getInitials(name) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0].toUpperCase()).join("") || "CI";
}
