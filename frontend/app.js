const MAX_FILE_SIZE = 10 * 1024 * 1024;
const MAX_PREVIEW_ROWS = 100;

const elements = {
  browseButton: document.querySelector("#browseButton"),
  dataTable: document.querySelector("#dataTable"),
  emptyState: document.querySelector("#emptyState"),
  fileInput: document.querySelector("#fileInput"),
  fileMeta: document.querySelector("#fileMeta"),
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
    showMessage("Vui lòng chọn đúng tệp có phần mở rộng .csv.", "error");
    return;
  }
  if (file.size > MAX_FILE_SIZE) {
    showMessage("Tệp vượt quá giới hạn 10 MB.", "error");
    return;
  }

  const reader = new FileReader();
  reader.addEventListener("load", () => {
    try {
      const dataset = parseCSV(String(reader.result));
      if (!dataset.headers.length || !dataset.rows.length) throw new Error("Tệp không chứa dữ liệu hợp lệ.");
      displayDataset(dataset, file.name, file.size);
      showMessage(`Đã đọc thành công ${file.name}.`, "success");
    } catch (error) {
      showMessage(error.message || "Không thể đọc tệp CSV này.", "error");
    }
  });
  reader.addEventListener("error", () => showMessage("Không thể đọc tệp. Vui lòng thử lại.", "error"));
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
    ["Số dòng", dataset.rows.length.toLocaleString("vi-VN")],
    ["Số cột", dataset.headers.length.toLocaleString("vi-VN")],
    ["Ô trống", emptyCells.toLocaleString("vi-VN")],
    ["Độ đầy đủ", `${completePercent}%`]
  ];

  elements.statsGrid.replaceChildren(...stats.map(([label, value]) => {
    const card = document.createElement("article");
    card.className = "stat-card";
    const labelElement = document.createElement("span");
    const valueElement = document.createElement("strong");
    labelElement.textContent = label;
    valueElement.textContent = value;
    card.append(labelElement, valueElement);
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
      td.textContent = value || "Trống";
      if (!value) td.className = "is-empty";
      tr.append(td);
    });
    tbody.append(tr);
  });

  elements.dataTable.replaceChildren(thead, tbody);
  const shown = Math.min(rows.length, MAX_PREVIEW_ROWS);
  elements.rowSummary.textContent = rows.length
    ? `Hiển thị ${shown} / ${currentDataset.rows.length} dòng`
    : "Không tìm thấy dòng phù hợp";
}

function filterRows(event) {
  const query = event.target.value.trim().toLocaleLowerCase("vi");
  const filtered = query
    ? currentDataset.rows.filter((row) => row.some((value) => value.toLocaleLowerCase("vi").includes(query)))
    : currentDataset.rows;
  renderTable(filtered.slice(0, MAX_PREVIEW_ROWS));
}

function loadSampleData() {
  const sample = [
    ["order_id", "customer", "city", "amount", "status"],
    ["ORD-1001", "Nguyễn Minh", "Hồ Chí Minh", "1250000", "Completed"],
    ["ORD-1002", "Trần Hà", "Đà Nẵng", "890000", "Processing"],
    ["ORD-1003", "Lê An", "Hà Nội", "", "Pending"],
    ["ORD-1004", "Phạm Vy", "Cần Thơ", "2140000", "Completed"],
    ["ORD-1005", "Hoàng Nam", "Hải Phòng", "760000", "Completed"]
  ];
  const [headers, ...rows] = sample;
  displayDataset({ headers, rows }, "sample-orders.csv", 348);
  showMessage("Đã tải dữ liệu mẫu để bạn khám phá giao diện.", "success");
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
