import math
import random
import time
import tkinter as tk

TAU = math.pi * 2.0
PHI = (1.0 + math.sqrt(5.0)) / 2.0


def dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross3(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def norm3(a):
    l = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    return (a[0] / l, a[1] / l, a[2] / l)


def sub3(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def min_distance_edges(verts, tol=1e-3):
    pairs = [(math.dist(verts[i], verts[j]), i, j)
             for i in range(len(verts))
             for j in range(i + 1, len(verts))]
    dmin = min(d for d, _, _ in pairs)
    return [(i, j) for d, i, j in pairs if d <= dmin + tol]


def extract_faces(verts, edges):
    nbrs = [[] for _ in verts]
    for a, b in edges:
        nbrs[a].append(b)
        nbrs[b].append(a)
    order = []
    for v in range(len(verts)):
        x, y, z = verts[v]
        ln = math.sqrt(x * x + y * y + z * z)
        t = (x / ln, y / ln, z / ln)
        r = None
        for nb in nbrs[v]:
            d = sub3(verts[nb], verts[v])
            dp = dot3(d, t)
            p = sub3(d, (dp * t[0], dp * t[1], dp * t[2]))
            lp = math.sqrt(dot3(p, p))
            if lp > 1e-9:
                r = (p[0] / lp, p[1] / lp, p[2] / lp)
                break
        if r is None:
            r = (1.0, 0.0, 0.0)
        angs = []
        for nb in nbrs[v]:
            d = sub3(verts[nb], verts[v])
            dp = dot3(d, t)
            p = sub3(d, (dp * t[0], dp * t[1], dp * t[2]))
            angs.append((math.atan2(dot3(cross3(r, p), t), dot3(r, p)), nb))
        angs.sort()
        order.append([nb for _, nb in angs])
    used = set()
    raw = []
    for a0 in range(len(verts)):
        for b0 in order[a0]:
            if (a0, b0) in used:
                continue
            face = [a0, b0]
            a, b = a0, b0
            ok = False
            for _ in range(len(verts) + 4):
                used.add((a, b))
                lst = order[b]
                c = lst[(lst.index(a) - 1) % len(lst)]
                if c == a0:
                    used.add((b, c))
                    ok = True
                    break
                face.append(c)
                a, b = b, c
            if ok and len(face) >= 3:
                raw.append(face)
    seen = set()
    faces = []
    for f in raw:
        key = frozenset(f)
        if key in seen:
            continue
        seen.add(key)
        faces.append(f)
    return faces


def orient_faces(verts, faces, two_sided):
    incident = {}
    for fi, f in enumerate(faces):
        n = len(f)
        for k in range(n):
            a, b = f[k], f[(k + 1) % n]
            key = (a, b) if a < b else (b, a)
            incident.setdefault(key, []).append((fi, a, b))
    flipped = [False] * len(faces)
    visited = [False] * len(faces)
    for start in range(len(faces)):
        if visited[start]:
            continue
        visited[start] = True
        stack = [start]
        while stack:
            fi = stack.pop()
            f = faces[fi]
            n = len(f)
            for k in range(n):
                a, b = f[k], f[(k + 1) % n]
                if flipped[fi]:
                    a, b = b, a
                key = (a, b) if a < b else (b, a)
                for fj, c, d in incident.get(key, ()):
                    if fj == fi or visited[fj]:
                        continue
                    if c == a and d == b:
                        faces[fj] = faces[fj][::-1]
                        flipped[fj] = True
                    visited[fj] = True
                    stack.append(fj)
    if two_sided:
        return
    vol = 0.0
    for f in faces:
        x0, y0, z0 = verts[f[0]]
        for k in range(1, len(f) - 1):
            ax, ay, az = verts[f[k]]
            bx, by, bz = verts[f[k + 1]]
            vol += (x0 * (ay * bz - az * by)
                    + y0 * (az * bx - ax * bz)
                    + z0 * (ax * by - ay * bx))
    if vol < 0.0:
        for i in range(len(faces)):
            faces[i] = faces[i][::-1]


class Shape:
    __slots__ = ("name", "verts", "faces", "edges", "rgb", "two_sided",
                 "ghost_fill", "chrome_sky", "chrome_ground", "dots")

    def __init__(self, name, verts, faces, edges, rgb, two_sided):
        self.name = name
        self.verts = verts
        self.faces = faces
        self.edges = edges
        self.rgb = rgb
        self.two_sided = two_sided
        self.ghost_fill = "#%02x%02x%02x" % tuple(int(c * 0.07) for c in rgb)
        self.chrome_sky = tuple(int(c * 0.5 + 127) for c in rgb)
        self.chrome_ground = tuple(int(c * 0.18) for c in rgb)
        self.dots = len(verts) <= 42


def finish(name, verts, faces, rgb, two_sided=False):
    r = max(math.sqrt(x * x + y * y + z * z) for x, y, z in verts)
    verts = [(x / r, y / r, z / r) for x, y, z in verts]
    orient_faces(verts, faces, two_sided)
    es = set()
    for f in faces:
        n = len(f)
        for k in range(n):
            a, b = f[k], f[(k + 1) % n]
            es.add((a, b) if a < b else (b, a))
    return Shape(name, verts, faces, sorted(es), rgb, two_sided)


def cube():
    vs = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    es = min_distance_edges(vs)
    return finish("Cube", vs, extract_faces(vs, es), (86, 210, 255))


def tetrahedron():
    vs = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
    es = min_distance_edges(vs)
    return finish("Tetrahedron", vs, extract_faces(vs, es), (255, 176, 82))


def octahedron():
    vs = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    es = min_distance_edges(vs)
    return finish("Octahedron", vs, extract_faces(vs, es), (120, 255, 150))


def icosahedron():
    vs = []
    for a in (-1, 1):
        for b in (-PHI, PHI):
            vs.append((0, a, b))
            vs.append((a, b, 0))
            vs.append((b, 0, a))
    es = min_distance_edges(vs)
    return finish("Icosahedron", vs, extract_faces(vs, es), (255, 120, 220))


def dodecahedron():
    vs = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
    a, b = PHI ** -1, PHI
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            vs.append((0, s1 * a, s2 * b))
            vs.append((s2 * b, 0, s1 * a))
            vs.append((s1 * a, s2 * b, 0))
    es = min_distance_edges(vs)
    return finish("Dodecahedron", vs, extract_faces(vs, es), (255, 232, 100))


def sphere(bands=10, seg=16):
    vs, fs = [], []
    for i in range(bands):
        lat = math.pi * (i + 1) / (bands + 1)
        for j in range(seg):
            lon = TAU * j / seg
            vs.append((math.sin(lat) * math.cos(lon), math.cos(lat),
                       math.sin(lat) * math.sin(lon)))
    vs.append((0.0, 1.0, 0.0))
    vs.append((0.0, -1.0, 0.0))
    top, bot = len(vs) - 2, len(vs) - 1
    for i in range(bands):
        for j in range(seg):
            v0 = i * seg + j
            v1 = i * seg + (j + 1) % seg
            if i == 0:
                fs.append([top, v0, v1])
            else:
                fs.append([v0 - seg, v0, v1, v1 - seg])
            if i == bands - 1:
                fs.append([bot, v1, v0])
    return finish("Sphere", vs, fs, (150, 175, 255))


def torus(major=26, minor=12):
    vs, fs = [], []
    R, r = 0.72, 0.36
    for i in range(major):
        u = TAU * i / major
        cu, su = math.cos(u), math.sin(u)
        for j in range(minor):
            v = TAU * j / minor
            w = R + r * math.cos(v)
            vs.append((w * cu, r * math.sin(v), w * su))
    for i in range(major):
        for j in range(minor):
            a = i * minor + j
            b = i * minor + (j + 1) % minor
            c = ((i + 1) % major) * minor + (j + 1) % minor
            d = ((i + 1) % major) * minor + j
            fs.append([a, b, c, d])
    return finish("Torus", vs, fs, (255, 105, 105))


def tube(name, curve, segs, tube_r, tube_n, rgb, closed, caps):
    vs, rings = [], []
    eps = 1e-4
    for i in range(segs):
        t = i / segs
        c = curve(t)
        t2 = t + eps if closed else min(t + eps, 1.0)
        t0 = t - eps if closed else max(t - eps, 0.0)
        tan = norm3(sub3(curve(t2), curve(t0)))
        n1 = cross3(tan, (0.0, 1.0, 0.0))
        ln = math.sqrt(dot3(n1, n1))
        if ln < 1e-6:
            n1 = (1.0, 0.0, 0.0)
        else:
            n1 = (n1[0] / ln, n1[1] / ln, n1[2] / ln)
        n2 = cross3(tan, n1)
        ring = []
        for j in range(tube_n):
            th = TAU * j / tube_n
            co, si = math.cos(th), math.sin(th)
            ox = tube_r * (co * n1[0] + si * n2[0])
            oy = tube_r * (co * n1[1] + si * n2[1])
            oz = tube_r * (co * n1[2] + si * n2[2])
            vs.append((c[0] + ox, c[1] + oy, c[2] + oz))
            ring.append(len(vs) - 1)
        rings.append(ring)
    fs = []
    for i in range(segs if closed else segs - 1):
        r0 = rings[i]
        r1 = rings[(i + 1) % segs]
        for j in range(tube_n):
            j2 = (j + 1) % tube_n
            fs.append([r0[j], r0[j2], r1[j2], r1[j]])
    if caps:
        for ring, t in ((rings[0], 0.0), (rings[-1], 1.0)):
            ci = len(vs)
            vs.append(curve(t))
            for j in range(tube_n):
                fs.append([ci, ring[j], ring[(j + 1) % tube_n]])
    return finish(name, vs, fs, rgb)


def torus_knot(p=2, q=3, segs=72, tube_n=6):
    R, r, tr = 0.72, 0.34, 0.21

    def curve(t):
        u = TAU * t
        a, b = p * u, q * u
        w = R + r * math.cos(b)
        return (w * math.cos(a), r * math.sin(b), w * math.sin(a))

    return tube("Torus Knot", curve, segs, tr, tube_n, (180, 140, 255),
                closed=True, caps=False)


def spring(segs=64, tube_n=6):
    R, tr, turns = 0.42, 0.15, 3

    def curve(t):
        ang = TAU * turns * t
        return (R * math.cos(ang), -1 + 2 * t, R * math.sin(ang))

    return tube("Spring", curve, segs, tr, tube_n, (240, 255, 120),
                closed=False, caps=True)


def mobius(cols=72):
    R, w = 0.72, 0.42
    vs = []
    for k in range(cols):
        t = TAU * k / cols
        ct, st = math.cos(t), math.sin(t)
        ht = t / 2.0
        for s in (-w, w):
            rad = R + s * math.cos(ht)
            vs.append((rad * ct, s * math.sin(ht), rad * st))
    fs = []
    for k in range(cols):
        k2 = (k + 1) % cols
        a = 2 * k
        b = 2 * k + 1
        c = 2 * k2 + 1
        d = 2 * k2
        if k == cols - 1:
            c, d = 0, 1
        fs.append([a, b, c, d])
    return finish("Möbius", vs, fs, (95, 240, 225), two_sided=True)


SHAPES = [cube, tetrahedron, octahedron, icosahedron, dodecahedron,
          sphere, torus, torus_knot, mobius, spring]

MODES = ("Wire", "Solid", "Chrome", "Toon", "Ghost")

HELP_TEXT = ("← / →   switch shape\n"
             "1-5 / M   shader style\n"
             "space     pause\n"
             "A         auto-cycle shapes\n"
             "+ / −     spin speed\n"
             "wheel     zoom\n"
             "drag      rotate (with inertia)\n"
             "R         reset view\n"
             "F         fullscreen\n"
             "H         close help\n"
             "Esc       quit")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("3D Shader Styles - Tkinter")
        self.geometry("960x640")
        self.configure(bg="#05050c")
        self.fs = False
        self.canvas = tk.Canvas(self, bg="#05050c", bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        bar = tk.Frame(self, bg="#10101a")
        bar.pack(fill="x")

        def make_cmd(fn):
            def cmd():
                fn()
                self.canvas.focus_set()
            return cmd

        def btn(txt, fn):
            b = tk.Button(bar, text=txt, command=make_cmd(fn),
                          bg="#1d2030", fg="#dfe3f0", activebackground="#33355c",
                          activeforeground="#ffffff", relief="flat", bd=0,
                          padx=10, pady=3, font=("Segoe UI", 9), cursor="hand2")
            b.pack(side="left", padx=3, pady=5)
            return b

        btn("< Prev", lambda: self.switch(-1))
        btn("Next >", lambda: self.switch(1))
        self.pause_btn = btn("Pause", self.toggle_pause)
        self.mode_btn = btn("Style: Solid", self.cycle_mode)
        self.auto_btn = btn("Auto: Off", self.toggle_auto)
        btn("Reset", self.reset_view)
        btn("Speed -", lambda: self.change_speed(1 / 1.3))
        btn("Speed +", lambda: self.change_speed(1.3))
        self.status = tk.Label(bar, bg="#10101a", fg="#8b92a8", justify="right",
                               font=("Segoe UI", 9))
        self.status.pack(side="right", padx=10)

        self.shapes = [f() for f in SHAPES]
        self.idx = 0
        self.mode = 0
        self.ax = 0.5
        self.ay = 0.8
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.speed = 1.0
        self.zoom = 1.0
        self.paused = False
        self.auto = False
        self.trans_t = 1.0
        self.last_switch = time.perf_counter()
        self.dragging = False
        self.drag_prev = (0, 0)
        self.drag_time = 0.0
        self.bob_t = 0.0
        self.win_w = 0
        self.win_h = 0
        self.fps = 60.0
        self.last_frame = time.perf_counter()
        self.bake_job = None
        self.show_help = False

        self.bind("<Left>", lambda e: self.switch(-1))
        self.bind("<Right>", lambda e: self.switch(1))
        self.bind("<space>", lambda e: self.toggle_pause())
        self.bind("<m>", lambda e: self.cycle_mode())
        self.bind("<a>", lambda e: self.toggle_auto())
        self.bind("<r>", lambda e: self.reset_view())
        self.bind("<f>", lambda e: self.toggle_fullscreen())
        self.bind("<h>", lambda e: self.toggle_help())
        self.bind("<plus>", lambda e: self.change_speed(1.3))
        self.bind("<equal>", lambda e: self.change_speed(1.3))
        self.bind("<minus>", lambda e: self.change_speed(1 / 1.3))
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Configure>", self.on_resize)

        self.after(120, self.bake_bg)
        self.update_status()
        self.animate()

    def bake_bg(self):
        self.bake_job = None
        c = self.canvas
        w, h = self.win_w, self.win_h
        if w < 40 or h < 40:
            return
        c.delete("bg")
        bands = 44
        top = (21, 22, 44)
        bot = (6, 6, 14)
        for i in range(bands):
            y0 = h * i // bands
            y1 = h * (i + 1) // bands
            t = i / (bands - 1)
            col = "#%02x%02x%02x" % tuple(int(top[k] + (bot[k] - top[k]) * t)
                                          for k in range(3))
            c.create_rectangle(0, y0, w, y1, fill=col, outline=col, tags="bg")
        rng = random.Random(7)
        for _ in range(150):
            x = rng.randrange(w)
            y = rng.randrange(int(h * 0.85))
            s = rng.uniform(0.5, 1.7)
            g = rng.randrange(45, 110)
            c.create_oval(x, y, x + s, y + s,
                          fill="#%02x%02x%02x" % (g, g, min(255, g + 25)),
                          outline="", tags="bg")
        base = min(w, h)
        sx, sy = w * 0.5, h * 0.48 + base * 0.46
        for f in (1.0, 0.72, 0.45):
            rx, ry = base * 0.26 * f, base * 0.055 * f
            c.create_oval(sx - rx, sy - ry, sx + rx, sy + ry, fill="#000000",
                          outline="", stipple="gray12", tags="bg")

    def update_status(self):
        s = self.shapes[self.idx]
        self.status.config(
            text=f"{s.name}  ·  {len(s.verts)} verts / {len(s.faces)} faces  ·  "
                 f"x{self.speed:.2f}  ·  {MODES[self.mode]}\n"
                 "←→ shape · 1-5/M style · space pause · A auto · R reset · "
                 "F full · H help · wheel zoom · drag rotate")
        self.mode_btn.config(text=f"Style: {MODES[self.mode]}")
        self.auto_btn.config(text=f"Auto: {'On' if self.auto else 'Off'}")

    def switch(self, d):
        self.idx = (self.idx + d) % len(self.shapes)
        self.trans_t = 0.0
        self.last_switch = time.perf_counter()
        self.update_status()

    def toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.config(text="Play" if self.paused else "Pause")

    def cycle_mode(self):
        self.mode = (self.mode + 1) % len(MODES)
        self.update_status()

    def toggle_auto(self):
        self.auto = not self.auto
        self.last_switch = time.perf_counter()
        self.update_status()

    def reset_view(self):
        self.ax = 0.5
        self.ay = 0.8
        self.vel_x = self.vel_y = 0.0
        self.zoom = 1.0
        self.speed = 1.0
        self.update_status()

    def toggle_fullscreen(self):
        self.fs = not self.fs
        self.attributes("-fullscreen", self.fs)

    def toggle_help(self):
        self.show_help = not self.show_help

    def change_speed(self, factor):
        self.speed = min(4.0, max(0.25, self.speed * factor))
        self.update_status()

    def on_wheel(self, e):
        self.zoom = max(0.35, min(2.8, self.zoom * (1.12 if e.delta > 0 else 1 / 1.12)))

    def on_press(self, e):
        self.dragging = True
        self.drag_prev = (e.x, e.y)
        self.drag_time = time.perf_counter()
        self.vel_x = self.vel_y = 0.0

    def on_drag(self, e):
        now = time.perf_counter()
        dt = max(now - self.drag_time, 1 / 240)
        self.drag_time = now
        dx = e.x - self.drag_prev[0]
        dy = e.y - self.drag_prev[1]
        self.drag_prev = (e.x, e.y)
        self.ay += dx * 0.005
        self.ax += dy * 0.005
        self.vel_y = 0.75 * self.vel_y + 0.25 * (dx * 0.005 / dt)
        self.vel_x = 0.75 * self.vel_x + 0.25 * (dy * 0.005 / dt)

    def on_release(self, e):
        self.dragging = False

    def on_resize(self, e):
        self.win_w = e.width
        self.win_h = e.height
        if self.bake_job is not None:
            self.after_cancel(self.bake_job)
        self.bake_job = self.after(180, self.bake_bg)

    def shade(self, rgb, t):
        if t < 0.0:
            t = 0.0
        elif t > 1.0:
            t = 1.0
        k = 0.16 + 0.84 * t
        return "#%02x%02x%02x" % (int(rgb[0] * k), int(rgb[1] * k), int(rgb[2] * k))

    def render_frame(self):
        c = self.canvas
        w, h = self.win_w, self.win_h
        if w < 40 or h < 40:
            return
        shape = self.shapes[self.idx]
        u = self.trans_t - 1.0
        ts = 1.0 + 2.70158 * u * u * u + 1.70158 * u * u
        bob = 0.05 * math.sin(self.bob_t * 1.4)
        cx = w * 0.5
        cy = h * 0.48
        scale = min(w, h) * 0.33 * self.zoom * ts
        dist = 3.4
        cax, sax = math.cos(self.ax), math.sin(self.ax)
        cay, say = math.cos(self.ay), math.sin(self.ay)
        pts3 = []
        pts2 = []
        ap3 = pts3.append
        ap2 = pts2.append
        for x, y, z in shape.verts:
            x, z = x * cay - z * say, x * say + z * cay
            y, z = y * cax - z * sax, y * sax + z * cax
            y += bob
            ap3((x, y, z))
            f = dist / (dist - z)
            ap2((cx + x * f * scale, cy - y * f * scale))
        mode = MODES[self.mode]
        la = self.bob_t * 0.45
        l1x, l1y, l1z = norm3((0.84 * math.cos(la), 0.55, 0.84 * math.sin(la)))
        l2x, l2y, l2z = norm3((-0.5, -0.35, 0.78))
        h1x, h1y, h1z = norm3((l1x, l1y, l1z + 1.0))
        h2x, h2y, h2z = norm3((l2x, l2y, l2z + 1.0))
        rgb = shape.rgb
        br, bgc, bc = rgb
        if mode == "Wire":
            c.delete("frame")
            for a, b in shape.edges:
                za, zb = pts3[a][2], pts3[b][2]
                tt = ((za + zb) * 0.5 + 1.0) * 0.5
                pa, pb = pts2[a], pts2[b]
                c.create_line(pa[0], pa[1], pb[0], pb[1], fill=self.shade(rgb, tt),
                              width=1 + (tt > 0.55), tags="frame")
            if shape.dots:
                for x, y, z in pts3:
                    r = 1.7 + z * 1.2
                    c.create_oval(x - r, y - r, x + r, y + r,
                                  fill=self.shade(rgb, (z + 1) * 0.5), outline="",
                                  tags="frame")
        else:
            two = shape.two_sided
            ghost_fill = shape.ghost_fill
            sky = shape.chrome_sky
            ground = shape.chrome_ground
            items = []
            aitems = items.append
            for f in shape.faces:
                A = pts3[f[0]]
                B = pts3[f[1]]
                C = pts3[f[2]]
                ux = B[0] - A[0]
                uy = B[1] - A[1]
                uz = B[2] - A[2]
                vx = C[0] - A[0]
                vy = C[1] - A[1]
                vz = C[2] - A[2]
                nx = uy * vz - uz * vy
                ny = uz * vx - ux * vz
                nz = ux * vy - uy * vx
                if two:
                    if nz < 0.0:
                        nx = -nx
                        ny = -ny
                        nz = -nz
                elif nz <= 0.0:
                    continue
                inv = 1.0 / math.sqrt(nx * nx + ny * ny + nz * nz)
                n1 = nx * inv
                n2 = ny * inv
                n3 = nz * inv
                d1 = n1 * l1x + n2 * l1y + n3 * l1z
                if d1 > 0.0:
                    d1 = d1 * d1
                else:
                    d1 = 0.0
                d2 = n1 * l2x + n2 * l2y + n3 * l2z
                if d2 < 0.0:
                    d2 = 0.0
                s1 = n1 * h1x + n2 * h1y + n3 * h1z
                if s1 > 0.0:
                    s2 = s1 * s1
                    s4 = s2 * s2
                    s8 = s4 * s4
                    s16 = s8 * s8
                    s1 = s16 * s16
                else:
                    s1 = 0.0
                s2h = n1 * h2x + n2 * h2y + n3 * h2z
                if s2h > 0.0:
                    s2h = s2h * s2h
                    s2h = s2h * s2h * s2h
                else:
                    s2h = 0.0
                rim = 1.0 - n3
                rim = rim * rim * rim
                spec = 140.0 * s1 + 46.0 * s2h
                if len(f) == 4:
                    depth = A[2] + B[2] + C[2] + pts3[f[3]][2]
                    coords = pts2[f[0]] + pts2[f[1]] + pts2[f[2]] + pts2[f[3]]
                elif len(f) == 3:
                    depth = A[2] + B[2] + C[2]
                    coords = pts2[f[0]] + pts2[f[1]] + pts2[f[2]]
                else:
                    depth = 0.0
                    coords = ()
                    for i in f:
                        depth += pts3[i][2]
                        coords = coords + pts2[i]
                if mode == "Chrome":
                    tt = (n2 + 1.0) * 0.5
                    kk = 0.3 + 0.7 * d1
                    cr = (ground[0] + (sky[0] - ground[0]) * tt) * kk + spec + 200.0 * rim
                    cg = (ground[1] + (sky[1] - ground[1]) * tt) * kk + spec + 200.0 * rim
                    cb = (ground[2] + (sky[2] - ground[2]) * tt) * kk + spec + 200.0 * rim
                elif mode == "Toon":
                    kk = 0.22 + 0.78 * (int(min(d1, 0.999) * 4.0) * 0.25)
                    cr, cg, cb = br * kk, bgc * kk, bc * kk
                else:
                    kk = 0.20 + 0.78 * d1 + 0.34 * d2
                    cr = br * kk + spec + br * 0.25 * rim
                    cg = bgc * kk + spec + bgc * 0.25 * rim
                    cb = bc * kk + spec + bc * 0.25 * rim
                if mode == "Toon":
                    fill = "#%02x%02x%02x" % (int(cr), int(cg), int(cb))
                    outline = "#%02x%02x%02x" % (int(br * 0.2), int(bgc * 0.2), int(bc * 0.2))
                elif mode == "Ghost":
                    fill = ghost_fill
                    outline = self.shade(rgb, (depth / len(f) + 1.0) * 0.5)
                else:
                    fill = "#%02x%02x%02x" % (int(cr if cr < 255.0 else 255.0),
                                              int(cg if cg < 255.0 else 255.0),
                                              int(cb if cb < 255.0 else 255.0))
                    outline = "#%02x%02x%02x" % (int(cr * 0.45), int(cg * 0.45), int(cb * 0.45))
                aitems((depth, fill, outline, coords))
            items.sort(key=lambda it: it[0])
            c.delete("frame")
            for depth, fill, outline, coords in items:
                c.create_polygon(*coords, fill=fill, outline=outline, tags="frame")
        name = shape.name
        c.create_text(12, 10, anchor="nw", fill="#9aa3b8", tags="frame",
                      text=f"{name}  ·  {mode}", font=("Segoe UI", 12, "bold"))
        c.create_text(w - 12, 10, anchor="ne", fill="#6b7288", tags="frame",
                      text=f"{self.fps:.0f} fps", font=("Segoe UI", 10))
        if self.show_help:
            c.create_rectangle(w / 2 - 175, h / 2 - 135, w / 2 + 175, h / 2 + 145,
                               fill="#0b0b14", outline="#33355c", tags="frame")
            c.create_text(w / 2, h / 2 + 5, text=HELP_TEXT, fill="#c8cede",
                          justify="center", font=("Segoe UI", 10), tags="frame")

    def animate(self):
        now = time.perf_counter()
        dt = now - self.last_frame
        self.last_frame = now
        if dt > 0.1:
            dt = 0.1
        if dt > 0:
            self.fps = 0.9 * self.fps + 0.1 / dt
        if not self.paused:
            self.ay += 0.55 * self.speed * dt
            self.ax += 0.13 * self.speed * dt
            if not self.dragging:
                self.ay += self.vel_y * dt
                self.ax += self.vel_x * dt
                damp = math.exp(-4.2 * dt)
                self.vel_y *= damp
                self.vel_x *= damp
                if abs(self.vel_x) < 0.002 and abs(self.vel_y) < 0.002:
                    self.vel_x = self.vel_y = 0.0
            self.bob_t += dt
        if self.auto and not self.paused and now - self.last_switch > 8.0:
            self.switch(1)
        if self.trans_t < 1.0:
            self.trans_t = min(1.0, self.trans_t + dt / 0.5)
        self.render_frame()
        self.after(14, self.animate)


if __name__ == "__main__":
    App().mainloop()
