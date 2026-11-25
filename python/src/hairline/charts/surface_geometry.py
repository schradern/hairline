"""Surface geometry in pt: a grid of values seen from a viewpoint (orthographic projection), drawn back to front as
flat polygons over a floor and two back walls, with ticks on the edges nearest the viewer.

The scene is the view-independent part (the grid in a cube of width 2, the fills, ticks and titles with their widths);
`scene_shapes()` projects it for one view and fits it into the plot box. Pure; mirrored in R's surface_geometry.R and
in the shared interactive script, which draws the same scene again as the reader turns it."""

from __future__ import annotations

import math

from hairline.charts.donut_geometry import Measure, text
from hairline.errors import HairlineLayoutError
from hairline.layout.geometry import Box
from hairline.tokens import load_tokens

AXES = ("x", "y", "z")
# Depths are rounded before sorting so the order of equally deep cells is the same in Python, R and the browser.
DEPTH_DIGITS = 9
# A direction shorter than this has no side (an edge seen end on); its labels go below it.
SHORT = 1e-9


def surface_scene(spec: dict, measure: Measure, style: dict) -> dict:
    """The spec with every text's width in pt and the colours and sizes the drawing needs: all the browser needs to
    draw it again from another angle."""
    rules, neutral, size = load_tokens()["surface"], style["neutral"], style["sizes"]["label"]
    ticks = {axis: [{**tick, "width": measure(tick["text"], "label")} for tick in spec["ticks"][axis]]
             for axis in AXES}
    titles = {axis: {"text": title, "width": measure(title, "label") if title else 0.0}
              for axis, title in spec["titles"].items()}
    return {"xs": spec["xs"], "ys": spec["ys"], "zs": spec["zs"], "fills": spec["fills"], "height": spec["height"],
            "view": spec["view"], "ticks": ticks, "titles": titles,
            "text": {"size": size, "cap": style["cap_height"] * size, "descender": style["descender"] * size,
                     "ticks": neutral["faint"], "titles": neutral["muted"]},
            "lines": {"axis": neutral["axis"], "grid": neutral["grid"], "axis_width": style["axis_width"],
                      "grid_width": style["grid"]},
            "gap": rules["label_gap"] * style["base"], "align": rules["align"], "seam": rules["seam_pt"]}


def projector(view: dict):
    """Cube point -> [across, down, depth]: turned by the azimuth about the vertical axis, tilted by the elevation;
    depth grows away from the viewer."""
    azimuth, elevation = math.radians(view["azimuth"]), math.radians(view["elevation"])
    turn_cos, turn_sin = math.cos(azimuth), math.sin(azimuth)
    tilt_cos, tilt_sin = math.cos(elevation), math.sin(elevation)

    def project(point) -> list[float]:
        x, y, z = point
        across, back = x * turn_cos - y * turn_sin, x * turn_sin + y * turn_cos
        return [across, -(z * tilt_cos + back * tilt_sin), back * tilt_cos - z * tilt_sin]
    return project


def cube_frame(scene: dict, project) -> dict:
    """Which edges carry the axes in this view: x and y along the floor edges that meet at the floor corner nearest
    the viewer, z up the side edge at the leftmost floor corner next to it."""
    floor = -scene["height"] / 2
    corners = [(x, y) for y in (-1, 1) for x in (-1, 1)]
    near_x, near_y = min(corners, key=lambda corner: round(project((*corner, floor))[2], DEPTH_DIGITS))
    sides = [(-near_x, near_y), (near_x, -near_y)]
    side_x, side_y = min(sides, key=lambda corner: round(project((*corner, floor))[0], DEPTH_DIGITS))
    return {"floor": floor, "top": -floor, "near": (near_x, near_y), "z_corner": (side_x, side_y),
            "other_corner": next(corner for corner in sides if corner != (side_x, side_y)),
            "far": (-near_x, -near_y)}


def frame_lines(scene: dict, frame: dict) -> list[tuple[list, str]]:
    """Segments of the floor, the two back walls and the three axes, each with its line kind."""
    floor, top = frame["floor"], frame["top"]
    near_x, near_y = frame["near"]
    far_x, far_y = frame["far"]
    ticks = {axis: [tick["at"] for tick in scene["ticks"][axis]] for axis in AXES}
    grid = [[(at, -1, floor), (at, 1, floor)] for at in ticks["x"]]
    grid += [[(-1, at, floor), (1, at, floor)] for at in ticks["y"]]
    grid += [[(far_x, -1, at), (far_x, 1, at)] for at in ticks["z"]]
    grid += [[(-1, far_y, at), (1, far_y, at)] for at in ticks["z"]]
    grid += [[(far_x, -1, floor), (far_x, 1, floor)], [(-1, far_y, floor), (1, far_y, floor)]]
    grid += [[(*corner, floor), (*corner, top)] for corner in (frame["far"], frame["other_corner"])]
    axes = [[(-1, near_y, floor), (1, near_y, floor)], [(near_x, -1, floor), (near_x, 1, floor)],
            [(*frame["z_corner"], floor), (*frame["z_corner"], top)]]
    return [(segment, "grid") for segment in grid] + [(segment, "axis") for segment in axes]


def unit(vector: list[float]) -> list[float]:
    length = math.hypot(*vector)
    return [0.0, 1.0] if length < SHORT else [vector[0] / length, vector[1] / length]


def placement(direction: list[float], scene: dict) -> tuple[str, float]:
    """Alignment and baseline shift of a text set off from its point along `direction`: to the side it points to,
    below the point when it points down, above it when up."""
    threshold, glyphs = scene["align"], scene["text"]
    align = "left" if direction[0] > threshold else "right" if direction[0] < -threshold else "center"
    shift = glyphs["cap"] if direction[1] > threshold else -glyphs["descender"] if direction[1] < -threshold \
        else glyphs["cap"] / 2
    return align, shift


def label(point: list[float], offset: list[float], content: str, width: float, color: str, part: str,
          placed: tuple[str, float]) -> dict:
    """A text at a projected point (unit coordinates) set off by `offset` pt, before the scene is scaled."""
    return {"at": point[:2], "offset": offset, "text": content, "width": width, "color": color, "part": part,
            "align": placed[0], "shift": placed[1]}


def reach(direction: list[float], labels: list[dict], scene: dict) -> float:
    """How far the widest of `labels` reaches along `direction`, to set the axis title beyond them."""
    tall = scene["text"]["cap"] + scene["text"]["descender"]
    return max((abs(direction[0]) * item["width"] + abs(direction[1]) * tall for item in labels), default=0.0)


def floor_labels(scene: dict, frame: dict, project, axis: str) -> list[dict]:
    """Tick labels and the title of the x or y axis, set off outward from the floor's centre."""
    floor, (near_x, near_y) = frame["floor"], frame["near"]
    edge = (lambda at: (at, near_y, floor)) if axis == "x" else (lambda at: (near_x, at, floor))
    middle, centre = project(edge(0.0)), project((0.0, 0.0, floor))
    direction, gap = unit([middle[0] - centre[0], middle[1] - centre[1]]), scene["gap"]
    placed, colours = placement(direction, scene), scene["text"]
    ticks = [label(project(edge(tick["at"])), [direction[0] * gap, direction[1] * gap], tick["text"],
                   tick["width"], colours["ticks"], "tick", placed) for tick in scene["ticks"][axis]]
    title = scene["titles"][axis]
    if not title["text"]:
        return ticks
    across = normal(project(edge(-1.0)), project(edge(1.0)), direction)
    away = 2 * gap + reach(across, ticks, scene)
    return ticks + [label(middle, [across[0] * away, across[1] * away], title["text"], title["width"],
                          colours["titles"], "title", placement(across, scene))]


def normal(start: list[float], end: list[float], direction: list[float]) -> list[float]:
    """The unit normal of an edge on the page, on the side `direction` points to: an axis title set off along it
    clears every tick label of the edge, wherever along the edge they sit."""
    run = [end[0] - start[0], end[1] - start[1]]
    if math.hypot(*run) < SHORT:
        return direction
    across = unit([-run[1], run[0]])
    return across if across[0] * direction[0] + across[1] * direction[1] >= 0 else [-across[0], -across[1]]


def height_labels(scene: dict, frame: dict, project) -> list[dict]:
    """Tick labels of the z axis beside its edge, away from the cube, and its title above them."""
    corner, gap, glyphs = frame["z_corner"], scene["gap"], scene["text"]
    side = -1.0 if project((*corner, frame["floor"]))[0] <= 0 else 1.0
    placed = ("right" if side < 0 else "left", glyphs["cap"] / 2)
    ticks = [label(project((*corner, tick["at"])), [side * gap, 0.0], tick["text"], tick["width"], glyphs["ticks"],
                   "tick", placed) for tick in scene["ticks"]["z"]]
    title = scene["titles"]["z"]
    if not title["text"]:
        return ticks
    rise = -(glyphs["cap"] / 2 + gap + glyphs["descender"])
    return ticks + [label(project((*corner, frame["top"])), [side * gap, rise], title["text"], title["width"],
                          glyphs["titles"], "title", (placed[0], 0.0))]


def label_span(item: dict, scene: dict) -> tuple[tuple[float, float], tuple[float, float]]:
    """A label's extent in pt around its scaled point: (left, right) and (top, bottom)."""
    share = {"left": 0.0, "center": 0.5, "right": 1.0}[item["align"]]
    left = item["offset"][0] - share * item["width"]
    baseline = item["offset"][1] + item["shift"]
    return (left, left + item["width"]), (baseline - scene["text"]["cap"], baseline + scene["text"]["descender"])


def extent(items: list[tuple[float, float, float]], scale: float) -> tuple[float, float]:
    """Where points with fixed extents (low, high) in pt start and end at `scale`."""
    return min(scale * point + low for point, low, _ in items), max(scale * point + high for point, _, high in items)


def largest_scale(items: list[tuple[float, float, float]], room: float) -> float:
    """The largest scale at which points with fixed extents (low, high) in pt span at most `room`: each pair of a
    point further along and one before it bounds the scale; none is found when even that scale overflows."""
    scale = math.inf
    for point, _, high in items:
        for other, low, _ in items:
            if point - other > SHORT:
                scale = min(scale, (room - high + low) / (point - other))
    start, end = extent(items, scale)
    return scale if end - start <= room + 1e-6 else -math.inf


def fitted(scene: dict, box: Box, corners: list[list[float]], labels: list[dict]) -> tuple[float, list[float]]:
    """Scale and offset that fit the cube's corners and every label into the box: as large as the tighter side
    allows, centred across and set at the top."""
    spans = [label_span(item, scene) for item in labels]
    across = [(corner[0], 0.0, 0.0) for corner in corners] + [(item["at"][0], *span[0])
                                                              for item, span in zip(labels, spans, strict=True)]
    down = [(corner[1], 0.0, 0.0) for corner in corners] + [(item["at"][1], *span[1])
                                                            for item, span in zip(labels, spans, strict=True)]
    scale = min(largest_scale(across, box.width), largest_scale(down, box.height))
    if not scale > 0 or math.isinf(scale):
        raise HairlineLayoutError(f"hairline: surface: the axis labels leave no room for the surface in "
                                  f"{box.width:.0f} x {box.height:.0f} pt. Shorten the axis titles or use a wider size")
    (left, right), (top, _) = extent(across, scale), extent(down, scale)
    return scale, [box.x + (box.width - (right - left)) / 2 - left, box.y - top]


def scene_shapes(scene: dict, box: Box, view: dict | None = None) -> list[dict]:
    """The scene from `view` (its own by default), fitted into the box: lines, then cells far to near, then texts."""
    project = projector(view or scene["view"])
    frame = cube_frame(scene, project)
    labels = floor_labels(scene, frame, project, "x") + floor_labels(scene, frame, project, "y") + \
        height_labels(scene, frame, project)
    corners = [project((x, y, z)) for z in (frame["floor"], frame["top"]) for y in (-1, 1) for x in (-1, 1)]
    scale, offset = fitted(scene, box, corners, labels)

    def place(point) -> list[float]:
        return [offset[0] + scale * point[0], offset[1] + scale * point[1]]
    lines = scene["lines"]
    shapes = [{"kind": "line", "points": [place(project(end)) for end in segment], "color": lines[kind],
               "width": lines[f"{kind}_width"]} for segment, kind in frame_lines(scene, frame)]
    shapes += cell_shapes(scene, project, place)
    for item in labels:
        x, y = place(item["at"])
        shapes.append({**text(x + item["offset"][0], y + item["offset"][1] + item["shift"], item["text"], "label",
                              item["color"], item["align"]), "part": item["part"]})
    return shapes


def cell_shapes(scene: dict, project, place) -> list[dict]:
    """One polygon per cell with four values, far to near; its seams drawn in its own colour so none shows."""
    xs, ys, zs = scene["xs"], scene["ys"], scene["zs"]
    cells = []
    for row in range(len(ys) - 1):
        for column in range(len(xs) - 1):
            fill = scene["fills"][row][column]
            if fill is None:
                continue
            corners = [(column, row), (column + 1, row), (column + 1, row + 1), (column, row + 1)]
            projected = [project((xs[i], ys[j], zs[j][i])) for i, j in corners]
            depth = round(sum(point[2] for point in projected) / 4, DEPTH_DIGITS)
            cells.append((-depth, len(cells), fill, projected))
    cells.sort(key=lambda cell: (cell[0], cell[1]))
    return [{"kind": "polygon", "points": [place(point) for point in projected], "fill": fill, "edge": fill,
             "edge_width": scene["seam"], "part": "cell"} for _, _, fill, projected in cells]
