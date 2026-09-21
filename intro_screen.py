# intro_screen.py
#
# IntroScreen is shown instead of the normal top/category/canvas/bottom bar
# UI in two moments (see AppState.screen):
#   - The very first thing the app shows on launch.
#   - Again after a finished composition has been emailed (see
#     GalandaApp.confirm_send in main.py).
#
# Both are the same widget: a centered image (the single PNG in
# assets/start/, loaded the same way category picker options are) with one
# big flat button underneath. The button's icon, label, AND layout all
# differ between the two states -- start.png centered above "START" the
# first time, back.png to the left of "Nová kompozícia" after a send --
# tracked by AppState.intro_button_key and kept in sync here.

import os

from kivy.app import App
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

import image_assets
import theme
import translations

# intro_button_key -> (icon filename under theme.ICON_DIR, stacked?) for
# that state. "stacked" = icon centered above the label (start screen);
# not stacked = icon to the left of the label (end screen, after a send).
_BUTTON_CONFIG = {
    "start_button": ("start.png", True),
    "new_session_button": ("back.png", False),
}


class _IntroButton(ButtonBehavior, FloatLayout):
    """Icon+text button whose icon, label, AND layout all change together
    (see _BUTTON_CONFIG) as AppState.intro_button_key changes -- unlike
    every other icon button in the app, which has one fixed icon/layout.

    The icon and label are positioned by hand in _relayout() rather than by
    a nested BoxLayout: a BoxLayout re-lays out its children on its own
    schedule and snaps them back to one edge on the cross axis, undoing any
    centering applied from outside, which left the icon and text off-axis."""

    def __init__(self, on_press, **kwargs):
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", 280)
        super().__init__(**kwargs)
        self.bind(on_press=lambda *_a: on_press())
        self._stacked = True

        self.icon = Image(
            size_hint=(None, None),
            size=theme.INTRO_BUTTON_ICON_SIZE,
            allow_stretch=True,
            keep_ratio=True,
        )
        self.add_widget(self.icon)

        self.label = Label(
            font_size=theme.INTRO_BUTTON_FONT_SIZE,
            **theme.font_kwargs(),
            color=theme.ACCENT_COLOR,
            size_hint=(None, None),
            halign="center",
        )
        self.label.bind(texture_size=self.label.setter("size"))
        self.add_widget(self.label)

        self.bind(size=self._relayout, pos=self._relayout)
        self.icon.bind(size=self._relayout)
        self.label.bind(size=self._relayout)
        self._relayout()

    def set_stacked(self, stacked):
        self._stacked = stacked
        self._relayout()

    def _relayout(self, *_args):
        icon, label = self.icon, self.label
        # Centers are computed from x/y/width/height directly, NOT read from
        # self.center_x/center_y: those are cached alias properties that are
        # still stale when this runs from a size/pos change callback, which
        # left the icon and label stuck at the button's old (tiny) center.
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        if self._stacked:
            # Icon above label, both centered on the button's vertical axis.
            spacing = theme.INTRO_BUTTON_SPACING
            total_h = icon.height + spacing + label.height
            icon_y = cy + total_h / 2 - icon.height
            icon.pos = (cx - icon.width / 2, icon_y)
            label.pos = (cx - label.width / 2, icon_y - spacing - label.height)
        else:
            # Icon left of label, both centered on the horizontal axis.
            spacing = theme.INTRO_BUTTON_SIDE_SPACING
            left = cx - (icon.width + spacing + label.width) / 2
            icon.pos = (left, cy - icon.height / 2)
            label.pos = (left + icon.width + spacing, cy - label.height / 2)


class IntroScreen(BoxLayout):

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, 1))
        kwargs.setdefault("padding", 40)
        kwargs.setdefault("spacing", 24)
        super().__init__(**kwargs)

        state = App.get_running_app().state
        start_image_path = image_assets.get_start_image(state.assets_dir)

        if start_image_path is not None:
            # Image plays multi-frame GIFs automatically (default
            # anim_delay=0.25s/frame) -- no extra code needed for that.
            self.image = Image(
                source=start_image_path,
                allow_stretch=True,
                keep_ratio=True,
                size_hint=(theme.INTRO_IMAGE_SCALE, theme.INTRO_IMAGE_SCALE),
            )
        else:
            # No start image dropped in yet -- show a placeholder message
            # instead of a blank gap, so it's obvious what's missing.
            self.image = Label(
                font_size=theme.FONT_SIZE_NORMAL,
                **theme.font_kwargs(),
                color=theme.TEXT_COLOR,
                size_hint=(1, 1),
            )
            App.get_running_app().register_i18n(self.image, "start_image_missing")
        # The image is smaller than its slot (see theme.INTRO_IMAGE_SCALE),
        # and a BoxLayout would pin it to a corner, so it's centered in the
        # slot by an AnchorLayout.
        image_slot = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, 1))
        image_slot.add_widget(self.image)
        self.add_widget(image_slot)

        self.button = _IntroButton(on_press=state.start_composition)
        self.add_widget(self.button)

        # The button's icon/text both depend on intro_button_key, which
        # changes at runtime, so they can't use the fixed-key
        # register_i18n() helper -- kept in sync manually here instead.
        state.bind(current_language=self._refresh_button, intro_button_key=self._refresh_button)
        self._refresh_button()

    def _refresh_button(self, *_args):
        state = App.get_running_app().state
        self.button.label.text = translations.get_text(state.current_language, state.intro_button_key)
        icon_name, stacked = _BUTTON_CONFIG[state.intro_button_key]
        self.button.icon.source = os.path.join(theme.ICON_DIR, icon_name)
        self.button.set_stacked(stacked)
