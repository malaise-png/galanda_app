# theme.py
#
# All the "look and feel" numbers for the app live in this one file on purpose.
# The final visual design is NOT locked in yet, so instead of scattering colors,
# sizes and fonts across every widget file, everything tweakable is collected
# here. If you want to change a color, a size, or a font later, this is almost
# always the only file you need to open.
#
# Colors in Kivy are RGBA tuples with each value between 0.0 and 1.0 (not 0-255).

import os

# Every path in this file is resolved relative to this file's own location
# (not the process's current working directory), so the app finds its
# fonts/assets/exports correctly no matter how or from where it's launched
# -- e.g. a systemd service or a desktop autostart entry on the kiosk,
# which won't necessarily have BASE_DIR as their working directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Dev vs. deployment
# ---------------------------------------------------------------------------

# True  -> runs in a normal window, with a mouse-based "second finger"
#          simulator turned on, so you can test on a laptop.
# False -> runs truly fullscreen/borderless with no window chrome, and the
#          mouse multitouch simulator is turned off (not needed on a real
#          touchscreen, and we don't want a stray Ctrl-click to add a fake
#          second touch point on the real kiosk).
#
# Driven by the GALANDA_KIOSK env var rather than a hardcoded flag: the
# Pi's systemd service (see deploy/galanda.service.template) always sets
# GALANDA_KIOSK=1, so the kiosk forces itself into deployment mode no
# matter what this file says in git -- there's nothing to remember to
# flip back and forth between committing from Windows and running on the
# Pi. Leave GALANDA_KIOSK unset for normal dev/laptop runs.
DEV_MODE = os.environ.get("GALANDA_KIOSK") != "1"

# When DEV_MODE is True: shrink the dev window so it actually fits on a
# laptop screen, instead of forcing a literal 1080x1920 window (taller
# than most monitors). The window is still resizable/maximizable, and
# whatever size it ends up at, the whole UI is scaled (via a Scatter, see
# main.py) to fit it while keeping its exact 1080x1920 layout and
# proportions -- so what you see in dev is a shrunk but otherwise
# pixel-accurate preview of the kiosk screen. Set to False if your dev
# monitor is actually tall enough to show the window at full size.
DEV_FIT_TO_SCREEN = True

# Initial dev window size: main.py tries to detect the actual screen's
# usable work area (screen minus taskbar) and fits the window within
# DEV_FIT_SCREEN_MARGIN of it, preserving the 1080:1920 aspect ratio. If
# that detection isn't available (e.g. not on Windows), it falls back to
# plain DEV_FIT_INITIAL_SCALE x SCREEN_WIDTH/HEIGHT instead. Either way,
# resize or maximize the window freely afterwards -- the content keeps
# rescaling to fit. Only used when DEV_FIT_TO_SCREEN is True.
DEV_FIT_SCREEN_MARGIN = 0.85
DEV_FIT_INITIAL_SCALE = 0.35

# Left at 0 (disabled) -- see Config.set("postproc", "jitter_distance",
# ...) in main.py. The intent was to absorb a few pixels of raw
# coordinate noise this eGalax touch controller reports even while a
# finger is held still, but in practice Kivy's jitter postproc ate
# genuine drag/pinch/rotate moves entirely for this device (one-finger
# drag and two-finger gestures stopped working completely with any
# nonzero value) -- not worth the tradeoff. Revisit only with a much
# smaller value and thorough on-device testing, not assumed safe.
TOUCH_JITTER_DISTANCE = 0

# See DraggableImage.on_touch_down in canvas_widgets.py -- a new touch
# landing within this many pixels (at kiosk resolution) of one already
# being tracked by the same image is treated as sensor noise (a ghost
# duplicate of the real finger) rather than a genuine second finger, and
# is ignored so it can't trigger an unwanted rotate/resize. Real two-finger
# pinch/rotate gestures start with fingers much farther apart than this, so
# there's plenty of margin before this could reject an intentional gesture.
GHOST_TOUCH_MIN_SEPARATION = 50

# See _PaddedButton in menu_widgets.py -- how far (in pixels, at kiosk
# resolution) a flat text button's tappable area extends past its visible
# text on every side. These buttons are sized to hug just their own text
# and several (Info, SK/EN) sit flush against a screen edge, which is
# both a small target and where this kind of touchscreen tends to be
# least accurate.
BUTTON_TOUCH_PADDING = 24

# ---------------------------------------------------------------------------
# Screen / layout
# ---------------------------------------------------------------------------

# Target screen: a touchscreen mounted in PORTRAIT orientation.
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 1920

# Height of the strip along the very top (Info/Tutorial button + language
# switch) and the strip along the very bottom (Späť / Nová kompozícia /
# Poslať buttons).
TOP_BAR_HEIGHT = 110
BOTTOM_BAR_HEIGHT = 170

# Height of the row of 5 category buttons (POZADIE / TELO / RUKY / HLAVA /
# PREDMET), directly under the top bar.
CATEGORY_BAR_HEIGHT = 170

# Height of the horizontal-scrolling picker panel that drops down when a
# category button is tapped, showing that category's PNG options.
CATEGORY_PICKER_HEIGHT = 260

# Size of each tappable option inside an open category picker.
CATEGORY_THUMBNAIL_SIZE = (200, 200)

# Height of the floating email-entry bar shown when POSLAŤ is tapped.
# Tall enough to fit its own on-screen keyboard (_SimpleKeyboard in
# menu_widgets.py, 5 rows) below the text field.
EMAIL_BAR_HEIGHT = 700

# The one consistent horizontal inset used by the top bar, category bar and
# bottom bar, so their content (the Info button and SK/EN switch in the top
# bar especially) all lines up against the same left/right margin instead of
# each bar picking its own.
SIDE_MARGIN = 40

# Gap left on each side between the dropdown and the screen edge, so it
# doesn't span edge-to-edge.
DROPDOWN_SIDE_MARGIN = 0

# A plain line along the dropdown's bottom edge only -- its border.
DROPDOWN_OUTLINE_COLOR = (1, 1, 1, 1)
DROPDOWN_OUTLINE_WIDTH = 2

# Underline drawn beneath whichever option is currently "chosen" (the open
# category, the active language) -- see _add_underline() in menu_widgets.py.
UNDERLINE_WIDTH = 2

# The five category buttons, left to right, and the folder name (under
# ASSETS_DIR_NAME) each one's PNG options are loaded from.
CATEGORIES = ["pozadie", "telo", "ruky", "hlava", "predmet"]

# Categories where tapping an option ADDS a new instance to the canvas
# instead of replacing what's already there (up to that category's own cap
# in MAX_INSTANCES_PER_CATEGORY below -- further taps are ignored once a
# category is at its cap). POZADIE (a whole-canvas background image) is the
# only category that stays single-slot, handled separately in
# AppState._select_background -- see AppState.select_category_option.
MULTI_INSTANCE_CATEGORIES = {"telo", "ruky", "hlava", "predmet"}
MAX_INSTANCES_PER_CATEGORY = {
    "telo": 2,
    "ruky": 4,
    "hlava": 2,
    "predmet": 4,
}

# The canvas is a fixed-size rectangle in the middle of the screen -- it is
# NOT the whole remaining space, it's deliberately smaller so there's a
# visible black margin around it. Change these two numbers to resize it.
CANVAS_WIDTH = 723
CANVAS_HEIGHT = 1016

# CanvasArea's own base look: a PNG dropped into assets/canvas/ (see
# image_assets.get_canvas_texture) is stretched to fill the whole canvas --
# there's no flat-color fallback, it's simply blank until that PNG is
# added. Whatever POZADIE image the user then picks is placed on top of
# that, inset by this many pixels on every side -- smaller than the canvas
# itself -- so the paper-like texture stays visible as a border around it.
POZADIE_INSET = 60

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

BACKGROUND_COLOR = (43/255, 40/255, 41/255, 1)                # app background: black
PANEL_BACKGROUND_COLOR = (43/255, 40/255, 41/255, 1)  # side panels / bars: near-black
PANEL_BORDER_COLOR = (43/255, 40/255, 41/255, 1)      # thin separator lines

TEXT_COLOR = (1, 1, 1, 1)                       # default text: white
ACCENT_COLOR = (1, 1, 1, 1)            # buttons / highlights: warm gold

# Dashed outline drawn around the currently-selected image.
SELECTION_HIGHLIGHT_COLOR = ACCENT_COLOR
SELECTION_HIGHLIGHT_WIDTH = 2

# Key background for the email bar's on-screen keyboard (_SimpleKeyboard
# in menu_widgets.py) -- lighter than PANEL_BACKGROUND_COLOR so each key
# actually reads as a tappable button against the bar's near-black
# background, rather than disappearing into it.
KEYBOARD_KEY_COLOR = (70/255, 70/255, 70/255, 1)

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

# None means "use Kivy's built-in default font". To use a custom font later,
# set this to the path of a .ttf file, e.g. os.path.join(BASE_DIR, "fonts", "MyFont.ttf").
FONT_NAME = os.path.join(BASE_DIR, "fonts", "RoobertTRIAL-Medium.ttf")

# These apply everywhere EXCEPT the start/intro screen (see
# INTRO_BUTTON_FONT_SIZE below), which keeps its own separate size so
# changes here don't affect it.
FONT_SIZE_SMALL = "22sp"
FONT_SIZE_NORMAL = "38sp"
FONT_SIZE_LARGE = "40sp"

# The intro screen's START/Nová kompozícia label -- frozen at the size
# FONT_SIZE_LARGE used to be, deliberately not tied to it, so it doesn't
# move if FONT_SIZE_LARGE changes later.
INTRO_BUTTON_FONT_SIZE = "28sp"


def font_kwargs():
    """Widget kwarg dict for the font: {"font_name": FONT_NAME} if a custom
    font has been set above, or {} to just fall back to Kivy's own default
    font (Kivy's font_name property doesn't accept None directly, so a
    custom font path has to be added conditionally like this)."""
    return {} if FONT_NAME is None else {"font_name": FONT_NAME}

# ---------------------------------------------------------------------------
# Category images
# ---------------------------------------------------------------------------

# Folder names (relative to this file's location).
ASSETS_DIR_NAME = "assets"
EXPORT_DIR_NAME = "exports"

# A newly placed image (TELO/RUKY/HLAVA/PREDMET) is scaled to fit inside a
# box of this size (in pixels), preserving its own width/height ratio.
IMAGE_INITIAL_SIZE = (300, 300)

# How far a placed image can be pinch-resized, as a multiplier of its
# initial size.
IMAGE_SCALE_MIN = 0.3
IMAGE_SCALE_MAX = 3.0

# The round "X" delete badge shown at the top-right corner of a selected
# placed image (see DraggableImage in canvas_widgets.py). It's a child of
# the image's own Scatter, so it rotates/scales along with the image's
# frame rather than staying screen-space fixed.
DELETE_BUTTON_SIZE = (44, 44)
DELETE_BUTTON_COLOR = (0, 0, 0, 1)

# How far the delete badge's tappable area extends beyond its visible
# circle on every side, in pixels -- a touch anywhere within DELETE_BUTTON_SIZE
# plus this padding registers, not just a precise tap on the small circle
# itself.
DELETE_BUTTON_TOUCH_PADDING = 24

# ---------------------------------------------------------------------------
# Icons
# ---------------------------------------------------------------------------

ICON_DIR = os.path.join(BASE_DIR, "icon")

# Icon shown to the left of each label on the bottom bar buttons (back.png/
# new.png/send.png) -- see _IconButton in menu_widgets.py. These are
# detailed illustrations, not simple flat glyphs (native sizes run from
# ~660px to ~1200px), so a small box loses most of their detail no matter
# the source format -- but keep_ratio still means bigger isn't
# automatically better for every icon's own proportions, so this sits
# between the original 32px and the 56px that turned out too big.
BUTTON_ICON_SIZE = (44, 44)

# start.png/back.png on the intro screen are full illustrations (native
# 997x1600 / 1228x809) -- see _IntroButton in intro_screen.py -- so they
# get a much bigger box than the other icon buttons.
INTRO_BUTTON_ICON_SIZE = (120, 165)

# Size of the big start/end-screen image (assets/start/) as a fraction (0-1)
# of the space available to it -- the same widget serves both the start and
# the end screen, so this sizes both. Lower = smaller image.
INTRO_IMAGE_SCALE = 0.6

# Gap between the icon and the label: vertical (icon centered above the
# label) on the start screen, horizontal (icon to the left of the label)
# on the end screen shown after a send -- see _IntroButton.set_stacked().
INTRO_BUTTON_SPACING = 28
INTRO_BUTTON_SIDE_SPACING = 20

# Left/right arrow icons flanking an open category picker's scrolling row
# -- between the original 48px and the 24px that turned out too small.
SCROLL_ARROW_SIZE = (36, 36)
# How far one tap on an arrow scrolls the picker, as a fraction (0-1) of
# its total scrollable range.
SCROLL_STEP = 0.25
