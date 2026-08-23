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

    def on_press(self):
        App.get_running_app().state.delete_selected()


class DraggableImage(Scatter):
    """One PNG image instance placed on the canvas (TELO/RUKY/HLAVA slot,
    or one of possibly several PREDMET items)."""

    # True while this is the image currently touched/selected -- shows a
    # highlight rectangle around it.
    selected = BooleanProperty(False)

    def __init__(self, image_path, **kwargs):
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
            # bring it to the front. There are no dedicated front/back
            # buttons any more -- touch is how overlapping body parts get
            # rearranged.
            auto_bring_to_front=True,
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


class CanvasArea(Widget):
    """The fixed-size canvas surface in the middle of the screen. Its
    background is a flat color (theme.DEFAULT_CANVAS_COLOR) until a POZADIE
    image is picked, at which point set_background_image() stretches that
    image to fill the canvas. DraggableImage instances are added to it as
    normal child widgets by AppState."""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (theme.CANVAS_WIDTH, theme.CANVAS_HEIGHT))
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(rgba=theme.DEFAULT_CANVAS_COLOR)
            self._background_rect = Rectangle(pos=self.pos, size=self.size)
            # Drawn on top of the flat color rect above; has no texture
            # (and so is invisible, just showing the color through) until
            # set_background_image() gives it one.
            Color(1, 1, 1, 1)
            self._background_image_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_background_rect, size=self._update_background_rect)

    def _update_background_rect(self, *args):
        self._background_rect.pos = self.pos
        self._background_rect.size = self.size
        self._background_image_rect.pos = self.pos
        self._background_image_rect.size = self.size

    def set_background_image(self, image_path):
        """Set (or, with None, clear back to the flat DEFAULT_CANVAS_COLOR)
        the POZADIE image stretched to fill the whole canvas."""
        self._background_image_rect.texture = None if image_path is None else CoreImage(image_path).texture

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # Any tap on the canvas -- whether it lands on an image or
            # empty space -- closes the info/tutorial dropdown if it's
            # open, since it's in the way of actually composing.
            App.get_running_app().state.close_tutorial()

        # Let child images (drawn on top) have first go at the touch. Kivy's
        # default Widget.on_touch_down already does this for us and returns
        # a value telling us whether one of them grabbed it.
        handled = super().on_touch_down(touch)
        if not handled and self.collide_point(*touch.pos):
            App.get_running_app().state.select_target("canvas")
            return True
        return handled
