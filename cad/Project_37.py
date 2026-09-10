# SurfNDive honeycomb hull — Project 37
# Parametric FreeCAD build: surfboard-shaped hollow shell + honeycomb core.

import math

import FreeCAD as App
import Part

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None


DOC_NAME = "Project_37"

# 6'0" shortboard-ish hull (mm)
LENGTH = 1828.0
WIDTH = 508.0  # ~20"
HEIGHT = 68.0  # ~2.7" foil, not a slab
WALL = 5.0

HEX_RADIUS = 28.0
RIB = 3.0
HEX_X_HALF = 700.0
HEX_Y_HALF = 160.0


def view_fit():
    if Gui is not None and App.GuiUp:
        try:
            Gui.SendMsgToActiveView("ViewFit")
        except Exception:
            pass


def station_size(t):
    """t=0 at tail, t=1 at nose. Returns (half-width, half-thickness, deck_z)."""
    t = min(max(t, 0.0), 1.0)
    # Wide point a bit forward of center; squash tail; pinched round nose
    if t < 0.14:
        w = 0.52 + 0.38 * (t / 0.14) ** 0.75
    elif t > 0.74:
        u = (1.0 - t) / 0.26
        w = max(0.07, 0.92 * (u ** 0.7))
    else:
        w = 0.88 + 0.12 * math.sin(math.pi * (t - 0.14) / 0.60)

    th = 0.38 + 0.62 * (math.sin(math.pi * t) ** 1.15)
    # Mild rocker: nose and tail lift
    z0 = 16.0 * ((t - 0.5) ** 2)
    return (WIDTH / 2.0) * w, (HEIGHT / 2.0) * th, z0


def yz_ellipse_wire(x, ry, rz, z0):
    n = 28
    pts = []
    for i in range(n):
        a = 2.0 * math.pi * i / n
        pts.append(App.Vector(x, ry * math.cos(a), z0 + rz * math.sin(a)))
    pts.append(pts[0])
    return Part.Wire(Part.makePolygon(pts))


def loft_hull(inset=0.0):
    """Loft a surfboard solid. inset shrinks the sections for the inner cavity."""
    stations = 9
    wires = []
    for i in range(stations):
        t = i / float(stations - 1)
        x = -LENGTH / 2.0 + t * LENGTH
        ry, rz, z0 = station_size(t)
        ry = max(8.0, ry - inset)
        rz = max(4.0, rz - inset)
        wires.append(yz_ellipse_wire(x, ry, rz, z0))
    try:
        return Part.makeLoft(wires, True, False, False)
    except Exception:
        return Part.makeLoft(wires, True, True, False)


def make_hex_tube(outer_r, inner_r, height):
    def hex_prism(r, h):
        pts = []
        for i in range(6):
            a = math.radians(60 * i)
            pts.append(App.Vector(r * math.cos(a), r * math.sin(a), 0))
        pts.append(pts[0])
        face = Part.Face(Part.makePolygon(pts))
        return face.extrude(App.Vector(0, 0, h))

    outer = hex_prism(outer_r, height)
    if inner_r <= 0.5:
        return outer
    return outer.cut(hex_prism(inner_r, height))


def colorize(obj, rgb):
    if Gui is not None and App.GuiUp and obj is not None:
        try:
            obj.ViewObject.ShapeColor = rgb
        except Exception:
            pass


if App.ActiveDocument and App.ActiveDocument.Name == DOC_NAME:
    App.closeDocument(DOC_NAME)
doc = App.newDocument(DOC_NAME)

outer = loft_hull(0.0)
inner = loft_hull(WALL)

try:
    hollow_shell = outer.cut(inner)
except Exception as exc:
    App.Console.PrintError("Shell cut failed: %s\n" % exc)
    Part.show(outer, "OuterHull")
    doc.recompute()
    view_fit()
    raise

gap = 2.0
pitch_x = math.sqrt(3.0) * HEX_RADIUS + gap
pitch_y = 1.5 * HEX_RADIUS + gap
cell_h = max(20.0, HEIGHT - 2.0 * WALL)
grid = []

x = -HEX_X_HALF
col = 0
while x <= HEX_X_HALF:
    y = -HEX_Y_HALF
    while y <= HEX_Y_HALF:
        y_pos = y + (pitch_y / 2.0 if (col % 2) else 0.0)
        if abs(y_pos) <= HEX_Y_HALF:
            tube = make_hex_tube(HEX_RADIUS, HEX_RADIUS - RIB, cell_h)
            tube.translate(App.Vector(x, y_pos, -cell_h / 2.0))
            grid.append(tube)
        y += pitch_y
    x += pitch_x
    col += 1

App.Console.PrintMessage("Project 37 honeycomb cells: %d\n" % len(grid))

if not grid:
    Part.show(hollow_shell, "HollowShell")
else:
    honeycomb = Part.makeCompound(grid)
    try:
        core = honeycomb.common(inner)
    except Exception as exc:
        App.Console.PrintWarning("Honeycomb clip failed (%s).\n" % exc)
        core = honeycomb

    try:
        final_board = hollow_shell.fuse(core)
    except Exception as exc:
        App.Console.PrintWarning("Fuse failed (%s); showing parts.\n" % exc)
        colorize(Part.show(hollow_shell, "HollowShell"), (0.55, 0.72, 0.88))
        colorize(Part.show(core, "HoneycombCore"), (0.95, 0.72, 0.15))
        final_board = None

    if final_board is not None:
        cutaway = Part.makeBox(LENGTH + 80.0, WIDTH + 40.0, HEIGHT + 80.0)
        cutaway.translate(App.Vector(-LENGTH / 2.0 - 40.0, 0.0, -HEIGHT / 2.0 - 40.0))
        try:
            visible = final_board.cut(cutaway)
        except Exception as exc:
            App.Console.PrintWarning("Cutaway failed (%s).\n" % exc)
            visible = final_board
        colorize(Part.show(visible, "Project_37_Hull"), (0.55, 0.72, 0.88))

doc.recompute()
view_fit()
App.Console.PrintMessage("Project 37 complete.\n")
