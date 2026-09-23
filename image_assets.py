# image_assets.py
#
# Loads the PNG options shown in a category's horizontal picker (see
# CategoryPickerPanel in menu_widgets.py). Each category is just a folder
# under assets/ (theme.ASSETS_DIR_NAME) -- e.g. assets/hlava/ -- and every
# .png file dropped into it becomes one selectable option, in alphabetical
# order by filename. There's no manifest or registration step: adding or
# removing artwork is just adding or removing files in that folder.

import logging
import os

from PIL import Image as PILImage

import theme

# Pillow's PNG decoder logs at DEBUG (one line per chunk -- IHDR, IDAT,
# ...), which otherwise floods the console/journalctl with binary-chunk
# noise every time get_category_thumbnail() below decodes a source image,
# since Kivy's own logging setup ends up routing even DEBUG-level messages
# from other loggers through to the console.
logging.getLogger("PIL").setLevel(logging.WARNING)

_IMAGE_EXTENSIONS = (".png",)

# Where pre-generated category-picker thumbnails (see get_category_
# thumbnail() below) are cached, as assets_dir/.thumbnails/<category>/
# <filename> -- a dot-prefixed sibling of the category folders themselves,
# so it's never picked up by get_category_assets()'s own directory listing.
_THUMBNAIL_CACHE_DIR_NAME = ".thumbnails"

# The start/end-screen image (see get_start_image()) can be an animated GIF
# -- Kivy's Image widget plays multi-frame GIFs automatically -- or a plain
# PNG if you'd rather keep it static.
_START_IMAGE_EXTENSIONS = (".gif", ".png")


def get_category_assets(assets_dir, category):
    """Return a sorted list of (name, filepath) for every PNG file in
    assets_dir/category/. `name` is the filename without its extension.
    Returns an empty list if the folder doesn't exist yet or is empty --
    that's the normal state until the real artwork is dropped in."""
    category_dir = os.path.join(assets_dir, category)
    if not os.path.isdir(category_dir):
        return []

    assets = []
    for filename in sorted(os.listdir(category_dir)):
        if filename.lower().endswith(_IMAGE_EXTENSIONS):
            name = os.path.splitext(filename)[0]
            assets.append((name, os.path.join(category_dir, filename)))
    return assets


def get_category_thumbnail(assets_dir, category, image_path):
    """Return the path to a small, pre-scaled copy of image_path (down to
    theme.CATEGORY_THUMBNAIL_SIZE) for the category picker to display,
    generating and caching it first if it doesn't exist yet or the source
    file has changed since.

    The source artwork in assets/<category>/ is full-resolution (easily
    1000-1600px, several MB each -- see deploy/README.md's touch notes for
    how underpowered the Pi's CPU is by comparison) but only ever shown at
    CATEGORY_THUMBNAIL_SIZE in the picker (see AssetThumbnailButton in
    menu_widgets.py). Decoding all of a category's full-size PNGs on the UI
    thread every time it's opened is what caused the picker's noticeable
    delay -- this makes that a one-time cost per asset instead of a
    every-open one. Placing a picked option on the canvas still uses the
    original full-resolution image_path, not this thumbnail."""
    cache_dir = os.path.join(assets_dir, _THUMBNAIL_CACHE_DIR_NAME, category)
    thumbnail_path = os.path.join(cache_dir, os.path.basename(image_path))

    if os.path.exists(thumbnail_path) and os.path.getmtime(thumbnail_path) >= os.path.getmtime(image_path):
        return thumbnail_path

    os.makedirs(cache_dir, exist_ok=True)
    with PILImage.open(image_path) as source:
        source = source.convert("RGBA")
        source.thumbnail(theme.CATEGORY_THUMBNAIL_SIZE, PILImage.LANCZOS)
        source.save(thumbnail_path)
    return thumbnail_path


def pregenerate_thumbnails(assets_dir):
    """Generate (or refresh, if the source artwork changed) every
    category's thumbnails up front -- called on a background thread at app
    startup (see main.py) so the picker's first open per category doesn't
    pay get_category_thumbnail()'s one-time generation cost either."""
    for category in theme.CATEGORIES:
        for _name, path in get_category_assets(assets_dir, category):
            get_category_thumbnail(assets_dir, category, path)


def get_canvas_texture(assets_dir):
    """Return the path to the single canvas-texture image (a PNG) in
    assets/canvas/, used as CanvasArea's own paper-like background -- or
    None if it hasn't been added yet, in which case CanvasArea is simply
    blank. Same one-file-in-a-folder convention as get_start_image() below."""
    canvas_dir = os.path.join(assets_dir, "canvas")
    if not os.path.isdir(canvas_dir):
        return None

    for filename in sorted(os.listdir(canvas_dir)):
        if filename.lower().endswith(_IMAGE_EXTENSIONS):
            return os.path.join(canvas_dir, filename)
    return None


def _get_single_image(assets_dir, folder):
    """Return the path to the single image (an animated GIF or a PNG) in
    assets_dir/folder/, or None if it hasn't been added yet. Shared by
    get_start_image() and get_aftersent_image() below -- same
    one-file-in-a-folder convention for both."""
    image_dir = os.path.join(assets_dir, folder)
    if not os.path.isdir(image_dir):
        return None

    for filename in sorted(os.listdir(image_dir)):
        if filename.lower().endswith(_START_IMAGE_EXTENSIONS):
            return os.path.join(image_dir, filename)
    return None


def get_start_image(assets_dir):
    """Return the path to the single start-screen image in assets/start/,
    shown on first launch, or None if it hasn't been added yet."""
    return _get_single_image(assets_dir, "start")


def get_aftersent_image(assets_dir):
    """Return the path to the single post-send-screen image in
    assets/aftersent/, shown after a composition has been emailed, or None
    if it hasn't been added yet (in which case the start image is reused)."""
    return _get_single_image(assets_dir, "aftersent")
