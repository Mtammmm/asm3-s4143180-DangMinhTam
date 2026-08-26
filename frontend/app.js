const MAX_FILE_SIZE = 10 * 1024 * 1024;
const MAX_PREVIEW_ROWS = 100;

const elements = {
  authCloseButton: document.querySelector("#authCloseButton"),
  authDialog: document.querySelector("#authDialog"),
  browseButton: document.querySelector("#browseButton"),
  dataTable: document.querySelector("#dataTable"),
  emptyState: document.querySelector("#emptyState"),
  fileInput: document.querySelector("#fileInput"),
  fileMeta: document.querySelector("#fileMeta"),
  forgotForm: document.querySelector("#forgotForm"),
  guestAuth: document.querySelector("#guestAuth"),
  heroSampleButton: document.querySelector("#heroSampleButton"),
  loginForm: document.querySelector("#loginForm"),
  loadSampleButton: document.querySelector("#loadSampleButton"),
  message: document.querySelector("#message"),
  resetButton: document.querySelector("#resetButton"),
  results: document.querySelector("#results"),
  rowSummary: document.querySelector("#rowSummary"),
  searchInput: document.querySelector("#searchInput"),
  signOutButton: document.querySelector("#signOutButton"),
  signupForm: document.querySelector("#signupForm"),
  statsGrid: document.querySelector("#statsGrid"),
  themeToggle: document.querySelector("#themeToggle"),
  uploadZone: document.querySelector("#uploadZone"),
  userAuth: document.querySelector("#userAuth"),
  userInitials: document.querySelector("#userInitials"),
  userName: document.querySelector("#userName")
};

let currentDataset = { headers: [], rows: [] };

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

function initializeAuth() {
  const savedUser = localStorage.getItem("csv-insight-user") || sessionStorage.getItem("csv-insight-user");
  if (!savedUser) {
    renderAuthUser(null);
    return;
  }

  try {
    renderAuthUser(JSON.parse(savedUser));
  } catch {
    localStorage.removeItem("csv-insight-user");
    sessionStorage.removeItem("csv-insight-user");
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

function handleLogin(event) {
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
  window.setTimeout(() => {
    const email = emailInput.value.trim();
    const user = { name: formatNameFromEmail(email), email };
    saveAuthUser(user, elements.loginForm.elements.remember.checked);
    setSubmitState(elements.loginForm, false, "");
    setFormMessage("loginMessage", "Signed in successfully. This is a local demo session.", "success");
    window.setTimeout(closeAuthDialog, 650);
  }, 650);
}

function handleSignup(event) {
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
    setFormMessage("signupMessage", terms.checked ? "Check the highlighted fields and try again." : "Accept the demo terms to continue.", "error");
    elements.signupForm.querySelector('[aria-invalid="true"]')?.focus();
    return;
  }

  setSubmitState(elements.signupForm, true, "Creating account");
  window.setTimeout(() => {
    const user = { name: name.value.trim(), email: email.value.trim() };
    saveAuthUser(user, true);
    setSubmitState(elements.signupForm, false, "");
    setFormMessage("signupMessage", "Account created for this frontend demo. No password was stored.", "success");
    window.setTimeout(closeAuthDialog, 750);
  }, 700);
}

function handleForgotPassword(event) {
  event.preventDefault();
  clearAuthFeedback();
  const emailInput = elements.forgotForm.elements.email;
  if (!validateEmail(emailInput)) {
    setFormMessage("forgotMessage", "Enter a valid email address to continue.", "error");
    emailInput.focus();
    return;
  }

  setSubmitState(elements.forgotForm, true, "Preparing request");
  window.setTimeout(() => {
    setSubmitState(elements.forgotForm, false, "");
    setFormMessage("forgotMessage", "Reset request preview complete. Connect a backend later to send the email.", "success");
  }, 650);
}

function saveAuthUser(user, persist) {
  localStorage.removeItem("csv-insight-user");
  sessionStorage.removeItem("csv-insight-user");
  const storage = persist ? localStorage : sessionStorage;
  storage.setItem("csv-insight-user", JSON.stringify(user));
  renderAuthUser(user);
}

function renderAuthUser(user) {
  elements.guestAuth.hidden = Boolean(user);
  elements.userAuth.hidden = !user;
  if (!user) return;
  elements.userName.textContent = user.name;
  elements.userInitials.textContent = getInitials(user.name);
}

function signOut() {
  localStorage.removeItem("csv-insight-user");
  sessionStorage.removeItem("csv-insight-user");
  renderAuthUser(null);
}

function formatNameFromEmail(email) {
  const base = email.split("@")[0].replace(/[._-]+/g, " ").trim();
  if (!base) return "CSV user";
  return base.replace(/\b\w/g, (character) => character.toUpperCase());
}

function getInitials(name) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0].toUpperCase()).join("") || "CI";
}
