(function () {
  "use strict";

  const toggle = document.querySelector(".menu-toggle");
  const nav = document.getElementById("site-nav");

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      const expanded = this.getAttribute("aria-expanded") === "true";
      this.setAttribute("aria-expanded", String(!expanded));
      nav.classList.toggle("is-open", !expanded);
    });

    document.addEventListener("click", function (e) {
      if (!nav.contains(e.target) && !toggle.contains(e.target)) {
        toggle.setAttribute("aria-expanded", "false");
        nav.classList.remove("is-open");
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        toggle.setAttribute("aria-expanded", "false");
        nav.classList.remove("is-open");
      }
    });
  }

  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener("click", function (e) {
      const target = document.querySelector(this.getAttribute("href"));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
})();

(function () {
  "use strict";

  const input = document.getElementById("site-search");
  const btn = document.getElementById("site-search-btn");
  const results = document.getElementById("search-results");
  if (!input || !results) return;

  const data = window.__SEARCH_DATA__;
  const fuse = data ? new Fuse(data, {
    keys: ["title", "content"],
    threshold: 0.35,
    minMatchCharLength: 2,
  }) : null;

  function showMessage(msg) {
    results.innerHTML = "";
    const li = document.createElement("li");
    li.style.padding = "0.4rem 0.75rem";
    li.style.fontSize = "0.8125rem";
    li.style.color = "var(--color-text-muted)";
    li.textContent = msg;
    results.appendChild(li);
    results.hidden = false;
  }

  function runSearch() {
    const q = input.value.trim();
    results.innerHTML = "";
    if (!q) { results.hidden = true; return; }
    if (!fuse) { showMessage("Index de recherche indisponible."); return; }
    const hits = fuse.search(q, { limit: 8 });
    if (!hits.length) { showMessage("Aucun résultat."); return; }
    hits.forEach(function (h) {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = h.item.url;
      a.textContent = h.item.title;
      a.className = "site-nav__search-result-link";
      li.appendChild(a);
      results.appendChild(li);
    });
    results.hidden = false;
  }

  if (btn) btn.addEventListener("click", runSearch);

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") runSearch();
  });

  document.addEventListener("click", function (e) {
    if (!input.contains(e.target) && !results.contains(e.target) && e.target !== btn) {
      results.hidden = true;
    }
  });
})();
