/* hairline surfaces: the scene of a surface chart projected, fitted and ordered far to near, as Python's
   charts/surface_geometry.py and R's surface_layout.R do for the printed view. Shared by both packages; the figure
   script draws it again from the reader's angle. Exposes hairlineSceneShapes(scene, box, view, largest). */
var hairlineSceneShapes = (function () {
  "use strict";
  var DEPTH = 1e9, SHORT = 1e-9;

  function rounded(value) { return Math.round(value * DEPTH) / DEPTH; }

  function projector(view) {
    var azimuth = view.azimuth * Math.PI / 180, elevation = view.elevation * Math.PI / 180;
    var turnCos = Math.cos(azimuth), turnSin = Math.sin(azimuth);
    var tiltCos = Math.cos(elevation), tiltSin = Math.sin(elevation);
    return function (point) {
      var across = point[0] * turnCos - point[1] * turnSin, back = point[0] * turnSin + point[1] * turnCos;
      return [across, -(point[2] * tiltCos + back * tiltSin), back * tiltCos - point[2] * tiltSin];
    };
  }

  function smallest(items, key) {
    var best = 0;
    items.forEach(function (item, index) { if (key(item) < key(items[best])) { best = index; } });
    return items[best];
  }

  function cubeFrame(scene, project) {
    var floor = -scene.height / 2;
    var near = smallest([[-1, -1], [1, -1], [-1, 1], [1, 1]],
      function (corner) { return rounded(project([corner[0], corner[1], floor])[2]); });
    var sides = [[-near[0], near[1]], [near[0], -near[1]]];
    var side = smallest(sides, function (corner) { return rounded(project([corner[0], corner[1], floor])[0]); });
    return { floor: floor, top: -floor, near: near, zCorner: side, otherCorner: side === sides[0] ? sides[1] : sides[0],
      far: [-near[0], -near[1]] };
  }

  function at(scene, axis) { return scene.ticks[axis].map(function (tick) { return tick.at; }); }

  function frameLines(scene, frame) {
    var floor = frame.floor, top = frame.top, near = frame.near, far = frame.far, grid = [];
    at(scene, "x").forEach(function (v) { grid.push([[v, -1, floor], [v, 1, floor]]); });
    at(scene, "y").forEach(function (v) { grid.push([[-1, v, floor], [1, v, floor]]); });
    at(scene, "z").forEach(function (v) { grid.push([[far[0], -1, v], [far[0], 1, v]]); });
    at(scene, "z").forEach(function (v) { grid.push([[-1, far[1], v], [1, far[1], v]]); });
    grid.push([[far[0], -1, floor], [far[0], 1, floor]], [[-1, far[1], floor], [1, far[1], floor]]);
    [far, frame.otherCorner].forEach(function (c) { grid.push([[c[0], c[1], floor], [c[0], c[1], top]]); });
    var z = frame.zCorner;
    var axes = [[[-1, near[1], floor], [1, near[1], floor]], [[near[0], -1, floor], [near[0], 1, floor]],
      [[z[0], z[1], floor], [z[0], z[1], top]]];
    return grid.map(function (s) { return [s, "grid"]; }).concat(axes.map(function (s) { return [s, "axis"]; }));
  }

  function unit(vector) {
    var length = Math.sqrt(vector[0] * vector[0] + vector[1] * vector[1]);
    return length < SHORT ? [0, 1] : [vector[0] / length, vector[1] / length];
  }

  function placement(direction, scene) {
    var threshold = scene.align, glyphs = scene.text;
    var align = direction[0] > threshold ? "left" : direction[0] < -threshold ? "right" : "center";
    var shift = direction[1] > threshold ? glyphs.cap : direction[1] < -threshold ? -glyphs.descender : glyphs.cap / 2;
    return [align, shift];
  }

  function label(point, offset, text, width, color, part, placed) {
    return { at: [point[0], point[1]], offset: offset, text: text, width: width, color: color, part: part,
      align: placed[0], shift: placed[1] };
  }

  function reach(direction, labels, scene) {
    var tall = scene.text.cap + scene.text.descender;
    return labels.reduce(function (most, item) {
      return Math.max(most, Math.abs(direction[0]) * item.width + Math.abs(direction[1]) * tall);
    }, 0);
  }

  function floorLabels(scene, frame, project, axis) {
    var floor = frame.floor, near = frame.near, gap = scene.gap;
    var edge = axis === "x" ? function (v) { return [v, near[1], floor]; }
      : function (v) { return [near[0], v, floor]; };
    var middle = project(edge(0)), centre = project([0, 0, floor]);
    var direction = unit([middle[0] - centre[0], middle[1] - centre[1]]), placed = placement(direction, scene);
    var labels = scene.ticks[axis].map(function (tick) {
      return label(project(edge(tick.at)), [direction[0] * gap, direction[1] * gap], tick.text, tick.width,
        scene.text.ticks, "tick", placed);
    });
    var title = scene.titles[axis];
    if (!title.text) { return labels; }
    var across = normal(project(edge(-1)), project(edge(1)), direction);
    var away = 2 * gap + reach(across, labels, scene);
    return labels.concat([label(middle, [across[0] * away, across[1] * away], title.text, title.width,
      scene.text.titles, "title", placement(across, scene))]);
  }

  function normal(start, end, direction) {
    var run = [end[0] - start[0], end[1] - start[1]];
    if (Math.sqrt(run[0] * run[0] + run[1] * run[1]) < SHORT) { return direction; }
    var across = unit([-run[1], run[0]]);
    return across[0] * direction[0] + across[1] * direction[1] >= 0 ? across : [-across[0], -across[1]];
  }

  function heightLabels(scene, frame, project) {
    var corner = frame.zCorner, gap = scene.gap, glyphs = scene.text;
    var side = project([corner[0], corner[1], frame.floor])[0] <= 0 ? -1 : 1;
    var placed = [side < 0 ? "right" : "left", glyphs.cap / 2];
    var labels = scene.ticks.z.map(function (tick) {
      return label(project([corner[0], corner[1], tick.at]), [side * gap, 0], tick.text, tick.width, glyphs.ticks,
        "tick", placed);
    });
    var title = scene.titles.z;
    if (!title.text) { return labels; }
    var rise = -(glyphs.cap / 2 + gap + glyphs.descender);
    return labels.concat([label(project([corner[0], corner[1], frame.top]), [side * gap, rise], title.text,
      title.width, glyphs.titles, "title", [placed[0], 0])]);
  }

  function labelSpan(item, scene) {
    var share = { left: 0, center: 0.5, right: 1 }[item.align];
    var left = item.offset[0] - share * item.width, baseline = item.offset[1] + item.shift;
    return [[left, left + item.width], [baseline - scene.text.cap, baseline + scene.text.descender]];
  }

  function extent(items, scale) {
    var start = Infinity, end = -Infinity;
    items.forEach(function (item) {
      start = Math.min(start, scale * item[0] + item[1]);
      end = Math.max(end, scale * item[0] + item[2]);
    });
    return [start, end];
  }

  function largestScale(items, room) {
    var scale = Infinity;
    items.forEach(function (one) {
      items.forEach(function (other) {
        if (one[0] - other[0] > SHORT) { scale = Math.min(scale, (room - one[2] + other[1]) / (one[0] - other[0])); }
      });
    });
    var span = extent(items, scale);
    return span[1] - span[0] <= room + 1e-6 ? scale : -Infinity;
  }

  function fitted(scene, box, corners, labels, largest) {
    var spans = labels.map(function (item) { return labelSpan(item, scene); });
    function rows(index) {
      return corners.map(function (c) { return [c[index], 0, 0]; }).concat(labels.map(function (item, k) {
        return [item.at[index], spans[k][index][0], spans[k][index][1]];
      }));
    }
    var across = rows(0), down = rows(1);
    var scale = Math.min(largestScale(across, box[2]), largestScale(down, box[3]), largest);
    if (!(scale > 0) || !isFinite(scale)) { return null; }
    var horizontal = extent(across, scale), vertical = extent(down, scale);
    return { scale: scale, offset: [box[0] + (box[2] - (horizontal[1] - horizontal[0])) / 2 - horizontal[0],
      box[1] - vertical[0]] };
  }

  function cellShapes(scene, project, place) {
    var xs = scene.xs, ys = scene.ys, cells = [];
    for (var row = 0; row < ys.length - 1; row += 1) {
      for (var column = 0; column < xs.length - 1; column += 1) {
        var fill = scene.fills[row][column];
        if (typeof fill !== "string") { continue; }
        var corners = [[column, row], [column + 1, row], [column + 1, row + 1], [column, row + 1]];
        var projected = corners.map(function (c) { return project([xs[c[0]], ys[c[1]], scene.zs[c[1]][c[0]]]); });
        var depth = rounded(projected.reduce(function (sum, p) { return sum + p[2]; }, 0) / 4);
        cells.push({ depth: depth, index: cells.length, fill: fill, corners: corners, projected: projected });
      }
    }
    cells.sort(function (a, b) { return b.depth - a.depth || a.index - b.index; });
    return cells.map(function (cell) {
      return { points: cell.projected.map(place), fill: cell.fill, corners: cell.corners };
    });
  }

  // Lines, cells far to near and texts in pt, or null where the labels leave the surface no room. `largest` caps
  // the scale, so turning never draws the surface larger than it was printed.
  return function (scene, box, view, largest) {
    var project = projector(view), frame = cubeFrame(scene, project);
    var labels = floorLabels(scene, frame, project, "x").concat(floorLabels(scene, frame, project, "y"),
      heightLabels(scene, frame, project));
    var corners = [];
    [frame.floor, frame.top].forEach(function (z) {
      [-1, 1].forEach(function (y) { [-1, 1].forEach(function (x) { corners.push(project([x, y, z])); }); });
    });
    var fit = fitted(scene, box, corners, labels, largest);
    if (!fit) { return null; }
    function place(point) { return [fit.offset[0] + fit.scale * point[0], fit.offset[1] + fit.scale * point[1]]; }
    return {
      scale: fit.scale,
      // Where grid point (column, row) is drawn in this view, or null where it has no value.
      vertex: function (column, row) {
        var z = scene.zs[row][column];
        return typeof z === "number" ? place(project([scene.xs[column], scene.ys[row], z])) : null;
      },
      lines: frameLines(scene, frame).map(function (line) {
        return { points: line[0].map(function (end) { return place(project(end)); }), color: scene.lines[line[1]],
          width: scene.lines[line[1] + "_width"] };
      }),
      cells: cellShapes(scene, project, place),
      texts: labels.map(function (item) {
        var point = place(item.at);
        return { x: point[0] + item.offset[0], y: point[1] + item.offset[1] + item.shift, text: item.text,
          color: item.color, align: item.align, part: item.part };
      })
    };
  };
}());
if (typeof module !== "undefined") { module.exports = hairlineSceneShapes; }
