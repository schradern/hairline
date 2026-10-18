/* hairline interactive figures: tooltips and series highlighting over the static SVG, drawn from the targets in
   the figure's JSON (positions in pt from the top-left corner). Shared by the Python and R packages. */
(function () {
  "use strict";
  var root = document.currentScript.parentNode;
  var data = JSON.parse(root.querySelector("script.hairline-targets").textContent);
  var overlay = root.querySelector("svg.hairline-overlay");
  var tip = root.querySelector(".hairline-tip");
  var NS = "http://www.w3.org/2000/svg";

  function element(name, attributes, parent) {
    var node = document.createElementNS(NS, name);
    Object.keys(attributes).forEach(function (key) { node.setAttribute(key, attributes[key]); });
    parent.appendChild(node);
    return node;
  }

  function points(list) { return list.map(function (point) { return point[0] + "," + point[1]; }).join(" "); }

  function draw(series, parent, hit) {
    var reach = data.style.hit;
    series.marks.forEach(function (mark) {
      var paint = hit ? "transparent" : series.color;
      if (mark.line) {
        element("polyline", { points: points(mark.line), fill: "none", stroke: paint,
          "stroke-width": hit ? Math.max(reach, mark.width) : mark.width, "stroke-linejoin": "round" }, parent);
      } else if (mark.dot) {
        element("circle", { cx: mark.dot[0], cy: mark.dot[1], r: hit ? Math.max(reach / 2, mark.r) : mark.r,
          fill: paint }, parent);
      } else if (mark.rect) {
        element("rect", { x: mark.rect[0], y: mark.rect[1], width: mark.rect[2], height: mark.rect[3],
          fill: paint }, parent);
      } else if (mark.polygon) {
        element("polygon", { points: points(mark.polygon), fill: paint,
          "fill-opacity": hit ? 1 : (mark.alpha === undefined ? 1 : mark.alpha) }, parent);
      }
    });
  }

  var veil = element("g", { "class": "hairline-veil" }, overlay);
  data.panels.forEach(function (box) {
    element("rect", { x: box[0], y: box[1], width: box[2], height: box[3], fill: data.style.surface,
      "fill-opacity": data.style.veil }, veil);
  });
  var focus = element("g", { "class": "hairline-veil" }, overlay);
  var hits = element("g", {}, overlay);

  function place(at, text) {
    var scale = root.clientWidth / data.width;
    tip.textContent = text;
    tip.style.fontSize = (data.style.size * scale) + "px";
    tip.style.left = (at[0] / data.width * 100) + "%";
    tip.style.top = (at[1] / data.height * 100) + "%";
    tip.style.display = "block";
  }

  function show(series, at, text) {
    while (focus.firstChild) { focus.removeChild(focus.firstChild); }
    draw(series, focus, false);
    veil.style.display = "block";
    focus.style.display = "block";
    if (text) { place(at, text); } else { tip.style.display = "none"; }
  }

  function hide() { veil.style.display = "none"; focus.style.display = "none"; tip.style.display = "none"; }

  function nearest(series, event) {
    var matrix = overlay.getScreenCTM();
    if (!matrix || !series.tips.length) { return null; }
    var cursor = overlay.createSVGPoint();
    cursor.x = event.clientX;
    cursor.y = event.clientY;
    var at = cursor.matrixTransform(matrix.inverse());
    var best = series.tips[0], distance = Infinity;
    series.tips.forEach(function (candidate) {
      var dx = candidate.at[0] - at.x, dy = candidate.at[1] - at.y, gap = dx * dx + dy * dy;
      if (gap < distance) { distance = gap; best = candidate; }
    });
    return best;
  }

  var byName = {};
  data.series.forEach(function (series) {
    byName[series.name] = series;
    var group = element("g", { "class": "hairline-hit", tabindex: 0, role: "img", "aria-label": series.name }, hits);
    draw(series, group, true);
    group.addEventListener("pointermove", function (event) {
      var target = nearest(series, event);
      show(series, target ? target.at : null, target ? target.text : null);
    });
    group.addEventListener("pointerleave", hide);
    group.addEventListener("focus", function () {
      var first = series.tips[0];
      show(series, first ? first.at : null, first ? first.text : series.name);
    });
    group.addEventListener("blur", hide);
  });
  data.legend.forEach(function (entry) {
    var series = byName[entry.name];
    if (!series) { return; }
    var box = element("rect", { x: entry.box[0], y: entry.box[1], width: entry.box[2], height: entry.box[3],
      fill: "transparent", "class": "hairline-hit" }, hits);
    box.addEventListener("pointerenter", function () { show(series, null, null); });
    box.addEventListener("pointerleave", hide);
  });
}());
