""" restrained, archival line icons for the Su Shi terrain map. """

from math import cos, pi, sin


LANDMARKS = {
    "眉山": ("三苏祠", "pavilion"),
    "成都": ("武侯祠", "gate"),
    "剑门关": ("关楼", "gate"),
    "广元": ("皇泽寺", "pavilion"),
    "汉中": ("古汉台", "terrace"),
    "长安": ("大雁塔", "tower"),
    "洛阳": ("白马寺", "gate"),
    "汴京": ("开封铁塔", "tower"),
    "凤翔": ("东湖喜雨亭", "pavilion"),
    "杭州": ("雷峰塔", "tower"),
    "密州": ("超然台", "terrace"),
    "徐州": ("黄楼", "pavilion"),
    "湖州": ("飞英塔", "tower"),
    "黄州": ("东坡赤壁酹江亭", "pavilion"),
    "汝州": ("风穴寺七祖塔", "tower"),
    "登州": ("蓬莱阁", "pavilion"),
    "颍州": ("文峰塔", "tower"),
    "扬州": ("五亭桥", "bridge"),
    "定州": ("开元寺塔", "tower"),
    "惠州": ("合江楼", "pavilion"),
    "雷州": ("三元塔", "tower"),
    "儋州": ("东坡书院", "academy"),
    "赣州": ("八境台", "terrace"),
    "金陵": ("鸡鸣寺药师塔", "tower"),
    "常州": ("天宁寺塔", "tower"),
}


def _line(draw, project, ink, points):
    draw.line(
        [project(u, v) for u, v in points],
        fill=ink,
        width=1,
        joint="curve",
    )


def _arch_points(cx, spring, radius, bottom, steps=10):
    points = [(cx - radius, bottom), (cx - radius, spring)]
    for i in range(steps + 1):
        angle = pi - pi * i / steps
        points.append(
            (cx + radius * cos(angle), spring - radius * sin(angle))
        )
    points.extend([(cx + radius, spring), (cx + radius, bottom)])
    return points


def _draw_tower(draw, p, ink):
    _line(draw, p, ink, [(0, 0), (0, 4)])
    _line(draw, p, ink, [(-1, 2), (0, 1), (1, 2)])
    roofs = [(5, 4), (10, 6), (15, 8), (20, 10), (25, 12)]
    for index, (eave, half) in enumerate(roofs):
        _line(
            draw,
            p,
            ink,
            [(-half - 1, eave + 2), (-half, eave), (0, eave - 2),
             (half, eave), (half + 1, eave + 2)],
        )
        _line(draw, p, ink, [(-half, eave + 1), (half, eave + 1)])
        wall_half = max(1, half - 2)
        bottom = roofs[index + 1][0] if index + 1 < len(roofs) else 31
        _line(draw, p, ink, [(-wall_half, eave + 2), (-wall_half, bottom)])
        _line(draw, p, ink, [(wall_half, eave + 2), (wall_half, bottom)])
    _line(draw, p, ink, [(-10, 31), (10, 31), (12, 34), (-12, 34), (-10, 31)])
    _line(draw, p, ink, [(-2, 31), (-2, 27), (2, 27), (2, 31)])


def _draw_gate(draw, p, ink):
    _line(draw, p, ink, [(0, 2), (0, 4)])
    _line(
        draw, p, ink,
        [(-14, 10), (-11, 7), (-6, 6), (0, 3), (6, 6),
         (11, 7), (14, 10), (9, 9), (-9, 9), (-14, 10)],
    )
    _line(draw, p, ink, [(-9, 10), (-9, 17), (9, 17), (9, 10)])
    _line(draw, p, ink, [(-5, 11), (-5, 16), (5, 16), (5, 11)])
    _line(draw, p, ink, [(-13, 19), (-9, 16), (9, 16), (13, 19)])
    _line(draw, p, ink, [(-12, 20), (-12, 34), (12, 34), (12, 20), (-12, 20)])
    _line(draw, p, ink, [(-12, 23), (12, 23)])
    _line(draw, p, ink, _arch_points(0, 28, 3, 34))
    _line(draw, p, ink, [(-9, 25), (-9, 32)])
    _line(draw, p, ink, [(9, 25), (9, 32)])


def _draw_pavilion(draw, p, ink):
    _line(draw, p, ink, [(0, 2), (0, 5)])
    _line(
        draw, p, ink,
        [(-14, 12), (-11, 9), (-6, 8), (0, 4), (6, 8),
         (11, 9), (14, 12), (9, 11), (-9, 11), (-14, 12)],
    )
    _line(draw, p, ink, [(-10, 13), (10, 13)])
    for u in (-9, 9):
        _line(draw, p, ink, [(u, 12), (u, 29)])
    _line(draw, p, ink, [(-8, 20), (8, 20)])
    _line(draw, p, ink, [(-8, 24), (8, 24)])
    for u in (-4, 0, 4):
        _line(draw, p, ink, [(u, 20), (u, 24)])
    _line(draw, p, ink, [(-11, 29), (11, 29), (13, 32), (-13, 32), (-11, 29)])
    _line(draw, p, ink, [(-13, 34), (13, 34)])


def _draw_terrace(draw, p, ink):
    _line(draw, p, ink, [(0, 1), (0, 3)])
    _line(
        draw, p, ink,
        [(-11, 9), (-8, 6), (0, 3), (8, 6), (11, 9),
         (7, 8), (-7, 8), (-11, 9)],
    )
    for u in (-7, 7):
        _line(draw, p, ink, [(u, 9), (u, 17)])
    _line(draw, p, ink, [(-10, 15), (10, 15)])
    for u in (-10, -5, 0, 5, 10):
        _line(draw, p, ink, [(u, 15), (u, 19)])
    _line(draw, p, ink, [(-11, 19), (11, 19), (14, 34), (-14, 34), (-11, 19)])
    _line(draw, p, ink, [(-12, 23), (12, 23)])
    _line(draw, p, ink, [(-3, 23), (-5, 34)])
    _line(draw, p, ink, [(3, 23), (5, 34)])
    for v, half in ((26, 3.7), (29, 4.2), (32, 4.7)):
        _line(draw, p, ink, [(-half, v), (half, v)])


def _draw_bridge(draw, p, ink):
    pavilions = [(-11, 10, 2.4), (-5.5, 9, 2.7), (0, 6, 3.3),
                 (5.5, 9, 2.7), (11, 10, 2.4)]
    for cx, roof, half in pavilions:
        _line(
            draw, p, ink,
            [(cx - half - 0.8, roof + 3), (cx, roof),
             (cx + half + 0.8, roof + 3)],
        )
        _line(draw, p, ink, [(cx - half, roof + 3), (cx - half, 21)])
        _line(draw, p, ink, [(cx + half, roof + 3), (cx + half, 21)])
    _line(draw, p, ink, [(-14, 21), (14, 21)])
    _line(draw, p, ink, [(-14, 23), (14, 23)])
    _line(draw, p, ink, [(-14, 20), (-14, 25), (14, 25), (14, 20)])
    for cx in (-9, 0, 9):
        _line(draw, p, ink, _arch_points(cx, 29, 3.2, 34, steps=8))


def _draw_academy(draw, p, ink):
    _line(
        draw, p, ink,
        [(-14, 14), (-9, 10), (0, 5), (9, 10), (14, 14),
         (10, 13), (-10, 13), (-14, 14)],
    )
    _line(draw, p, ink, [(-10, 14), (-10, 29), (10, 29), (10, 14)])
    _line(draw, p, ink, [(-12, 17), (12, 17)])
    _line(draw, p, ink, [(-2, 29), (-2, 20), (2, 20), (2, 29)])
    for cx in (-6, 6):
        _line(draw, p, ink, [(cx - 2, 20), (cx - 2, 25),
                             (cx + 2, 25), (cx + 2, 20), (cx - 2, 20)])
        _line(draw, p, ink, [(cx, 20), (cx, 25)])
    _line(draw, p, ink, [(-12, 29), (12, 29), (13, 31), (-13, 31), (-12, 29)])
    _line(draw, p, ink, [(-4, 31), (-5, 34), (5, 34), (4, 31)])
    _line(draw, p, ink, [(-13, 34), (-5, 34)])
    _line(draw, p, ink, [(5, 34), (13, 34)])


_DRAWERS = {
    "tower": _draw_tower,
    "gate": _draw_gate,
    "pavilion": _draw_pavilion,
    "terrace": _draw_terrace,
    "bridge": _draw_bridge,
    "academy": _draw_academy,
}


def draw_landmark(draw, x, y, name, alpha=200, scale=1.0,
                  color=(185, 155, 94)):
    """Draw a landmark above its terrain anchor; unknown names are ignored."""
    if name not in LANDMARKS or scale <= 0:
        return

    _, kind = LANDMARKS[name]
    ink = (color[0], color[1], color[2], max(0, min(255, int(alpha))))

    def project(u, v):
        return (round(x + u * scale), round(y - (40 - v) * scale))

    _DRAWERS[kind](draw, project, ink)
    draw.line(
        [project(0, 34), (round(x), round(y))],
        fill=ink,
        width=1,
    )
    draw.line(
        [(round(x - 2 * scale), round(y)),
         (round(x + 2 * scale), round(y))],
        fill=ink,
        width=1,
    )
