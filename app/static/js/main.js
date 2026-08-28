/* AD Security Camera Solution - interactive helpers */
document.addEventListener("DOMContentLoaded", function () {
  // Mobile nav toggle
  var toggle = document.querySelector(".menu-toggle");
  var nav = document.querySelector(".site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      nav.classList.toggle("open");
    });
    nav.querySelectorAll("a").forEach(function (a) {
      a.addEventListener("click", function () { nav.classList.remove("open"); });
    });
  }

  // Admin mobile sidebar
  var admTgl = document.querySelector(".admin-mobile-toggle");
  var sidebar = document.querySelector(".admin-sidebar");
  if (admTgl && sidebar) {
    admTgl.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });
  }

  // FAQ accordion
  document.querySelectorAll(".faq-item .faq-q").forEach(function (q) {
    q.addEventListener("click", function () {
      var item = q.closest(".faq-item");
      item.classList.toggle("open");
    });
  });

  // Format price attributes
  document.querySelectorAll(".fmt-price").forEach(function (el) {
    var val = parseFloat(el.getAttribute("data-price") || "0") || 0;
    if (!el.textContent.trim()) {
      el.textContent = "$" + val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
  });

  // Quantity steppers
  document.querySelectorAll(".qty-input").forEach(function (box) {
    var minus = box.querySelector(".qty-minus");
    var plus = box.querySelector(".qty-plus");
    var input = box.querySelector("input");
    if (!minus || !plus || !input) return;
    minus.addEventListener("click", function () {
      var v = parseInt(input.value, 10) || 1;
      if (v > 1) input.value = v - 1;
    });
    plus.addEventListener("click", function () {
      var v = parseInt(input.value, 10) || 1;
      input.value = v + 1;
    });
  });

  // Gallery filter (category chips)
  var chips = document.querySelectorAll("[data-filter]");
  var galleryItems = document.querySelectorAll("[data-gallery-cat]");
  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      chips.forEach(function (c) { c.classList.remove("active"); });
      chip.classList.add("active");
      var f = chip.getAttribute("data-filter");
      galleryItems.forEach(function (item) {
        var cat = item.getAttribute("data-gallery-cat") || "";
        item.style.display = (f === "all" || cat === f) ? "" : "none";
      });
    });
  });

  // Confirm destructive actions
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!confirm(form.getAttribute("data-confirm") || "Are you sure?")) {
        e.preventDefault();
      }
    });
  });

  // Auto-dismiss alerts
  setTimeout(function () {
    document.querySelectorAll(".alert").forEach(function (a) {
      a.style.transition = "opacity .5s";
      a.style.opacity = "0";
      setTimeout(function () { a.remove(); }, 600);
    });
  }, 4000);
});