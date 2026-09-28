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

    let activeIdx = -1;

    function getItems() {
      return results.querySelectorAll(".site-nav__search-suggestion");
    }

    function setActive(idx) {
      const items = getItems();
      items.forEach(function (li, i) {
        li.classList.toggle("site-nav__search-suggestion--active", i === idx);
      });
      activeIdx = idx;
    }

    input.addEventListener("input", function () {
      const q = input.value.trim();
      activeIdx = -1;
      if (q.length < 3) { results.hidden = true; return; }
      if (!fuse) return;
      showDropdown(results, fuse.search(q, { limit: 6 }), q);
    });

    input.addEventListener("keydown", function (e) {
      if (!results.hidden && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
        e.preventDefault();
        const items = getItems();
        if (!items.length) return;
        const next = e.key === "ArrowDown"
          ? Math.min(activeIdx + 1, items.length - 1)
          : Math.max(activeIdx - 1, 0);
        setActive(next);
        const link = items[next].querySelector("a");
        if (link) link.focus();
        return;
      }
      if (e.key === "Escape") {
        results.hidden = true;
        activeIdx = -1;
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        if (activeIdx >= 0) {
          const items = getItems();
          const link = items[activeIdx] && items[activeIdx].querySelector("a");
          if (link) { link.click(); return; }
        }
        const q = input.value.trim();
        if (!q) return;
        results.hidden = true;
        showInMain(fuse ? fuse.search(q, { limit: 20 }) : [], q);
      }
    });

    results.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        const items = getItems();
        const next = e.key === "ArrowDown"
          ? Math.min(activeIdx + 1, items.length - 1)
          : Math.max(activeIdx - 1, 0);
        setActive(next);
        const link = items[next] && items[next].querySelector("a");
        if (link) link.focus(); else input.focus();
      }
      if (e.key === "Escape") {
        results.hidden = true;
        activeIdx = -1;
        input.focus();
      }
    });

    document.addEventListener("click", function (e) {
      if (!input.closest(".site-nav__search-box").contains(e.target)) {
        results.hidden = true;
        activeIdx = -1;
      }
    });
  }

  initSearch("site-search", "search-results");
})();

(function () {
  "use strict";

  const bar = document.querySelector(".share-bar");
  if (!bar) return;

  const canonical = document.querySelector('link[rel="canonical"]');
  const url = canonical ? canonical.href : location.href.split("#")[0];
  const text = bar.dataset.shareText || document.title;
  const status = bar.querySelector(".share-bar__status");
  let statusTimer = null;

  function announce(message) {
    status.textContent = message;
    clearTimeout(statusTimer);
    statusTimer = setTimeout(function () { status.textContent = ""; }, 2500);
  }

  bar.querySelectorAll("[data-share-pattern]").forEach(function (link) {
    link.href = link.dataset.sharePattern
      .replace("{url}", encodeURIComponent(url))
      .replace("{text}", encodeURIComponent(text));
  });

  // Native share sheet (mostly mobile): reaches every app the device has,
  // not just the networks listed in the bar.
  const native = bar.querySelector("[data-share-native]");
  if (native && navigator.share) {
    native.hidden = false;
    native.addEventListener("click", function () {
      navigator.share({ title: text, url: url }).catch(function () {});
    });
  }

  const copy = bar.querySelector("[data-share-copy]");
  if (copy) {
    copy.addEventListener("click", function () {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(
          function () { announce("Lien copié"); },
          function () { window.prompt("Copiez ce lien :", url); }
        );
      } else {
        // Clipboard API needs a secure context (https / localhost).
        window.prompt("Copiez ce lien :", url);
      }
    });
  }

  const print = bar.querySelector("[data-share-print]");
  if (print) {
    print.addEventListener("click", function () { window.print(); });
  }
})();

(function () {
  "use strict";

  // "Page au hasard": pick from the search index (every published page),
  // skipping the current one, drawn again on every page load. The link stays
  // hidden when JS or the index is missing. A real href (not a click
  // handler) keeps middle-click / open-in-new-tab working.
  const link = document.querySelector("[data-random-page]");
  const current = location.pathname.split("/").pop() || "index.html";
  const urls = (window.__SEARCH_DATA__ || [])
    .map(function (entry) { return entry.url; })
    .filter(function (url) { return url !== current; });
  if (!link || !urls.length) return;

  link.href = urls[Math.floor(Math.random() * urls.length)];
  link.closest("li").hidden = false;
})();

(function () {
  "use strict";

  // Folded tree-view branches would otherwise be missing from the printout:
  // open them for the print, then fold them back.
  let reopened = [];
  window.addEventListener("beforeprint", function () {
    reopened = Array.from(document.querySelectorAll(".page-body details:not([open])"));
    reopened.forEach(function (d) { d.open = true; });
  });
  window.addEventListener("afterprint", function () {
    reopened.forEach(function (d) { d.open = false; });
    reopened = [];
  });
})();
