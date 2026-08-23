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
# big flat text button underneath. Only the button's label differs --
# "START" the first time, "Nová kompozícia" after a send -- which is
# tracked by AppState.intro_button_key and kept in sync here.

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label

import image_assets
import theme
import translations


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
                source=start_image_path, allow_stretch=True, keep_ratio=True, size_hint=(1, 1)
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
        self.add_widget(self.image)

        self.button = Button(
            font_size=theme.FONT_SIZE_LARGE,
            **theme.font_kwargs(),
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            color=theme.ACCENT_COLOR,
            size_hint=(1, None),
            height=110,
        )
        self.button.bind(on_press=lambda *_a: state.start_composition())
        self.add_widget(self.button)

        # The button's translation key can change at runtime
        # (intro_button_key), unlike every other button in the app, so it
        # can't use the fixed-key register_i18n() helper -- it's kept in
        # sync manually here instead.
        state.bind(current_language=self._refresh_button_text, intro_button_key=self._refresh_button_text)
        self._refresh_button_text()

    def _refresh_button_text(self, *_args):
        state = App.get_running_app().state
        self.button.text = translations.get_text(state.current_language, state.intro_button_key)
