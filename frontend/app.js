const MAX_FILE_SIZE = 10 * 1024 * 1024;
const MAX_PREVIEW_ROWS = 100;

const elements = {
  browseButton: document.querySelector("#browseButton"),
  dataTable: document.querySelector("#dataTable"),
  emptyState: document.querySelector("#emptyState"),
  fileInput: document.querySelector("#fileInput"),
  fileMeta: document.querySelector("#fileMeta"),
  heroSampleButton: document.querySelector("#heroSampleButton"),
  loadSampleButton: document.querySelector("#loadSampleButton"),
  message: document.querySelector("#message"),
  resetButton: document.querySelector("#resetButton"),
  results: document.querySelector("#results"),
  rowSummary: document.querySelector("#rowSummary"),
  searchInput: document.querySelector("#searchInput"),
  statsGrid: document.querySelector("#statsGrid"),
  uploadZone: document.querySelector("#uploadZone")
};

let currentDataset = { headers: [], rows: [] };

elements.browseButton.addEventListener("click", () => elements.fileInput.click());
elements.fileInput.addEventListener("change", (event) => handleFile(event.target.files[0]));
elements.loadSampleButton.addEventListener("click", loadSampleData);
elements.heroSampleButton.addEventListener("click", loadSampleData);
elements.resetButton.addEventListener("click", resetWorkspace);
elements.searchInput.addEventListener("input", filterRows);

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

  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      const dataset = parseCSV(String(reader.result));
      if (!dataset.headers.length || !dataset.rows.length) throw new Error("The file does not contain valid data.");
      displayDataset(dataset, file.name, file.size);
      showMessage(`${file.name} was loaded successfully.`, "success");
    } catch (error) {
      showMessage(error.message || "This CSV file could not be read.", "error");
    }
  });
  reader.addEventListener("error", () => showMessage("The file could not be read. Please try again.", "error"));
  reader.readAsText(file, "UTF-8");
}

function parseCSV(text) {
  const lines = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"' && quoted && next === '"') {
      field += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
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
    const marker = document.createElement("i");
    const valueElement = document.createElement("strong");
    const hintElement = document.createElement("small");
    labelElement.textContent = label;
    marker.setAttribute("aria-hidden", "true");
    valueElement.textContent = value;
    hintElement.textContent = hint;
    top.append(labelElement, marker);
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

function loadSampleData() {
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
