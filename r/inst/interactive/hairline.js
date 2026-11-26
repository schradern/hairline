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

  // A mark is drawn in its series colour unless it gives its own; "edge" outlines it, "hit" only takes the pointer.
  function draw(series, parent, hit) {
    var reach = data.style.hit;
    series.marks.forEach(function (mark) {
      if (mark.hit && !hit) { return; }
      var paint = hit ? "transparent" : (mark.color || series.color);
      var node;
      if (mark.line) {
        node = element("polyline", { points: points(mark.line), fill: "none", stroke: paint,
          "stroke-width": hit ? Math.max(reach, mark.width) : mark.width, "stroke-linejoin": "round" }, parent);
      } else if (mark.dot) {
        node = element("circle", { cx: mark.dot[0], cy: mark.dot[1], r: hit ? Math.max(reach / 2, mark.r) : mark.r,
          fill: paint }, parent);
      } else if (mark.diamond) {
        var x = mark.diamond[0], y = mark.diamond[1], r = hit ? Math.max(reach / 2, mark.r) : mark.r;
        node = element("polygon", { points: points([[x - r, y], [x, y - r], [x + r, y], [x, y + r]]), fill: paint },
          parent);
      } else if (mark.rect) {
        node = element("rect", { x: mark.rect[0], y: mark.rect[1], width: mark.rect[2],
          height: Math.max(mark.rect[3], hit ? reach : 0), fill: paint,
          "fill-opacity": hit || mark.alpha === undefined ? 1 : mark.alpha }, parent);
        if (hit && mark.rect[3] < reach) { node.setAttribute("y", mark.rect[1] + mark.rect[3] / 2 - reach / 2); }
      } else if (mark.polygon) {
        node = element("polygon", { points: points(mark.polygon), fill: paint,
          "fill-opacity": hit ? 1 : (mark.alpha === undefined ? 1 : mark.alpha) }, parent);
      }
      if (node && mark.edge && !hit) {
        node.setAttribute("stroke", mark.edge);
        node.setAttribute("stroke-width", mark.edge_width || 1);
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

  function highlight(series, at, text) {
    while (focus.firstChild) { focus.removeChild(focus.firstChild); }
    draw(series, focus, false);
    // A series hovered only (a box under its own text) shows its tip without fading the others.
    var drawn = series.marks.some(function (mark) { return !mark.hit; });
    veil.style.display = drawn ? "block" : "none";
    focus.style.display = "block";
    if (text) { place(at, text); } else { tip.style.display = "none"; }
  }

  function hide() { veil.style.display = "none"; focus.style.display = "none"; tip.style.display = "none"; }

  // The figures on one page answer each other (a report's, or several in one document): pointing at a series
  // highlights the series of the same name and colour in every other figure. hairline keeps a group's colour across
  // charts, so the two together are the same group; a name alone could be a chart's own title.
  function linkKey(series) { return series.name + "\n" + String(series.color).toLowerCase().slice(0, 7); }
  var byKey = {}, linked = window.hairlineFigures = window.hairlineFigures || [];
  var self = {
    echo: function (key) { var series = byKey[key]; if (series) { highlight(series, null, null); } else { hide(); } },
    clear: hide
  };
  linked.push(self);

  function others(act) { linked.forEach(function (figure) { if (figure !== self) { act(figure); } }); }

  function show(series, at, text) {
    highlight(series, at, text);
    var key = linkKey(series);
    others(function (figure) { figure.echo(key); });
  }

  function leave() { hide(); others(function (figure) { figure.clear(); }); }

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
    byKey[linkKey(series)] = series;
    var group = element("g", { "class": "hairline-hit", tabindex: 0, role: "img", "aria-label": series.name }, hits);
    draw(series, group, true);
    group.addEventListener("pointermove", function (event) {
      var target = nearest(series, event);
      show(series, target ? target.at : null, target ? target.text : null);
    });
    group.addEventListener("pointerleave", leave);
    group.addEventListener("focus", function () {
      var first = series.tips[0];
      show(series, first ? first.at : null, first ? first.text : series.name);
    });
    group.addEventListener("blur", leave);
  });
  data.legend.forEach(function (entry) {
    var series = byName[entry.name];
    if (!series) { return; }
    var box = element("rect", { x: entry.box[0], y: entry.box[1], width: entry.box[2], height: entry.box[3],
      fill: "transparent", "class": "hairline-hit" }, hits);
    box.addEventListener("pointerenter", function () { show(series, null, null); });
    box.addEventListener("pointerleave", leave);
  });

  // Surfaces turn: dragging or the arrow keys draw the scene again from another angle (hairline-scene.js), Home or a
  // double click returns to the printed view, and a pointer on the surface reads its nearest grid point.
  function text(item, size, parent) {
    var node = element("text", { x: item.x, y: item.y, fill: item.color, "font-size": size,
      "font-family": data.style.font, "text-anchor": { left: "start", center: "middle", right: "end" }[item.align] },
      parent);
    node.textContent = item.text;
  }

  function inside(point, polygon) {
    var found = false;
    for (var i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
      var a = polygon[i], b = polygon[j];
      if ((a[1] > point[1]) !== (b[1] > point[1]) &&
          point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]) { found = !found; }
    }
    return found;
  }

  function pointer(event) {
    var matrix = overlay.getScreenCTM();
    if (!matrix) { return null; }
    var cursor = overlay.createSVGPoint();
    cursor.x = event.clientX;
    cursor.y = event.clientY;
    var at = cursor.matrixTransform(matrix.inverse());
    return [at.x, at.y];
  }

  function drawScene(shown, scene, parent) {
    while (parent.firstChild) { parent.removeChild(parent.firstChild); }
    shown.lines.forEach(function (line) {
      element("polyline", { points: points(line.points), fill: "none", stroke: line.color,
        "stroke-width": line.width }, parent);
    });
    shown.cells.forEach(function (cell) {
      element("polygon", { points: points(cell.points), fill: cell.fill, stroke: cell.fill,
        "stroke-width": scene.seam, "stroke-linejoin": "miter" }, parent);
    });
    shown.texts.forEach(function (item) { text(item, scene.text.size, parent); });
  }

  // The grid point nearest `at` on the frontmost cell under it, as [cell, corner index], or null off the surface.
  function nearestPoint(shown, at) {
    for (var k = shown.cells.length - 1; k >= 0; k -= 1) {
      var cell = shown.cells[k];
      if (!inside(at, cell.points)) { continue; }
      var distances = cell.points.map(function (p) { return Math.pow(p[0] - at[0], 2) + Math.pow(p[1] - at[1], 2); });
      return [cell, distances.indexOf(Math.min.apply(null, distances))];
    }
    return null;
  }

  function tipText(scene, corner) {
    return scene.titles.x.text + " " + scene.tips.x[corner[0]] + ", " + scene.titles.y.text + " " +
      scene.tips.y[corner[1]] + ": " + scene.tips.z[corner[1]][corner[0]];
  }

  // The outlines that mark one grid point: the surface cell under the pointer, the heatmap cell of the same point
  // and a ring at the point on the surface.
  function pointMarks(scene, layer) {
    var stroke = { fill: "none", stroke: data.style.ink, "stroke-width": 1, display: "none" };
    var surface = element("polygon", stroke, layer), cell = element("rect", stroke, layer);
    var ring = element("circle", Object.assign({ r: 2.5 }, stroke), layer), cells = {};
    (scene.flat ? scene.flat.cells : []).forEach(function (found) { cells[found[4] + "," + found[5]] = found; });
    function show(node, attributes) {
      Object.keys(attributes).forEach(function (key) { node.setAttribute(key, attributes[key]); });
      node.setAttribute("display", "inline");
    }
    return {
      cells: scene.flat ? scene.flat.cells : [],
      clear: function () {
        [surface, cell, ring].forEach(function (node) { node.setAttribute("display", "none"); });
        tip.style.display = "none";
      },
      surface: function (polygon) { show(surface, { points: points(polygon) }); },
      cell: function (corner) {
        var found = cells[corner[0] + "," + corner[1]];
        if (found) { show(cell, { x: found[0], y: found[1], width: found[2], height: found[3] }); }
      },
      ring: function (at) { if (at) { show(ring, { cx: at[0], cy: at[1] }); } }
    };
  }

  function readPoint(scene, shown, at, marks) {
    var found = nearestPoint(shown, at);
    var corner = found && found[0].corners[found[1]];
    marks.clear();
    if (!corner || !scene.tips.z[corner[1]][corner[0]]) { return; }
    marks.surface(found[0].points);
    marks.cell(corner);
    place(found[0].points[found[1]], tipText(scene, corner));
  }

  // A pointer on the heatmap beside a surface: its cell, and the same grid point marked on the surface.
  function readCell(scene, shown, at, marks) {
    marks.clear();
    var found = marks.cells.filter(function (cell) {
      return at[0] >= cell[0] && at[0] <= cell[0] + cell[2] && at[1] >= cell[1] && at[1] <= cell[1] + cell[3];
    })[0];
    if (!found || !scene.tips.z[found[5]][found[4]]) { return; }
    var corner = [found[4], found[5]];
    marks.cell(corner);
    marks.ring(shown.vertex(corner[0], corner[1]));
    place([found[0] + found[2] / 2, found[1]], tipText(scene, corner));
  }

  function bindCells(scene, layer, surface) {
    var box = scene.flat.box;
    var hit = element("rect", { x: box[0], y: box[1], width: box[2], height: box[3], fill: "transparent",
      "class": "hairline-hit" }, layer);
    hit.addEventListener("pointermove", function (event) { var at = pointer(event); if (at) { surface.cell(at); } });
    hit.addEventListener("pointerleave", surface.leave);
  }

  // Pointer and keys of a turnable surface: dragging and the arrow keys call turn(azimuth, elevation) from the
  // current view, Home, Escape and a double click turn back to the printed one.
  function bindTurning(hit, surface) {
    var drag = null, turning = surface.scene.turning, printed = surface.scene.view;
    hit.addEventListener("pointerdown", function (event) {
      hit.setPointerCapture(event.pointerId);
      drag = { x: event.clientX, y: event.clientY, view: surface.view() };
    });
    hit.addEventListener("pointermove", function (event) {
      if (!drag) { var at = pointer(event); if (at) { surface.read(at); } return; }
      var rate = turning.drag_degrees_per_pt * data.width / root.clientWidth;
      surface.turn(drag.view.azimuth - (event.clientX - drag.x) * rate,
        drag.view.elevation + (event.clientY - drag.y) * rate);
    });
    hit.addEventListener("pointerup", function () { drag = null; });
    hit.addEventListener("pointercancel", function () { drag = null; });
    hit.addEventListener("pointerleave", function () { if (!drag) { surface.leave(); } });
    hit.addEventListener("dblclick", function () { surface.turn(printed.azimuth, printed.elevation); });
    hit.addEventListener("keydown", function (event) {
      var view = surface.view();
      var steps = { ArrowLeft: [turning.turn_step, 0], ArrowRight: [-turning.turn_step, 0],
        ArrowUp: [0, turning.tilt_step], ArrowDown: [0, -turning.tilt_step] }[event.key];
      if (steps) { surface.turn(view.azimuth + steps[0], view.elevation + steps[1]); }
      else if (event.key === "Home" || event.key === "Escape") { surface.turn(printed.azimuth, printed.elevation); }
      else { return; }
      event.preventDefault();
    });
  }

  function turnable(scene) {
    var box = scene.box || data.panels[scene.panel], printed = scene.view;
    var first = hairlineSceneShapes(scene, box, printed, Infinity);
    if (!first) { return; }
    var layer = element("g", {}, overlay);
    var cover = element("rect", { x: box[0], y: box[1], width: box[2], height: box[3], fill: data.style.surface,
      display: "none" }, layer);
    var drawn = element("g", {}, layer);
    var marks = pointMarks(scene, layer);
    var hit = element("rect", { x: box[0], y: box[1], width: box[2], height: box[3], fill: "transparent",
      tabindex: 0, role: "img", "aria-label": scene.hint, "class": "hairline-hit hairline-turn" }, layer);
    var view = { elevation: printed.elevation, azimuth: printed.azimuth }, shown = first, frame = 0;

    function draw() {
      frame = 0;
      var turned = view.elevation !== printed.elevation || view.azimuth !== printed.azimuth;
      shown = turned ? hairlineSceneShapes(scene, box, view, first.scale) || shown : first;
      cover.setAttribute("display", turned ? "inline" : "none");
      drawScene(turned ? shown : { lines: [], cells: [], texts: [] }, scene, drawn);
    }
    var surface = {
      scene: scene,
      view: function () { return view; },
      read: function (at) { readPoint(scene, shown, at, marks); },
      cell: function (at) { readCell(scene, shown, at, marks); },
      leave: function () { marks.clear(); hide(); },
      turn: function (azimuth, elevation) {
        var limits = scene.turning.elevation_limits;
        view = { azimuth: ((azimuth + 180) % 360 + 360) % 360 - 180,
          elevation: Math.min(limits[1], Math.max(limits[0], elevation)) };
        marks.clear();
        if (!frame) { frame = window.requestAnimationFrame(draw); }
      }
    };
    bindTurning(hit, surface);
    if (scene.flat) { bindCells(scene, layer, surface); }
    hit.addEventListener("focus", function () { place([box[0] + box[2] / 2, box[1]], scene.hint); });
    hit.addEventListener("blur", hide);
  }

  if (data.scenes && typeof hairlineSceneShapes === "function") { data.scenes.forEach(turnable); }
}());
