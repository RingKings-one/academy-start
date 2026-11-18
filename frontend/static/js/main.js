(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const header = $("#header");
  const onScrollHeader = () => {
    if (!header) return;
    header.classList.toggle("is-solid", window.scrollY > 12);
  };
  onScrollHeader();
  window.addEventListener("scroll", onScrollHeader, { passive: true });

  const toggle = $("#nav-toggle");
  const nav = $("#nav");
  toggle?.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  });
  nav?.querySelectorAll("a").forEach((a) =>
    a.addEventListener("click", () => {
      nav.classList.remove("is-open");
      toggle?.setAttribute("aria-expanded", "false");
    })
  );

  const sticky = $("#sticky-cta");
  const trial = $("#trial");
  const syncSticky = () => {
    if (!sticky || !trial) return;
    const rect = trial.getBoundingClientRect();
    const hide = rect.top < window.innerHeight * 0.7 && rect.bottom > 120;
    sticky.classList.toggle("is-on", window.scrollY > 480 && !hide);
  };
  window.addEventListener("scroll", syncSticky, { passive: true });
  syncSticky();

  const openTrial = (slug) => {
    if (slug) {
      $$("#dir-chips .chip").forEach((c) => {
        c.classList.toggle("is-active", c.dataset.slug === slug);
      });
    }
    trial?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  };
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-open-trial]");
    if (!btn) return;
    e.preventDefault();
    openTrial(btn.getAttribute("data-dir-slug"));
  });

  const chat = $("#bot-chat");
  const messages = [
    { t: "Система", m: "Заявка на пробное получена. Подтвердите в боте." },
    { t: "Напоминание", m: "Завтра в 17:00. Ответьте «Буду» или «Не дойду»." },
    { t: "Академия Старт", m: "Ждём в зале. Сменная обувь и вода — с собой." },
  ];
  if (chat) {
    messages.forEach((item, i) => {
      const el = document.createElement("div");
      el.className = "msg";
      el.style.animationDelay = reduce ? "0ms" : `${400 + i * 900}ms`;
      el.innerHTML = `<strong>${item.t}</strong>${item.m}`;
      chat.appendChild(el);
    });
  }

  const maskWord = $("#mask-word");
  if (maskWord && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) {
            maskWord.classList.add("is-in");
            io.disconnect();
          }
        });
      },
      { threshold: 0.35 }
    );
    io.observe(maskWord);
  } else {
    maskWord?.classList.add("is-in");
  }

  const canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (canHover) {
    $$("[data-light-card]").forEach((card) => {
      card.addEventListener("pointermove", (e) => {
        const r = card.getBoundingClientRect();
        card.style.setProperty("--mx", `${e.clientX - r.left}px`);
        card.style.setProperty("--my", `${e.clientY - r.top}px`);
        card.classList.add("is-lit");
      });
      card.addEventListener("pointerleave", () => card.classList.remove("is-lit"));
    });
  }

  const hero = $("#hero");
  const heroBg = hero?.querySelector(".hero__bg-image");
  if (heroBg && !reduce) {
    window.addEventListener(
      "scroll",
      () => {
        const y = Math.min(window.scrollY, 500);
        heroBg.style.transform = `scale(${1.02 + y * 0.00004}) translateY(${y * 0.12}px)`;
      },
      { passive: true }
    );
  }

  const bindChips = (root) => {
    const box = $(root);
    if (!box) return;
    box.addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (!chip) return;
      box.querySelectorAll(".chip").forEach((c) => c.classList.remove("is-active"));
      chip.classList.add("is-active");
    });
  };
  bindChips("#dir-chips");
  bindChips("#med-chips");

  let step = 1;
  const total = 3;
  const progress = $("#trial-progress-bar");
  const stepLabel = $("#trial-step-label");
  const panels = $$("[data-step-panel]");

  const showStep = (n) => {
    step = n;
    panels.forEach((p) => {
      const id = Number(p.getAttribute("data-step-panel"));
      const on = id === step;
      p.hidden = !on;
      p.classList.toggle("is-active", on);
    });
    if (progress) progress.style.width = `${(step / total) * 100}%`;
    if (stepLabel) stepLabel.textContent = `Шаг ${step} из ${total}`;
  };
  showStep(1);

  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-trial-next]")) {
      if (step === 1) {
        const name = $("#f-parent")?.value.trim() || "";
        const phone = $("#f-phone")?.value.trim() || "";
        if (name.length < 2 || phone.replace(/\D/g, "").length < 10) {
          alert("Укажите имя и телефон");
          return;
        }
      }
      if (step === 2) {
        const child = $("#f-child")?.value.trim() || "";
        const age = Number($("#f-age")?.value);
        if (child.length < 2 || !age || age < 3 || age > 18) {
          alert("Укажите имя ребёнка и возраст от 3 до 18");
          return;
        }
      }
      if (step < total) showStep(step + 1);
    }
    if (e.target.closest("[data-trial-back]")) {
      if (step > 1) showStep(step - 1);
    }
  });

  const err = $("#form-error");
  const success = $("#trial-success");

  $("#trial-submit")?.addEventListener("click", async () => {
    err && (err.hidden = true);
    if (!$("#f-pd")?.checked) {
      if (err) {
        err.hidden = false;
        err.textContent = "Нужно согласие на обработку персональных данных";
      }
      return;
    }
    const slug = $("#dir-chips .chip.is-active")?.dataset.slug || "sambo";
    const med = $("#med-chips .chip.is-active")?.dataset.med || "needs";
    const body = {
      parent_name: $("#f-parent")?.value.trim(),
      phone: $("#f-phone")?.value.trim(),
      child_name: $("#f-child")?.value.trim(),
      child_age: Number($("#f-age")?.value),
      direction_slug: slug,
      medcert: med,
      pd_consent: true,
    };
    const btn = $("#trial-submit");
    if (btn) btn.disabled = true;
    try {
      const res = await fetch("/api/trial", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || data.message || "Не удалось отправить заявку");
      }
      $$("[data-step-panel]").forEach((p) => (p.hidden = true));
      if (stepLabel) stepLabel.hidden = true;
      if (progress?.parentElement) progress.parentElement.hidden = true;
      if (success) success.hidden = false;
      const link = $("#bot-deep-link");
      if (link && data.deep_link) link.href = data.deep_link;
      if ($("#success-msg")) $("#success-msg").textContent = data.message || "";
      if ($("#footer-bot") && data.deep_link) $("#footer-bot").href = data.deep_link;
    } catch (e) {
      if (err) {
        err.hidden = false;
        err.textContent = e.message || "Ошибка сети";
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  fetch("/api/directions")
    .then((r) => (r.ok ? r.json() : []))
    .then((dirs) => {
      if (!Array.isArray(dirs) || !dirs.length) return;
      const chips = $("#dir-chips");
      if (!chips) return;
      chips.innerHTML = "";
      dirs.forEach((d, i) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "chip" + (i === 0 ? " is-active" : "");
        b.dataset.slug = d.slug;
        b.textContent = d.name;
        chips.appendChild(b);
      });
    })
    .catch(() => {});
})();
