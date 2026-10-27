"""Embedded single-page web dashboard for nanolink.

Provides an interactive dark-mode UI with zero external assets/CDNs.
"""

from __future__ import annotations

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>nanolink ⚡ URL Shortener & Analytics</title>
  <style>
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --border: #30363d;
      --text: #c9d1d9;
      --text-muted: #8b949e;
      --accent: #58a6ff;
      --accent-hover: #1f6feb;
      --success: #238636;
      --success-hover: #2ea043;
      --danger: #da3633;
      --radius: 8px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 2rem 1rem;
    }
    .container { max-width: 960px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1rem;
    }
    .brand { font-size: 1.5rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 0.5rem; }
    .badge {
      background: rgba(56, 139, 253, 0.15);
      color: var(--accent);
      padding: 0.2rem 0.6rem;
      border-radius: 20px;
      font-size: 0.8rem;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }
    h2 { font-size: 1.2rem; margin-bottom: 1rem; color: #fff; }
    .form-group { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1rem; }
    input[type="text"], input[type="url"], input[type="number"] {
      background: #0d1117;
      border: 1px solid var(--border);
      color: var(--text);
      padding: 0.6rem 0.8rem;
      border-radius: 6px;
      font-size: 0.95rem;
      flex: 1;
      min-width: 200px;
    }
    input:focus { outline: none; border-color: var(--accent); }
    button {
      background: var(--success);
      color: #fff;
      border: none;
      padding: 0.6rem 1.2rem;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s;
    }
    button:hover { background: var(--success-hover); }
    .btn-secondary { background: #21262d; border: 1px solid var(--border); }
    .btn-secondary:hover { background: #30363d; }
    .result-box {
      display: none;
      background: rgba(35, 134, 54, 0.1);
      border: 1px solid rgba(46, 160, 67, 0.4);
      padding: 1rem;
      border-radius: 6px;
      margin-top: 1rem;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }
    .table-responsive { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem; }
    th { padding: 0.75rem; border-bottom: 1px solid var(--border); color: var(--text-muted); font-weight: 600; }
    td { padding: 0.75rem; border-bottom: 1px solid var(--border); }
    tr:hover td { background: rgba(255, 255, 255, 0.02); }
    .link-code { color: var(--accent); font-weight: 600; text-decoration: none; }
    .stats-modal {
      display: none;
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      z-index: 100;
      align-items: center;
      justify-content: center;
      padding: 1rem;
    }
    .modal-content {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      width: 100%;
      max-width: 700px;
      max-height: 90vh;
      overflow-y: auto;
      padding: 1.5rem;
    }
    .grid-metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 1rem;
      margin: 1rem 0;
    }
    .metric-card {
      background: #0d1117;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 1rem;
      text-align: center;
    }
    .metric-value { font-size: 1.5rem; font-weight: 700; color: var(--accent); }
    .metric-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }
    .chart-bar { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; font-size: 0.85rem; }
    .bar-fill { background: var(--accent); height: 18px; border-radius: 3px; min-width: 4px; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">⚡ nanolink <span class="badge">Production Microservice</span></div>
      <div style="font-size:0.85rem;color:var(--text-muted);">Self-Hosted URL Engine</div>
    </header>

    <!-- Create Link Card -->
    <section class="card">
      <h2>Shorten New URL</h2>
      <form id="shorten-form">
        <div class="form-group">
          <input type="url" id="target-url" placeholder="https://very-long-destination-url.com/path" required />
          <input type="text" id="custom-alias" placeholder="Custom alias (optional)" style="max-width: 220px;" />
          <input type="number" id="ttl-seconds" placeholder="TTL (seconds)" style="max-width: 140px;" />
          <button type="submit">Shorten</button>
        </div>
      </form>
      <div id="result-box" class="result-box">
        <div>
          <div>Short URL created: <a id="short-link-href" class="link-code" target="_blank"></a></div>
          <div id="short-link-meta" style="font-size:0.8rem;color:var(--text-muted);margin-top:0.25rem;"></div>
        </div>
        <button id="copy-btn" class="btn-secondary" type="button">Copy Link</button>
      </div>
    </section>

    <!-- Active Links Table -->
    <section class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;flex-wrap:wrap;gap:0.75rem;">
        <h2>Existing Links</h2>
        <div style="display:flex;gap:0.5rem;flex:1;max-width:400px;">
          <input type="text" id="search-input" placeholder="🔍 Search code, URL, or tag..." style="padding:0.4rem 0.75rem;font-size:0.85rem;" oninput="onSearchInput()" />
          <button class="btn-secondary" onclick="loadLinks()" style="padding:0.4rem 0.8rem;font-size:0.85rem;">Reset</button>
        </div>
      </div>
      <div class="table-responsive">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Destination</th>
              <th>Tags</th>
              <th>Clicks</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="links-tbody">
            <tr><td colspan="6" style="text-align:center;color:var(--text-muted);">Loading links...</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>

  <!-- Analytics Modal -->
  <div id="stats-modal" class="stats-modal">
    <div class="modal-content">
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:0.75rem;">
        <h2 id="modal-title" style="margin:0;">Analytics</h2>
        <button class="btn-secondary" onclick="closeModal()" style="padding:0.2rem 0.6rem;">&times;</button>
      </div>

      <div class="grid-metrics">
        <div class="metric-card">
          <div class="metric-value" id="m-total-clicks">0</div>
          <div class="metric-label">Total Clicks</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" id="m-unique-visitors">0</div>
          <div class="metric-label">Unique Visitors</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" id="m-top-browser">-</div>
          <div class="metric-label">Top Browser</div>
        </div>
        <div class="metric-card">
          <div class="metric-value" id="m-top-device">-</div>
          <div class="metric-label">Top Device</div>
        </div>
      </div>

      <h3 style="font-size:1rem;margin:1.2rem 0 0.5rem;">Daily Click History</h3>
      <div id="daily-chart" style="margin-bottom:1rem;"></div>

      <h3 style="font-size:1rem;margin:1.2rem 0 0.5rem;">Top Referrers</h3>
      <div id="referrers-list" style="font-size:0.9rem;"></div>
    </div>
  </div>

  <script>
    const form = document.getElementById("shorten-form");
    const resultBox = document.getElementById("result-box");
    const shortHref = document.getElementById("short-link-href");
    const copyBtn = document.getElementById("copy-btn");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const url = document.getElementById("target-url").value;
      const alias = document.getElementById("custom-alias").value.trim() || undefined;
      const ttl = parseInt(document.getElementById("ttl-seconds").value, 10) || undefined;

      try {
        const res = await fetch("/api/shorten", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url, alias, ttl_seconds: ttl })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to shorten URL");

        shortHref.href = data.short_url;
        shortHref.textContent = data.short_url;
        resultBox.style.display = "flex";
        form.reset();
        loadLinks();
      } catch (err) {
        alert(err.message);
      }
    });

    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(shortHref.href);
      copyBtn.textContent = "Copied!";
      setTimeout(() => { copyBtn.textContent = "Copy Link"; }, 2000);
    });

    let searchTimeout = null;
    function onSearchInput() {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        const query = document.getElementById("search-input").value.trim();
        loadLinks(query);
      }, 250);
    }

    async function loadLinks(query = "") {
      const tbody = document.getElementById("links-tbody");
      try {
        const endpoint = query ? `/api/search?q=${encodeURIComponent(query)}` : "/api/links?limit=50";
        const res = await fetch(endpoint);
        const data = await res.json();
        const links = data.links || data.results || [];
        if (links.length === 0) {
          tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">${query ? 'No matching links found.' : 'No links created yet.'}</td></tr>`;
          return;
        }
        tbody.innerHTML = links.map(l => {
          const tagsHtml = (l.tags && l.tags.length > 0)
            ? l.tags.map(t => `<span class="badge" style="font-size:0.7rem;margin-right:0.25rem;">${t}</span>`).join("")
            : '<span style="color:var(--text-muted);">-</span>';
          return `
            <tr>
              <td><a href="/${l.code}" target="_blank" class="link-code">${l.code}</a></td>
              <td style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${l.target_url}</td>
              <td>${tagsHtml}</td>
              <td><strong>${l.click_count}</strong></td>
              <td style="color:var(--text-muted);">${l.created_at.split('T')[0]}</td>
              <td>
                <button class="btn-secondary" onclick="viewStats('${l.code}')" style="padding:0.3rem 0.6rem;font-size:0.8rem;">Stats</button>
                <a href="/api/qr/${l.code}" target="_blank" class="btn-secondary" style="padding:0.3rem 0.6rem;font-size:0.8rem;text-decoration:none;display:inline-block;">QR</a>
              </td>
            </tr>
          `;
        }).join("");
      } catch (err) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--danger);">Error loading links.</td></tr>';
      }
    }

    async function viewStats(code) {
      try {
        const res = await fetch(`/api/stats/${code}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to fetch stats");

        document.getElementById("modal-title").textContent = `Analytics for /${code}`;
        document.getElementById("m-total-clicks").textContent = data.total_clicks;
        document.getElementById("m-unique-visitors").textContent = data.unique_visitors;

        const topBrowser = Object.keys(data.browsers)[0] || "None";
        const topDevice = Object.keys(data.devices)[0] || "None";
        document.getElementById("m-top-browser").textContent = topBrowser;
        document.getElementById("m-top-device").textContent = topDevice;

        // Daily chart
        const chartEl = document.getElementById("daily-chart");
        const dates = Object.entries(data.clicks_by_date);
        if (dates.length === 0) {
          chartEl.innerHTML = '<div style="color:var(--text-muted);">No clicks recorded yet.</div>';
        } else {
          const maxVal = Math.max(...dates.map(d => d[1]));
          chartEl.innerHTML = dates.map(([d, val]) => `
            <div class="chart-bar">
              <span style="width:90px;color:var(--text-muted);">${d}</span>
              <div class="bar-fill" style="width:${Math.max(8, (val / maxVal) * 350)}px;"></div>
              <span>${val}</span>
            </div>
          `).join("");
        }

        // Referrers
        const refEl = document.getElementById("referrers-list");
        if (data.top_referrers.length === 0) {
          refEl.innerHTML = '<div style="color:var(--text-muted);">No referrer data.</div>';
        } else {
          refEl.innerHTML = data.top_referrers.map(([r, c]) => `
            <div style="display:flex;justify-content:space-between;padding:0.4rem 0;border-bottom:1px solid var(--border);">
              <span>${r}</span><strong>${c} clicks</strong>
            </div>
          `).join("");
        }

        document.getElementById("stats-modal").style.display = "flex";
      } catch (err) {
        alert(err.message);
      }
    }

    function closeModal() {
      document.getElementById("stats-modal").style.display = "none";
    }

    // Load links on start
    loadLinks();
  </script>
</body>
</html>
"""
