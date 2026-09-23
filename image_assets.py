# image_assets.py
#
# Loads the PNG options shown in a category's horizontal picker (see
# CategoryPickerPanel in menu_widgets.py). Each category is just a folder
# under assets/ (theme.ASSETS_DIR_NAME) -- e.g. assets/hlava/ -- and every
# .png file dropped into it becomes one selectable option, in alphabetical
# order by filename. There's no manifest or registration step: adding or
# removing artwork is just adding or removing files in that folder.

import os

_IMAGE_EXTENSIONS = (".png",)

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
