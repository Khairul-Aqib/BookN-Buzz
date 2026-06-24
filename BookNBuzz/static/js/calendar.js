/* BookN'Buzz - custom booking calendar (vanilla JS, progressive enhancement).
 *
 * Enhances the native <input type="date"> into a month grid where:
 *   - past dates              -> disabled, dimmed + strikethrough
 *   - barber-blocked dates    -> disabled, hatched "unavailable" look
 *   - non-working weekdays    -> disabled (barber has no hours that day)
 *   - today                   -> distinct amber outline marker
 *   - selectable dates        -> bright, hover highlight, pointer cursor
 *   - the chosen date         -> solid amber "selected" style
 *
 * The disabled rules here mirror the server-side checks in views/customer.py,
 * so a past/blocked date can never be booked even if the UI is bypassed.
 */
(function () {
  "use strict";

  var root = document.getElementById("bnb-calendar");
  if (!root) return;

  var nativeInput = document.getElementById("date");
  var grid = root.querySelector(".cal-grid");
  var titleEl = root.querySelector(".cal-title");
  var prevBtn = root.querySelector(".cal-prev");
  var nextBtn = root.querySelector(".cal-next");
  var errorEl = root.querySelector(".cal-error");

  var MONTHS = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"];

  var today = root.dataset.today;                                  // 'YYYY-MM-DD'
  var blocked = new Set(JSON.parse(root.dataset.blocked || "[]")); // ['YYYY-MM-DD']
  var workdays = new Set(JSON.parse(root.dataset.weekdays || "[]"));// [0..6] Mon..Sun
  var selected = root.dataset.selected || "";

  function parseISO(s) { var p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function iso(dt) {
    return dt.getFullYear() + "-" +
           String(dt.getMonth() + 1).padStart(2, "0") + "-" +
           String(dt.getDate()).padStart(2, "0");
  }
  function midnight(dt) { return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate()); }
  // JS getDay(): 0=Sun..6=Sat. Convert to Python weekday: 0=Mon..6=Sun.
  function pyWeekday(dt) { return (dt.getDay() + 6) % 7; }

  var todayMid = midnight(parseISO(today));
  var view = midnight(selected ? parseISO(selected) : todayMid);
  view = new Date(view.getFullYear(), view.getMonth(), 1);

  function render() {
    grid.innerHTML = "";
    titleEl.textContent = MONTHS[view.getMonth()] + " " + view.getFullYear();

    var firstOfMonth = new Date(view.getFullYear(), view.getMonth(), 1);
    var leadBlanks = pyWeekday(firstOfMonth); // blanks before day 1 (Mon-first grid)
    var daysInMonth = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();

    for (var i = 0; i < leadBlanks; i++) {
      var blank = document.createElement("div");
      blank.className = "cal-cell cal-blank";
      grid.appendChild(blank);
    }

    for (var day = 1; day <= daysInMonth; day++) {
      var dt = new Date(view.getFullYear(), view.getMonth(), day);
      var ds = iso(dt);
      var cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cal-cell cal-day";
      cell.textContent = day;
      cell.setAttribute("data-date", ds);

      var isPast = midnight(dt) < todayMid;
      var isToday = ds === today;
      var isBlocked = blocked.has(ds);
      var isOff = workdays.size > 0 && !workdays.has(pyWeekday(dt));

      if (isToday) cell.classList.add("is-today");

      var disabled = false, reason = "";
      if (isPast) { cell.classList.add("is-past"); disabled = true; reason = "Past date"; }
      else if (isBlocked) { cell.classList.add("is-blocked"); disabled = true; reason = "Barber unavailable"; }
      else if (isOff) { cell.classList.add("is-off"); disabled = true; reason = "Shop closed"; }

      if (disabled) {
        cell.classList.add("is-disabled");
        cell.setAttribute("aria-disabled", "true");
        cell.tabIndex = -1;
        cell.title = reason;
        // no click handler -> not selectable
      } else {
        cell.classList.add("is-selectable");
        if (ds === selected) cell.classList.add("is-selected");
        cell.addEventListener("click", makeHandler(ds));
      }
      grid.appendChild(cell);
    }

    // Prevent navigating to months entirely before the current one.
    var curMonthStart = new Date(todayMid.getFullYear(), todayMid.getMonth(), 1);
    prevBtn.disabled = view <= curMonthStart;
  }

  function makeHandler(ds) {
    return function () { selectDate(ds); };
  }

  function selectDate(ds) {
    selected = ds;
    if (nativeInput) nativeInput.value = ds; // feeds the form submit
    var cells = grid.querySelectorAll(".cal-day");
    for (var i = 0; i < cells.length; i++) cells[i].classList.remove("is-selected");
    var chosen = grid.querySelector('.cal-day[data-date="' + ds + '"]');
    if (chosen) chosen.classList.add("is-selected");
    if (errorEl) errorEl.hidden = true;
    onDateSelected(ds); // load that date's slots into the right column
  }

  prevBtn.addEventListener("click", function () {
    view = new Date(view.getFullYear(), view.getMonth() - 1, 1);
    render();
  });
  nextBtn.addEventListener("click", function () {
    view = new Date(view.getFullYear(), view.getMonth() + 1, 1);
    render();
  });

  // Activate progressive enhancement: hide the native input, show the calendar.
  if (nativeInput) {
    nativeInput.required = false;          // hidden field must not block submit
    nativeInput.style.display = "none";
  }
  root.hidden = false;
  render();

  // Guard the form: a date must be chosen before searching for slots.
  var form = root.closest("form");
  if (form) {
    form.addEventListener("submit", function (e) {
      if (!nativeInput || !nativeInput.value) {
        e.preventDefault();
        if (errorEl) errorEl.hidden = false;
      }
    });
  }

  // ---- Right-column enhancement -------------------------------------------
  // Load a date's slots on click (no reload), toggle the mobile address
  // field, and keep the booking summary updating live as selections change.
  var panel = document.querySelector(".booking-panel");
  var slotsUrl = panel ? panel.dataset.slotsUrl : "";
  var slotsArea = document.getElementById("slotsArea");
  var slotsHeading = document.getElementById("slotsHeading");
  var confirmMode = document.getElementById("confirmMode");
  var confirmDate = document.getElementById("confirmDate");
  var confirmForm = document.getElementById("confirmForm");
  var confirmBtn = confirmForm ? confirmForm.querySelector('button[type="submit"]') : null;
  var sumMode = document.getElementById("sumMode");
  var sumDate = document.getElementById("sumDate");
  var sumTime = document.getElementById("sumTime");
  var addressBlock = document.getElementById("addressBlock");
  var addressField = document.getElementById("service_address");
  var findBtn = document.getElementById("findBtn");
  var modeRadios = document.querySelectorAll('input[name="mode"]');
  var DASH = "—";

  // JS active: slots load on date click, so the explicit button is redundant.
  if (findBtn) findBtn.hidden = true;

  function setTime(val) { if (sumTime) sumTime.textContent = val || DASH; }

  function renderSlots(data) {
    if (!slotsArea) return;
    var slots = (data && data.slots) || [];
    var label = (data && data.label) || "";
    if (slotsHeading) slotsHeading.textContent = label ? "Times for " + label : "Available times";
    if (sumDate) sumDate.textContent = label || DASH;
    if (confirmDate) confirmDate.value = (data && data.date) || "";
    setTime("");

    if (!slots.length) {
      slotsArea.innerHTML =
        '<p class="slots-hint muted">No open slots for this date. ' +
        'The barber may be fully booked or off. Try another date.</p>';
      if (confirmBtn) confirmBtn.disabled = true;
      return;
    }

    var html = '<div class="slot-grid">';
    for (var i = 0; i < slots.length; i++) {
      var s = slots[i], id = "slot-" + s;
      html += '<div class="slot">' +
        '<input type="radio" id="' + id + '" name="time_slot" value="' + s + '" required>' +
        '<label for="' + id + '">' + s + '</label></div>';
    }
    html += '</div>';
    slotsArea.innerHTML = html;
    if (confirmBtn) confirmBtn.disabled = false;
  }

  function onDateSelected(ds) {
    if (!slotsUrl || !slotsArea) return;
    slotsArea.innerHTML = '<p class="slots-hint muted">Loading times' + DASH + '</p>';
    if (confirmBtn) confirmBtn.disabled = true;
    fetch(slotsUrl + "?date=" + encodeURIComponent(ds), {
      headers: { "X-Requested-With": "fetch" }
    })
      .then(function (r) { return r.json(); })
      .then(renderSlots)
      .catch(function () {
        slotsArea.innerHTML =
          '<p class="slots-hint muted">Couldn\'t load times. Please try again.</p>';
      });
  }

  // Mode change: reveal/hide the mobile address field, keep summary in sync.
  function applyMode(val) {
    var isMobile = val === "mobile";
    if (confirmMode) confirmMode.value = val;
    if (sumMode) sumMode.textContent = isMobile ? "Mobile" : "Walk-in";
    if (addressBlock) addressBlock.hidden = !isMobile;
    if (addressField) addressField.required = isMobile;
  }
  for (var mi = 0; mi < modeRadios.length; mi++) {
    modeRadios[mi].addEventListener("change", function () { applyMode(this.value); });
  }

  // Live "Time" in the summary as slots are clicked (works for server-rendered
  // slots too, via event delegation).
  if (slotsArea) {
    slotsArea.addEventListener("change", function (e) {
      if (e.target && e.target.name === "time_slot") setTime(e.target.value);
    });
    // Reflect a pre-checked slot if the page reloaded with one selected.
    var pre = slotsArea.querySelector('input[name="time_slot"]:checked');
    if (pre) setTime(pre.value);
  }

  // Disable confirm until slots exist (e.g. page loaded with no date yet).
  if (confirmBtn && slotsArea && !slotsArea.querySelector('input[name="time_slot"]')) {
    confirmBtn.disabled = true;
  }
})();
