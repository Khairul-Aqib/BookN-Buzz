/* BookN'Buzz - availability "block days" calendar (vanilla JS).
 *
 * A month grid where clicking a date toggles it blocked/unblocked by submitting
 * a small POST form (server reloads the page with the new state). Past dates are
 * disabled. Blocked dates are highlighted red. The same blocked rule is enforced
 * server-side in views/barber.py.
 */
(function () {
  "use strict";

  var root = document.getElementById("block-calendar");
  if (!root) return;

  var form = document.getElementById("block-form");
  var dateInput = document.getElementById("block-date");
  var grid = root.querySelector(".cal-grid");
  var titleEl = root.querySelector(".cal-title");
  var prevBtn = root.querySelector(".cal-prev");
  var nextBtn = root.querySelector(".cal-next");

  var MONTHS = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"];

  var today = root.dataset.today;
  var blocked = new Set(JSON.parse(root.dataset.blocked || "[]"));

  function parseISO(s) { var p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function iso(dt) {
    return dt.getFullYear() + "-" +
           String(dt.getMonth() + 1).padStart(2, "0") + "-" +
           String(dt.getDate()).padStart(2, "0");
  }
  function midnight(dt) { return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate()); }
  function pyWeekday(dt) { return (dt.getDay() + 6) % 7; }  // Mon=0..Sun=6

  var todayMid = midnight(parseISO(today));
  var view = new Date(todayMid.getFullYear(), todayMid.getMonth(), 1);

  function submitDate(ds) {
    dateInput.value = ds;
    form.submit();
  }

  function render() {
    grid.innerHTML = "";
    titleEl.textContent = MONTHS[view.getMonth()] + " " + view.getFullYear();

    var firstOfMonth = new Date(view.getFullYear(), view.getMonth(), 1);
    var lead = pyWeekday(firstOfMonth);
    var days = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();

    for (var i = 0; i < lead; i++) {
      var blank = document.createElement("div");
      blank.className = "cal-cell cal-blank";
      grid.appendChild(blank);
    }

    for (var day = 1; day <= days; day++) {
      var dt = new Date(view.getFullYear(), view.getMonth(), day);
      var ds = iso(dt);
      var cell = document.createElement("button");
      cell.type = "button";
      cell.className = "cal-cell cal-day";
      cell.textContent = day;
      cell.setAttribute("data-date", ds);

      var isPast = midnight(dt) < todayMid;
      var isBlocked = blocked.has(ds);
      if (ds === today) cell.classList.add("is-today");

      if (isPast) {
        cell.classList.add("is-disabled", "is-past");
        cell.setAttribute("aria-disabled", "true");
        cell.tabIndex = -1;
        cell.title = "Past date";
      } else if (isBlocked) {
        cell.classList.add("is-blocked-day", "is-selectable");
        cell.title = "Blocked - no bookings. Click to unblock.";
        cell.addEventListener("click", (function (d) {
          return function () { submitDate(d); };
        })(ds));
      } else {
        cell.classList.add("is-selectable");
        cell.title = "Click to block this day";
        cell.addEventListener("click", (function (d) {
          return function () { submitDate(d); };
        })(ds));
      }
      grid.appendChild(cell);
    }

    var curMonthStart = new Date(todayMid.getFullYear(), todayMid.getMonth(), 1);
    prevBtn.disabled = view <= curMonthStart;
  }

  prevBtn.addEventListener("click", function () {
    view = new Date(view.getFullYear(), view.getMonth() - 1, 1);
    render();
  });
  nextBtn.addEventListener("click", function () {
    view = new Date(view.getFullYear(), view.getMonth() + 1, 1);
    render();
  });

  render();
})();
