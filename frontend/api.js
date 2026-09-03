(function initializeDatasetApi(global) {
  "use strict";

  const STORAGE_KEY = "csv-insight-datasets-v1";
  const API_BASE_URL = global.CSV_INSIGHT_API_URL || "";
  const USE_REMOTE_API = Boolean(API_BASE_URL);

  function getStoredAccessToken() {
    return localStorage.getItem("csv-insight-token") || sessionStorage.getItem("csv-insight-token") || "";
  }

  function wait(milliseconds = 260) {
    return new Promise((resolve) => global.setTimeout(resolve, milliseconds));
  }

  function readStore() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    } catch {
      return [];
    }
  }

  function writeStore(datasets) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(datasets));
    } catch (error) {
      throw new Error("Browser storage is full. Delete an older demo dataset or connect the S3 backend.");
    }
  }

  function calculateStats(headers, rows) {
    const totalCells = headers.length * rows.length;
    const missingValues = rows.flat().filter((value) => value === "").length;
    return {
      rows: rows.length,
      columns: headers.length,
      missingValues,
      completeness: totalCells ? Math.round(((totalCells - missingValues) / totalCells) * 100) : 0
    };
  }

  async function request(path, options = {}) {
    const accessToken = typeof global.CSV_INSIGHT_GET_TOKEN === "function"
      ? await global.CSV_INSIGHT_GET_TOKEN()
      : getStoredAccessToken();
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...options.headers
      }
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.message || payload.error?.message || `Request failed with status ${response.status}.`);
    }
    return response.status === 204 ? null : response.json();
  }

  const DatasetApi = {
    mode: USE_REMOTE_API ? "remote" : "mock",

    async listDatasets(owner) {
      if (USE_REMOTE_API) return request("/datasets");
      await wait();
      return readStore()
        .filter((dataset) => dataset.owner === owner)
        .map(({ headers, rows, ...summary }) => summary)
        .sort((first, second) => new Date(second.createdAt) - new Date(first.createdAt));
    },

    async createDataset({ owner, name, size, headers, rows, file, contentType = "text/csv" }) {
      if (USE_REMOTE_API) {
        if (!file) throw new Error("A source CSV file is required for cloud upload.");
        const created = await request("/datasets", {
          method: "POST",
          body: JSON.stringify({ name, size, contentType })
        });
        const uploaded = await fetch(created.upload.url, {
          method: created.upload.method || "PUT",
          headers: { "Content-Type": contentType },
          body: file
        });
        if (!uploaded.ok) throw new Error("The CSV could not be uploaded to cloud storage.");
        return created.dataset;
      }
      await wait(380);
      const dataset = {
        id: global.crypto?.randomUUID?.() || `dataset-${Date.now()}`,
        owner,
        name,
        size,
        status: "ready",
        createdAt: new Date().toISOString(),
        stats: calculateStats(headers, rows),
        headers,
        rows: rows.slice(0, 500)
      };
      const datasets = readStore();
      datasets.unshift(dataset);
      writeStore(datasets);
      return dataset;
    },

    async getDataset(id, owner) {
      if (USE_REMOTE_API) return request(`/datasets/${encodeURIComponent(id)}`);
      await wait();
      const dataset = readStore().find((item) => item.id === id && item.owner === owner);
      if (!dataset) throw new Error("Dataset was not found.");
      return dataset;
    },

    async queryDataset(id, owner, query) {
      if (USE_REMOTE_API) {
        return request(`/datasets/${encodeURIComponent(id)}/query`, {
          method: "POST",
          body: JSON.stringify(query)
        });
      }
      const dataset = await this.getDataset(id, owner);
      const columnIndex = dataset.headers.indexOf(query.column);
      if (columnIndex < 0) throw new Error("Select a valid column.");
      const expected = String(query.value || "").toLocaleLowerCase("en");
      const rows = dataset.rows.filter((row) => {
        const actual = String(row[columnIndex] || "");
        if (query.operator === "empty") return actual === "";
        if (query.operator === "equals") return actual.toLocaleLowerCase("en") === expected;
        if (query.operator === "greater") return Number(actual) > Number(query.value);
        if (query.operator === "less") return Number(actual) < Number(query.value);
        return actual.toLocaleLowerCase("en").includes(expected);
      });
      return { headers: dataset.headers, rows, count: rows.length };
    },

    async deleteDataset(id, owner) {
      if (USE_REMOTE_API) return request(`/datasets/${encodeURIComponent(id)}`, { method: "DELETE" });
      await wait(320);
      const datasets = readStore();
      const nextDatasets = datasets.filter((item) => !(item.id === id && item.owner === owner));
      if (nextDatasets.length === datasets.length) throw new Error("Dataset was not found.");
      writeStore(nextDatasets);
      return null;
    }
  };

  const AuthApi = {
    async register({ fullName, email, password }) {
      if (!USE_REMOTE_API) throw new Error("Set CSV_INSIGHT_API_URL before using account authentication.");
      return request("/auth/register", {
        method: "POST",
        body: JSON.stringify({ fullName, email, password })
      });
    },

    async login({ email, password }) {
      if (!USE_REMOTE_API) throw new Error("Set CSV_INSIGHT_API_URL before using account authentication.");
      return request("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
    },

    async forgotPassword(email) {
      if (!USE_REMOTE_API) throw new Error("Set CSV_INSIGHT_API_URL before using account authentication.");
      return request("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email })
      });
    },

    async getProfile() {
      if (!USE_REMOTE_API) throw new Error("Set CSV_INSIGHT_API_URL before using account authentication.");
      return request("/users/me");
    },

    async updateProfile(fullName) {
      return request("/users/me", {
        method: "PATCH",
        body: JSON.stringify({ fullName })
      });
    },

    async changePassword(currentPassword, newPassword) {
      return request("/users/me/password", {
        method: "POST",
        body: JSON.stringify({ currentPassword, newPassword })
      });
    },

    async uploadAvatar(file) {
      const prepared = await request("/users/me/avatar/upload-url", {
        method: "POST",
        body: JSON.stringify({ contentType: file.type })
      });
      const uploaded = await fetch(prepared.upload.url, {
        method: prepared.upload.method || "PUT",
        headers: { "Content-Type": file.type },
        body: file
      });
      if (!uploaded.ok) throw new Error("The profile picture could not be uploaded.");
      return request("/users/me/avatar", {
        method: "PATCH",
        body: JSON.stringify({ avatarKey: prepared.avatarKey })
      });
    }
  };

  global.DatasetApi = DatasetApi;
  global.AuthApi = AuthApi;
})(window);
