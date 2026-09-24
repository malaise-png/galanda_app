# canvas_widgets.py
#
# The two widgets that make up the actual drawing area:
#
#   CanvasArea     - the fixed-size rectangle in the middle of the screen.
#                    Holds the background image/color and every DraggableImage
#                    placed on it (as normal Kivy child widgets).
#   DraggableImage - one PNG image instance sitting on the canvas (a body,
#                    hands, head, or item). Built on top of Kivy's Scatter
#                    widget, which already handles drag-to-move,
#                    two-finger-rotate and pinch-to-resize for us -- we just
#                    add drawing the image texture, selecting it, and
#                    bringing it to the front on touch.

from kivy.app import App
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.properties import BooleanProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget
from kivy.vector import Vector

import image_assets
import theme


class _DeleteBadge(ButtonBehavior, Label):
    """Small round 'X' shown at the top-right corner of a selected
    DraggableImage -- tapping it deletes that image (see
    AppState.delete_selected()). Added/removed as a plain child of the
    Scatter (see DraggableImage.on_selected), so it rotates and scales
    along with the image's own frame rather than staying screen-fixed."""

    def __init__(self, **kwargs):
        kwargs.setdefault("text", "X")
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", theme.FONT_SIZE_SMALL)
        kwargs.setdefault("color", (1, 1, 1, 1))
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", theme.DELETE_BUTTON_SIZE)
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(rgba=theme.DELETE_BUTTON_COLOR)
            self._badge = Ellipse(pos=self.pos, size=self.size)
        self.bind(pos=self._update_badge, size=self._update_badge)

    def _update_badge(self, *_args):
        self._badge.pos = self.pos
        self._badge.size = self.size

    def collide_point(self, x, y):
        # ButtonBehavior's default hit test is the widget's own tight
        # (self.size) box -- just the visible circle. Padding it out makes
        # the tap target meaningfully bigger than the small badge itself,
        # without changing how big the badge looks.
        pad = theme.DELETE_BUTTON_TOUCH_PADDING
        return (
            self.x - pad <= x <= self.right + pad
            and self.y - pad <= y <= self.top + pad
        )

    def on_press(self):
        App.get_running_app().state.delete_selected()


def _clamp_axis(pos, size, canvas_pos, canvas_size):
    """Clamp a bounding box's position along one axis so it stays fully
    inside [canvas_pos, canvas_pos + canvas_size]. If the box is bigger than
    the canvas on this axis (possible once scaled up, or once rotated makes
    the axis-aligned bounding box bigger than the image itself), there's no
    position that satisfies that, so it's centered on the canvas instead --
    better than letting it be dragged arbitrarily far off to one side."""
    max_pos = canvas_pos + canvas_size - size
    if max_pos < canvas_pos:
        return canvas_pos + (canvas_size - size) / 2
    return min(max(pos, canvas_pos), max_pos)


class DraggableImage(Scatter):
    """One PNG image instance placed on the canvas (POZADIE/TELO/RUKY/HLAVA/
    PREDMET slot)."""

    # True while this is the image currently touched/selected -- shows a
    # highlight rectangle around it.
    selected = BooleanProperty(False)

    def __init__(self, image_path, bring_to_front=True, **kwargs):
        texture = CoreImage(image_path).texture

        # Fit the image inside theme.IMAGE_INITIAL_SIZE while keeping its
        # own width/height ratio, so it doesn't come out stretched.
        box_width, box_height = theme.IMAGE_INITIAL_SIZE
        aspect_ratio = texture.width / texture.height
        if aspect_ratio >= 1:
            width = box_width
            height = box_width / aspect_ratio
        else:
            width = box_height * aspect_ratio
            height = box_height

        super().__init__(
            size_hint=(None, None),
            size=(width, height),
            do_rotation=True,
            do_scale=True,
            do_translation=True,
            scale_min=theme.IMAGE_SCALE_MIN,
            scale_max=theme.IMAGE_SCALE_MAX,
            # Unlike the app's old vector shapes, touching an image DOES
            # bring it to the front -- except a body (TELO), which must
            # always stay directly above the background and below every
            # other placed image; AppState creates those with
            # bring_to_front=False so touching one never reorders it.
            auto_bring_to_front=bring_to_front,
            **kwargs
        )

        self.image_path = image_path

        with self.canvas:
            Color(1, 1, 1, 1)
            self._image_rect = Rectangle(texture=texture, pos=(0, 0), size=(width, height))
            # Selection highlight rectangle, added once and simply made
            # transparent/opaque afterwards (see on_selected below).
            self._highlight_color_instr = Color(rgba=(*theme.SELECTION_HIGHLIGHT_COLOR[:3], 0))
            self._highlight_line_instr = Line(
                rectangle=(0, 0, width, height),
                width=theme.SELECTION_HIGHLIGHT_WIDTH,
            )

        # Straddles the top-right corner of the frame (centered exactly on
        # it), only added as a child while selected -- see on_selected.
        self._delete_badge = _DeleteBadge()
        self._delete_badge.center = (width, height)

    def on_selected(self, instance, value):
        self._highlight_color_instr.a = 1 if value else 0
        if value:
            if self._delete_badge.parent is None:
                self.add_widget(self._delete_badge)
        elif self._delete_badge.parent is not None:
            self.remove_widget(self._delete_badge)

    def on_touch_down(self, touch):
        # Some touch controllers (this kiosk's eGalax panel included)
        # occasionally report a spurious second contact point a few pixels
        # from a real single-finger touch. Scatter treats any two touches
        # it's tracking as a rotate/scale gesture (see
        # transform_with_touch in kivy/uix/scatter.py), and that gesture's
        # angle/scale math is numerically unstable when the two points are
        # nearly coincident -- tiny sensor noise then reads as a sudden,
        # unwanted rotate/resize in the middle of what should be a plain
        # one-finger drag. Refusing to grab a new touch that lands
        # implausibly close to one already being tracked keeps a ghost
        # point from ever becoming Scatter's "second finger".
        for existing_touch in self._touches:
            if Vector(*touch.pos).distance(self._last_touch_pos[existing_touch]) < theme.GHOST_TOUCH_MIN_SEPARATION:
                return False

        # Scatter's own on_touch_down already checks whether the touch is
        # actually inside this image (accounting for its current rotation
        # and scale) before returning True, so `handled` being True already
        # means the touch landed on this image. It also dispatches to
        # children (like the delete badge) first -- if tapping the badge
        # just deleted this image, `self.parent` is now None, so don't
        # re-select an image that's no longer on the canvas.
        handled = super().on_touch_down(touch)
        if handled and self.parent is not None:
            App.get_running_app().state.select_target(self)
        return handled

    def on_transform_with_touch(self, touch):
        # Called after Scatter has applied a touch-driven drag/rotate/pinch
        # to this image -- clamp it back so it can never be moved (or
        # resized) out of the canvas's own bounds. self.bbox is the image's
        # axis-aligned bounding box in its parent's (the canvas's)
        # coordinates, already accounting for the current rotation/scale.
        super().on_transform_with_touch(touch)
        canvas_area = self.parent
        if canvas_area is None:
            return
        (box_x, box_y), (box_width, box_height) = self.bbox
        new_x = _clamp_axis(box_x, box_width, canvas_area.x, canvas_area.width)
        new_y = _clamp_axis(box_y, box_height, canvas_area.y, canvas_area.height)
        if new_x != box_x:
            self.x = new_x
        if new_y != box_y:
            self.y = new_y


class CanvasArea(Widget):
    """The fixed-size canvas surface in the middle of the screen. Its own
    base look is just the PNG dropped into assets/canvas/ (see
    image_assets.get_canvas_texture), stretched to fill the whole canvas --
    there's no flat-color fallback, so it's simply blank until that PNG is
    added. Once a POZADIE image is picked, set_background_image() places it
    on top of that, inset by theme.POZADIE_INSET on every side so the
    canvas texture stays visible as a border around it. DraggableImage
    instances are added to it as normal child widgets by AppState."""

    def __init__(self, assets_dir, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (theme.CANVAS_WIDTH, theme.CANVAS_HEIGHT))
        super().__init__(**kwargs)

        canvas_texture_path = image_assets.get_canvas_texture(assets_dir)
        canvas_texture = None if canvas_texture_path is None else CoreImage(canvas_texture_path).texture

        with self.canvas.before:
            # A Rectangle with no texture still paints an opaque flat fill
            # in whatever Color came before it -- so rather than that
            # showing through as a solid white square, this Color's alpha
            # stays 0 (fully transparent) until there actually is a
            # texture, making "no PNG yet" look like nothing drawn at all.
            self._canvas_texture_color = Color(rgba=(1, 1, 1, 1 if canvas_texture else 0))
            self._canvas_texture_rect = Rectangle(texture=canvas_texture, pos=self.pos, size=self.size)

            # The user-picked POZADIE image, inset smaller than the canvas
            # itself (see _update_background_rect) so the texture above
            # stays visible as a border around it. Same alpha trick: stays
            # transparent (rather than an opaque white patch) until
            # set_background_image() actually gives it a texture.
            self._background_image_color = Color(rgba=(1, 1, 1, 0))
            self._background_image_rect = Rectangle()

        self.bind(pos=self._update_background_rect, size=self._update_background_rect)
        self._update_background_rect()

    def _update_background_rect(self, *args):
        self._canvas_texture_rect.pos = self.pos
        self._canvas_texture_rect.size = self.size

        inset = theme.POZADIE_INSET
        self._background_image_rect.pos = (self.x + inset, self.y + inset)
        self._background_image_rect.size = (self.width - 2 * inset, self.height - 2 * inset)

    def set_background_image(self, image_path):
        """Set (or, with None, clear back to just the canvas texture
        showing through) the POZADIE image, inset by theme.POZADIE_INSET to
        fill everything but a border around the canvas."""
        if image_path is None:
            self._background_image_rect.texture = None
            self._background_image_color.a = 0
        else:
            self._background_image_rect.texture = CoreImage(image_path).texture
            self._background_image_color.a = 1

    def on_touch_down(self, touch):
        # Let child images (drawn on top) have first go at the touch. Kivy's
        # default Widget.on_touch_down already does this for us and returns
        # a value telling us whether one of them grabbed it.
        handled = super().on_touch_down(touch)
        if not handled and self.collide_point(*touch.pos):
            App.get_running_app().state.select_target("canvas")
            return True
        return handled
