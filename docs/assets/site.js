(() => {
  const hoverCapable = window.matchMedia("(hover: hover) and (pointer: fine)");
  const menus = [...document.querySelectorAll(".nav-menu")];

  const closeMenus = (except) => {
    menus.forEach((menu) => {
      if (menu !== except) menu.open = false;
    });
  };

  menus.forEach((menu) => {
    let closeTimer;

    menu.addEventListener("pointerenter", () => {
      if (!hoverCapable.matches) return;
      window.clearTimeout(closeTimer);
      closeMenus(menu);
      menu.open = true;
    });

    menu.addEventListener("pointerleave", () => {
      if (!hoverCapable.matches) return;
      window.clearTimeout(closeTimer);
      closeTimer = window.setTimeout(() => {
        menu.open = false;
      }, 140);
    });
  });

  document.addEventListener("pointermove", (event) => {
    if (!hoverCapable.matches) return;
    menus.forEach((menu) => {
      if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".nav-menu")) closeMenus();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenus();
      document.activeElement?.blur();
    }
  });

  document.querySelectorAll(".heading-anchor").forEach((link) => {
    const heading = link.closest("h1, h2, h3, h4, .section-title");
    if (!heading) return;
    const label = heading.textContent.replace(link.textContent, "").trim();
    link.setAttribute("aria-label", `Permalink to ${label}`);
    link.addEventListener("click", (event) => event.stopPropagation());
  });

  const live = document.createElement("div");
  live.className = "visually-hidden";
  live.setAttribute("aria-live", "polite");
  document.body.appendChild(live);

  document.querySelectorAll("pre").forEach((pre) => {
    const code = pre.querySelector("code");
    if (!code) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy-button";
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code to clipboard");
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(code.innerText);
        button.textContent = "Copied";
        live.textContent = "Code copied to clipboard";
        window.setTimeout(() => { button.textContent = "Copy"; }, 1600);
      } catch {
        live.textContent = "Copy failed";
      }
    });
    pre.appendChild(button);
  });
})();
