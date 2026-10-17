"""layout — page layout data for the v2 atmosphere collages (read by src/v2/compose.py).

    !!  PROVISIONAL LAYOUT  !!  Drafted against placeholder images, before the real renders and
    swatches existed.  Every number below is meant to be retuned by eye once
    build/v2/render/view{1,2}.png and build/v2/swatch/*.png are in place.

Page: A3 portrait, 3508 x 4961 px at 300 ppi.  Coordinates are page pixels, x right, y down.
Angles: degrees, POSITIVE = COUNTER-CLOCKWISE on the page (same as the live type twins).
Z-order: within each list, later entries sit on top.

SHEET keys
  title     {'text', 'x', 'y' (cap top of the title), 'size', 'tracking' (1/1000 em)}
  subtitle  {'text', 'dx' ('auto' = under the first word after the number, or px), 'dy' (baseline
             below the title baseline), 'size', 'tracking'}
  view      the main perspective render, placed with a stepped outline:
              'outline'  list of rectangles (x0, y0, x1, y1, torn_sides) whose UNION is the visible
                         image; torn_sides is a string of the sides of THAT rectangle that are torn
                         ('T', 'R', 'B', 'L', any combination, '' = clean cut)
              'frame'    (x0, y0, x1, y1) the render is cover-fitted into (default: outline bbox)
              'focus'    (fx, fy) 0..1 which part of the render stays in frame when cover-fitting
              'zoom'     >= 1 zooms the render inside the frame
              'seed', 'rim' (paper core on the torn sides), 'shadow' (dx, dy, blur, opacity)
  fragments list of material fragments:
              (swatch, crop, target, rot, edge, z, seed[, opts])
                swatch  name of build/v2/swatch/<swatch>.png
                crop    (u0, v0, u1, v1) box in the swatch, 0..1 of its width / height.  It is
                        widened or heightened about its centre to match the target's aspect, so a
                        swatch is never stretched.  None = centred, about 1:1 pixel scale.
                target  (x, y, w, h) page rectangle (rotated by `rot` about its centre), or a
                        quad ((x, y) top-left, top-right, bottom-right, bottom-left) for perspective
                        (rot is then ignored)
                rot     degrees, counter-clockwise
                edge    'torn' (all four sides), 'cut' (clean straight cut), or a string of the
                        torn sides of the unrotated rectangle, e.g. 'LB' = left and bottom torn
                z       'behind' (under the main view) or 'front' (over it)
                seed    any int: changes the tear
                opts    optional dict: 'rim' False (no white paper core), 'tear' amplitude x
                        (default 1.0), 'shadow' (dx, dy, blur, opacity), 'name' (layer name),
                        'tone' {'color', 'blend', 'opacity'} a clipped colour fill to harmonise
  echoes    patches cut from the render itself and laid back over its edge:
              (src_box, scale, (dx, dy), rot, edge, seed[, opts])
                src_box (x0, y0, x1, y1) a PAGE rectangle of the placed view to copy
                scale   ~1.0 .. 1.15 about the patch centre; (dx, dy) offset; rot, edge, seed as above
  notes     handwritten notes: (text, (x, y), rot, target, bend[, opts])
                text    '\\n' breaks lines;  (x, y) = left end of the FIRST baseline
                target  (x, y) the arrow tip, or None for no arrow
                bend    curvature of the arrow, about -0.5 .. 0.5 (sign flips the side)
                opts    'from': where the arrow leaves the text - 'auto', 'below', 'above', 'left',
                        'right', 'below_left', 'below_right', 'above_left', 'above_right', 'end'
                        (after the last line) or an absolute (x, y);
                        'from_offset': (dx, dy) nudge of the arrow start;
                        'c1', 'c2': absolute Bezier control points (override `bend`);
                        'style': 'note' (default) or 'sense' (smaller, softer sensory note);
                        'size', 'color', 'align', 'head' (arrowhead length px), 'gap' (px)
  intensity {'overlap': {'color', 'blend', 'opacity', 'feather'},  front fragments x the view
             'glows': [((cx, cy), radius, color, blend, opacity), ...]}  radial 'chosen area'
  footer    [(text, (x, y) baseline, align), ...]   small italic key line
  sources   one line for the hidden READ ME group
"""

# --------------------------------------------------------------------------------------------- #
# SHEET 1 - LOOKING FROM WITHIN (chosen area -> outside views)            PROVISIONAL
# --------------------------------------------------------------------------------------------- #
SHEET1 = {
    'title': {'text': '1.  LOOKING FROM WITHIN', 'x': 230, 'y': 200, 'size': 96, 'tracking': 140},
    'subtitle': {'text': 'chosen area to outside views', 'dx': 'auto', 'dy': 72, 'size': 40, 'tracking': 300},

    # render -> page: page_x ~ 284 + rx * 1.097, page_y ~ 520 + ry * 1.097 (frame below)
    # key content: olive trunk px 284-480 / py 2500-2890, canopy px 284-1580 / py 520-2890,
    # festoon py 1650-2150, windows py 2350-3530 (glass-block panel px 1120-1520, sheer in the
    # middle bay px 2060-2330, street tree px 2650-3190), table + lamp py 3530-4470 (lamp px ~1600)
    'view': {
        'outline': [
            (490, 640, 3160, 4300, ''),            # body
            (920, 520, 2500, 700, ''),             # raised step, top
            (360, 1250, 540, 3350, 'L'),           # left step, torn (keeps the olive trunk)
            (3100, 1150, 3290, 3900, 'R'),         # right step, torn
            (1040, 4240, 2660, 4470, 'B'),         # bottom step, torn
        ],
        'frame': (360, 520, 3290, 4470),
        'focus': (0.5, 0.5), 'zoom': 1.0,
        'seed': 11, 'rim': True, 'shadow': (12, 16, 30, 0.30),
    },

    'fragments': [
        # swatch             crop (u0, v0, u1, v1)       target (x, y, w, h)       rot   edge    z        seed
        # ---- behind the view
        ('dark_timber',      (0.10, 0.12, 0.80, 0.42),  (1180, 380, 760, 300),     -0.7, 'cut',  'behind', 101),
        ('linen_drape',      (0.10, 0.10, 0.80, 0.62),  (2560, 380, 720, 820),      1.1, 'LB',   'behind', 102),
        ('velvet',           (0.20, 0.30, 0.60, 0.52),  (2080, 4330, 520, 320),    -1.6, 'cut',  'behind', 104),
        ('dark_timber',      (0.55, 0.30, 0.80, 0.70),  (2600, 4260, 300, 440),     1.4, 'cut',  'behind', 105),
        ('fluted_oak',       (0.20, 0.10, 0.60, 0.90),  (3250, 3050, 220, 820),    -0.6, 'cut',  'behind', 106),
        # ---- in front of the view
        ('olive_leaves',     (0.15, 0.20, 0.85, 0.80),  (60, 470, 470, 560),        1.5, 'torn', 'front',  201),
        ('concrete',         (0.20, 0.10, 0.60, 0.45),  (880, 420, 360, 300),      -1.2, 'torn', 'front',  202),
        ('split_face_stone', (0.05, 0.05, 0.50, 0.70),  (40, 1300, 450, 820),       0.6, 'torn', 'front',  203),
        ('travertine',       (0.08, 0.20, 0.45, 0.95),  (50, 3330, 400, 700),      -0.5, 'torn', 'front',  204),
        ('split_face_stone', (0.05, 0.55, 0.95, 0.95),  (60, 3990, 980, 600),      -0.8, 'torn', 'front',  205),
        ('glass_block',      (0.05, 0.15, 0.60, 0.75),  (1090, 4090, 560, 600),     0.9, 'cut',  'front',  206),
        ('brass',            (0.20, 0.20, 0.60, 0.55),  (1720, 4200, 520, 460),    -0.5, 'cut',  'front',  207),
        ('sheer_fabric',     (0.30, 0.05, 0.75, 0.80),  (2980, 820, 470, 1080),    -0.7, 'TB',   'front',  208),
        ('glass_block',      (0.50, 0.10, 0.85, 0.80),  (3150, 2200, 330, 860),     0.4, 'cut',  'front',  209),
        ('travertine',       (0.55, 0.05, 0.85, 0.70),  (3130, 3260, 350, 880),    -1.3, 'torn', 'front',  210),
        ('concrete',         (0.20, 0.10, 0.55, 0.55),  (2340, 4230, 420, 500),     1.1, 'torn', 'front',  211),
    ],

    'echoes': [],

    'notes': [
        # text                    (x, y) baseline   rot    arrow tip       bend   opts
        ('olive\ntree',           (40, 1120),        2.0,  (820, 1500),   -0.30, {'from': 'right', 'size': 76}),
        ('texture\n+ shadow',     (30, 2230),        2.5,  (1050, 2700),   0.25, {'from': 'right', 'size': 74}),
        ('filtered light',        (2040, 470),      -1.5,  (1820, 1000),   0.25, {'from': 'below'}),
        ('soft fabric',           (2980, 330),       2.0,  (3180, 860),    0.35, {'from': 'below'}),
        ('glass\nblocks',         (3215, 1990),     -3.0,  (3290, 2310),  -0.35, {'from': 'below', 'size': 76}),
        ('split face stone',      (330, 4720),       0.5,  (230, 4480),    0.40, {'from': 'left'}),
        ('warm + intimate',       (1330, 4800),     -1.0,  (1900, 4560),  -0.30, {'from': 'above_right'}),
        ('concrete',              (2830, 4820),      1.5,  (2700, 4660),   0.25, {'from': 'left'}),
        # sensory notes (softer, no arrow)
        ('leaves\nrustle\nabove', (40, 2520),        2.0,  None,           0.0,  {'style': 'sense'}),
        ('fresh bread + olive oil', (1350, 4890),   -1.0,  None,           0.0,  {'style': 'sense'}),
        ('street hum,\nmuffled',  (3060, 4330),     -2.0,  None,           0.0,  {'style': 'sense'}),
    ],

    'intensity': {
        'overlap': {'color': '#C27A3E', 'blend': 'soft light', 'opacity': 0.42, 'feather': 60},
        'glows': [
            ((1300, 3000), 1300, '#B8643A', 'soft light', 0.30),   # the chosen area: tree + table
        ],
    },

    'footer': [
        ('restaurant  —  atmosphere collage 1 of 2', (230, 4868), 'left'),
        ('sound · smell · taste · texture · colour', (3278, 4868), 'right'),
    ],
    'sources': 'Main view: build/v2/render/view1.png (Blender render of the client design). Material swatches: build/v2/swatch/*.png.',
}


# --------------------------------------------------------------------------------------------- #
# SHEET 2 - LOOKING TOWARDS (chosen area from a distance)                  PROVISIONAL
# --------------------------------------------------------------------------------------------- #
SHEET2 = {
    'title': {'text': '2.  LOOKING TOWARDS', 'x': 230, 'y': 200, 'size': 96, 'tracking': 140},
    'subtitle': {'text': 'chosen area from a distance', 'dx': 'auto', 'dy': 72, 'size': 40, 'tracking': 300},

    # render -> page: page_x ~ 344 + rx * 1.097, page_y ~ 520 + ry * 1.097 (frame below)
    # key content: void rail py 520-1150; swag ceiling py 1110-2490; cabins px 1000-2190 /
    # py 2560-3250; glass-block screen px 2150-2910 / py 2380-3730; olive trunk px 2880-3300;
    # chairs px 344-1600 / py 3090-3680; our table px 720-2140 / py 3760-4470
    'view': {
        'outline': [
            (500, 660, 3140, 4300, ''),            # body
            (820, 520, 2420, 700, ''),             # raised step, top
            (360, 1300, 540, 3500, 'L'),           # left step, torn
            (3080, 1500, 3290, 3900, ''),          # right step
            (880, 4240, 2500, 4470, 'B'),          # bottom step, torn
        ],
        'frame': (360, 520, 3290, 4470),
        'focus': (0.5, 0.5), 'zoom': 1.0,
        'seed': 12, 'rim': True, 'shadow': (12, 16, 30, 0.30),
    },

    'fragments': [
        # ---- behind
        ('linen_drape',      (0.05, 0.05, 0.95, 0.45),  (980, 380, 1400, 380),     -0.6, 'B',    'behind', 401),
        ('dark_timber',      (0.20, 0.05, 0.60, 0.40),  (2380, 600, 300, 520),      0.8, 'cut',  'behind', 402),
        ('dark_timber',      (0.55, 0.10, 0.85, 0.95),  (70, 1700, 300, 1250),      0.3, 'cut',  'behind', 403),
        ('velvet',           (0.10, 0.20, 0.55, 0.50),  (1440, 4300, 560, 380),    -1.2, 'cut',  'behind', 404),
        # ---- in front
        ('sheer_fabric',     (0.10, 0.20, 0.50, 0.80),  (40, 640, 430, 760),       -0.8, 'torn', 'front',  501),
        ('concrete',         (0.05, 0.05, 0.75, 0.55),  (2500, 290, 900, 640),      1.3, 'torn', 'front',  502),
        ('white_brick',      (0.30, 0.05, 0.75, 0.95),  (3140, 1140, 340, 1180),   -0.5, 'L',    'front',  503),
        ('glass_block',      (0.20, 0.10, 0.60, 0.80),  (3170, 2720, 300, 620),     0.6, 'cut',  'front',  510),
        ('travertine',       (0.15, 0.15, 0.55, 0.85),  (50, 2330, 420, 1000),     -1.0, 'torn', 'front',  504),
        ('breccia_marble',   (0.10, 0.20, 0.70, 0.95),  (2900, 3560, 560, 1080),   -1.1, 'torn', 'front',  505),
        ('split_face_stone', (0.05, 0.30, 0.80, 0.70),  (50, 3980, 700, 520),       0.7, 'torn', 'front',  506),
        ('fluted_oak',       (0.10, 0.10, 0.60, 0.70),  (1090, 4150, 380, 430),    -0.9, 'cut',  'front',  507),
        ('brass',            (0.10, 0.30, 0.55, 0.65),  (2350, 4230, 460, 420),     0.9, 'cut',  'front',  508),
        ('dark_timber',      (0.05, 0.05, 0.30, 0.90),  (2000, 4170, 280, 470),    -1.8, 'cut',  'front',  509),
    ],

    'echoes': [],

    'notes': [
        ('layered ceiling elements', (1230, 455),   -1.0,  (1500, 1550),   0.25, {'from': 'below'}),
        ('concrete',              (2240, 230),       1.5,  (2620, 480),   -0.35, {'from': 'right'}),
        ('warm\nlighting',        (40, 1560),        2.5,  (1180, 2760),  -0.30, {'from': 'right', 'size': 76}),
        ('white\nbrick\nwall',    (3290, 2420),     -2.5,  (3330, 2300),   0.35, {'from': 'above', 'gap': 14,
                                                                                    'size': 72}),
        ('glass\nblocks',         (3265, 3440),     -2.0,  (3320, 3330),  -0.35, {'from': 'above', 'gap': 14, 'size': 70}),
        ('movement through space', (200, 4690),      1.0,  (880, 3820),   -0.30, {'from': 'above'}),
        ('tactile materials',     (1430, 4740),     -0.8,  (1720, 4560),  -0.25, {'from': 'above_right'}),
        ('unique stone',          (2640, 4790),      1.2,  (3020, 4600),   0.30, {'from': 'right'}),
        # sensory
        ('low murmur, soft acoustics', (200, 4810),  1.0,  None,           0.0,  {'style': 'sense'}),
        ('red wine + candle wax', (1430, 4840),     -0.8,  None,           0.0,  {'style': 'sense'}),
    ],

    'intensity': {
        'overlap': {'color': '#C27A3E', 'blend': 'soft light', 'opacity': 0.42, 'feather': 60},
        'glows': [
            ((1600, 2900), 1050, '#B8643A', 'soft light', 0.32),   # the chosen area: the cabins
        ],
    },

    'footer': [
        ('restaurant  —  atmosphere collage 2 of 2', (230, 4868), 'left'),
        ('sound · smell · taste · texture · colour', (3278, 4868), 'right'),
    ],
    'sources': 'Main view: build/v2/render/view2.png (Blender render of the client design). Material swatches: build/v2/swatch/*.png.',
}

SHEETS = {1: SHEET1, 2: SHEET2}
