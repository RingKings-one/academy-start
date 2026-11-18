(function () {
  const modal = document.getElementById("trial-modal");
  const form = document.getElementById("trial-form");
  const formWrap = document.getElementById("trial-form-wrap");
  const success = document.getElementById("trial-success");
  const errorBox = document.getElementById("form-error");
  const submitBtn = document.getElementById("submit-btn");
  const openBot = document.getElementById("open-bot");
  const successText = document.getElementById("success-text");

  function openModal() {
    formWrap.hidden = false;
    success.hidden = true;
    errorBox.style.display = "none";
    form.reset();
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  document.querySelectorAll("[data-open-trial]").forEach((el) => {
    el.addEventListener("click", openModal);
  });
  document.querySelectorAll("[data-close-trial]").forEach((el) => {
    el.addEventListener("click", closeModal);
  });
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.classList.contains("open")) closeModal();
  });

  // Подтянуть направления с API (если seed уже есть)
  fetch("/api/directions")
    .then((r) => (r.ok ? r.json() : []))
    .then((list) => {
      if (!Array.isArray(list) || !list.length) return;
      const select = document.getElementById("direction_slug");
      select.innerHTML = list
        .map(
          (d) =>
            `<option value="${d.slug}">${d.name}${
              d.age_min && d.age_max ? ` (${d.age_min}–${d.age_max} лет)` : ""
            }</option>`
        )
        .join("");
    })
    .catch(() => {});

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorBox.style.display = "none";
    submitBtn.disabled = true;
    submitBtn.textContent = "Отправляем…";

    const data = {
      parent_name: form.parent_name.value.trim(),
      phone: form.phone.value.trim(),
      child_name: form.child_name.value.trim(),
      child_age: Number(form.child_age.value),
      direction_slug: form.direction_slug.value,
      medcert: form.medcert.value,
      pd_consent: form.pd_consent.checked,
    };

    try {
      const res = await fetch("/api/trial", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = payload.detail;
        let msg = "Не удалось отправить заявку";
        if (typeof detail === "string") msg = detail;
        else if (Array.isArray(detail)) msg = detail.map((x) => x.msg || x).join("; ");
        throw new Error(msg);
      }

      formWrap.hidden = true;
      success.hidden = false;
      successText.textContent = payload.message || "Заявка принята";
      if (payload.deep_link) {
        openBot.href = payload.deep_link;
        openBot.style.display = "";
      } else {
        openBot.style.display = "none";
      }
    } catch (err) {
      errorBox.textContent = err.message || "Ошибка сети";
      errorBox.style.display = "block";
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Отправить";
    }
  });
})();
