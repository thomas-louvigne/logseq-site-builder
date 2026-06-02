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

  const main = document.querySelector("main.content");
  const data = window.__SEARCH_DATA__;
  const fuse = data
    ? new Fuse(data, {
        keys: ["title", "content"],
        threshold: 0.35,
        minMatchCharLength: 2,
        includeMatches: true,
      })
    : null;

  function excerpt(text, q, maxLen) {
    if (!text) return "";
    const idx = text.toLowerCase().indexOf(q.toLowerCase());
    const start = idx === -1 ? 0 : Math.max(0, idx - 40);
    const raw = text.slice(start, start + maxLen);
    const display = (start > 0 ? "…" : "") + raw + (start + maxLen < text.length ? "…" : "");
    if (idx === -1) return display;
    const re = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
    return display.replace(re, "<mark>$1</mark>");
  }

  function showDropdown(results, hits, q) {
    results.innerHTML = "";
    if (!hits.length) {
      const li = document.createElement("li");
      li.className = "site-nav__search-empty";
      li.textContent = "Aucun résultat.";
      results.appendChild(li);
    } else {
      hits.forEach(function (h) {
        const li = document.createElement("li");
        li.className = "site-nav__search-suggestion";
        const a = document.createElement("a");
        a.href = h.item.url;
        a.className = "site-nav__search-result-link";
        const titleRe = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
        const titleEl = document.createElement("span");
        titleEl.className = "site-nav__search-suggestion-title";
        titleEl.innerHTML = h.item.title.replace(titleRe, "<mark>$1</mark>");
        a.appendChild(titleEl);
        const snip = excerpt(h.item.content, q, 100);
        if (snip) {
          const snippetEl = document.createElement("span");
          snippetEl.className = "site-nav__search-suggestion-snippet";
          snippetEl.innerHTML = snip;
          a.appendChild(snippetEl);
        }
        li.appendChild(a);
        results.appendChild(li);
      });
    }
    results.hidden = false;
  }

  function showInMain(hits, q) {
    if (!main) return;
    document.querySelectorAll(".site-nav__search-results").forEach(function (r) { r.hidden = true; });
    const article = document.createElement("article");
    article.className = "page-article";
    const hdr = document.createElement("header");
    hdr.className = "page-header";
    const h1 = document.createElement("h1");
    h1.className = "page-title";
    h1.textContent = "Résultats pour « " + q + " »";
    hdr.appendChild(h1);
    article.appendChild(hdr);
    const body = document.createElement("div");
    body.className = "page-body";
    if (!hits.length) {
      const p = document.createElement("p");
      p.textContent = "Aucun résultat pour cette recherche.";
      body.appendChild(p);
    } else {
      const ul = document.createElement("ul");
      ul.style.cssText = "list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:1.25rem";
      hits.forEach(function (h) {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = h.item.url;
        a.style.cssText = "font-size:1.05rem;font-weight:500;display:block";
        a.textContent = h.item.title;
        li.appendChild(a);
        const snip = excerpt(h.item.content, q, 160);
        if (snip) {
          const p = document.createElement("p");
          p.style.cssText = "margin:0.25rem 0 0;font-size:0.875rem;color:var(--color-text-muted)";
          p.innerHTML = snip;
          li.appendChild(p);
        }
        ul.appendChild(li);
      });
      body.appendChild(ul);
    }
    article.appendChild(body);
    main.innerHTML = "";
    main.appendChild(article);
  }

  function initSearch(inputId, resultsId) {
    const input = document.getElementById(inputId);
    const results = document.getElementById(resultsId);
    if (!input || !results) return;

    input.addEventListener("input", function () {
      const q = input.value.trim();
      if (q.length < 3) { results.hidden = true; return; }
      if (!fuse) return;
      showDropdown(results, fuse.search(q, { limit: 6 }), q);
    });

    input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        const q = input.value.trim();
        if (!q) return;
        showInMain(fuse ? fuse.search(q, { limit: 20 }) : [], q);
      }
    });

    document.addEventListener("click", function (e) {
      if (!input.contains(e.target) && !results.contains(e.target)) {
        results.hidden = true;
      }
    });
  }

  initSearch("site-search", "search-results");
})();
