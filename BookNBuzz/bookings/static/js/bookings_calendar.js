/* BookN'Buzz - "jump to date" month calendar popover for Manage bookings.
 *
 * Clicking the date heading opens a month grid. Days that have bookings show a
 * dot. Clicking a day navigates the page to ?date=YYYY-MM-DD. Reuses the shared
 * .calendar / .cal-* styles from the Availability page.
 */
(function () {
  "use strict";

  var heading = document.getElementById("date-heading");
  var pop = document.getElementById("bk-pop");
  if (!heading || !pop) return;  // pending tab: no popover

  var grid = pop.querySelector(".cal-grid");
  var titleEl = pop.querySelector(".cal-title");
  var prevBtn = pop.querySelector(".cal-prev");
  var nextBtn = pop.querySelector(".cal-next");

  var MONTHS = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"];

  var selected = pop.dataset.selected;
  var today = pop.dataset.today;
  var counts = JSON.parse(pop.dataset.counts || "{}");

  function parseISO(s) { var p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function iso(dt) {
    return dt.getFullYear() + "-" +
           String(dt.getMonth() + 1).padStart(2, "0") + "-" +
           String(dt.getDate()).padStart(2, "0");
  }
  function pyWeekday(dt) { return (dt.getDay() + 6) % 7; }  // Mon=0..Sun=6

  var sel = parseISO(selected);
  var view = new Date(sel.getFullYear(), sel.getMonth(), 1);

  function go(ds) {
    var u = new URL(window.location.href);
    u.searchParams.set("date", ds);
    u.searchParams.delete("status");
    u.searchParams.delete("view");
    window.location.href = u.toString();
  }

  function render() {
    grid.innerHTML = "";
    titleEl.textContent = MONTHS[view.getMonth()] + " " + view.getFullYear();
    var lead = pyWeekday(new Date(view.getFullYear(), view.getMonth(), 1));
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
      cell.className = "cal-cell cal-day is-selectable";
      cell.textContent = day;
      cell.setAttribute("data-date", ds);
      if (ds === today) cell.classList.add("is-today");
      if (ds === selected) cell.classList.add("is-selected");
      if (counts[ds]) {
        var dot = document.createElement("span");
        dot.className = "cal-count";
        dot.title = counts[ds] + " booking(s)";
        cell.appendChild(dot);
      }
      cell.addEventListener("click", (function (d) {
        return function () { go(d); };
      })(ds));
      grid.appendChild(cell);
    }
  }

  prevBtn.addEventListener("click", function () {
    view = new Date(view.getFullYear(), view.getMonth() - 1, 1);
    render();
  });
  nextBtn.addEventListener("click", function () {
    view = new Date(view.getFullYear(), view.getMonth() + 1, 1);
    render();
  });

  function openPop() { pop.hidden = false; heading.setAttribute("aria-expanded", "true"); }
  function closePop() { pop.hidden = true; heading.setAttribute("aria-expanded", "false"); }

  heading.addEventListener("click", function (e) {
    e.stopPropagation();
    if (pop.hidden) openPop(); else closePop();
  });
  pop.addEventListener("click", function (e) { e.stopPropagation(); });
  document.addEventListener("click", function () { if (!pop.hidden) closePop(); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !pop.hidden) closePop();
  });

  render();
})();
