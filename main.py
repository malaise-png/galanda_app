# main.py
#
# Entry point. Run this file to start the app: `python main.py`
#
# IMPORTANT: Kivy reads its window settings (fullscreen, borderless, size,
# the Escape-quits-app shortcut, ...) the first time anything touches
# `kivy.core.window` / `kivy.app` -- which happens the moment you import
# them. So all `Config.set(...)` calls below MUST happen before those
# imports, or they'll silently have no effect. Don't reorder the imports
# in this file without keeping that in mind.

import os

from kivy.config import Config

import theme


def _detect_dev_screen_size():
    """Best-effort detection of the current screen's usable work area
    (screen resolution minus the taskbar), used to size the initial dev
    window so it actually fits. Returns None if detection isn't available
    (e.g. not running on Windows) -- callers fall back to a fixed fraction
    of SCREEN_WIDTH/HEIGHT instead."""
    try:
        import ctypes
        import ctypes.wintypes

        rect = ctypes.wintypes.RECT()
        # SPI_GETWORKAREA = 0x0030 -- the screen area excluding the taskbar.
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)
        return rect.right - rect.left, rect.bottom - rect.top
    except Exception:
        return None


if theme.DEV_MODE:
    Config.set("graphics", "fullscreen", "0")
    Config.set("graphics", "borderless", "0")
    if theme.DEV_FIT_TO_SCREEN:
        # Open a smaller, resizable window instead of forcing the literal
        # 1080x1920 kiosk resolution (taller than most dev monitors). The
        # whole UI is still laid out at exactly SCREEN_WIDTH x
        # SCREEN_HEIGHT and just rendered scaled down to fit whatever
        # window it's in (see build()/_fit_content_to_window below), so
        # resizing or maximizing this window is enough to "fit to screen"
        # -- the content keeps rescaling itself automatically.
        screen_size = _detect_dev_screen_size()
        if screen_size is not None:
            screen_width, screen_height = screen_size
            initial_scale = min(
                (screen_width * theme.DEV_FIT_SCREEN_MARGIN) / theme.SCREEN_WIDTH,
                (screen_height * theme.DEV_FIT_SCREEN_MARGIN) / theme.SCREEN_HEIGHT,
            )
        else:
            initial_scale = theme.DEV_FIT_INITIAL_SCALE
        Config.set("graphics", "width", str(int(theme.SCREEN_WIDTH * initial_scale)))
        Config.set("graphics", "height", str(int(theme.SCREEN_HEIGHT * initial_scale)))
        Config.set("graphics", "resizable", "1")
    else:
        Config.set("graphics", "width", str(theme.SCREEN_WIDTH))
        Config.set("graphics", "height", str(theme.SCREEN_HEIGHT))
    # Lets a second, simulated touch point be added by holding Ctrl and
    # clicking, so two-finger gestures (rotate, pinch-resize) can be tested
    # with just a mouse. Not needed (and turned off) on the real touchscreen.
    Config.set("input", "mouse", "mouse,multitouch_on_demand")
else:
    # True fullscreen kiosk mode with no window border, for the Pi.
    Config.set("graphics", "fullscreen", "auto")
    Config.set("graphics", "borderless", "1")
    # Force Kivy's own docked on-screen keyboard for the email entry field
    # (EmailSendBar) -- the kiosk has a touchscreen and no physical
    # keyboard attached. Left as the default ("") in DEV_MODE, so dev
    # testing just uses the laptop's real keyboard instead.
    Config.set("kivy", "keyboard_mode", "dock")
    # See theme.TOUCH_JITTER_DISTANCE -- absorbs small raw-coordinate noise
    # from the touch panel so a held/slow touch doesn't register as a tiny
    # unintended drag.
    Config.set("postproc", "jitter_distance", str(theme.TOUCH_JITTER_DISTANCE))
    # Kivy's own kivy/config.py adds this "%(name)s = probesysfs,..." entry
    # by default on Linux -- a direct-from-/dev/input touch provider that
    # runs independently of SDL2's own window input, and turned out to be
    # the ONLY thing actually delivering touch on this kiosk's
    # Wayland/labwc session (SDL2 wasn't reliably feeding touch through on
    # its own -- an earlier attempt to remove this entirely left the app
    # with no working touch at all). It defaults to reading the touch
    # device raw, with no rotation applied, which doesn't match the
    # screen's 90 clockwise OS-level rotation (see deploy/README.md) --
    # `param=rotation=90` is forwarded straight through to the underlying
    # mtdev provider (see probesysfs.py's own docstring for that syntax),
    # which applies the rotation itself. This is a DIFFERENT code path
    # from -- and not affected by -- the libinput calibration matrix
    # described in deploy/README.md; that matrix only matters for
    # touch delivered through Wayland/libinput/SDL2, which this app isn't
    # actually using. rotation=90 (with no extra invert flags) was solved
    # directly from mtdev.py's own coordinate math against two known real
    # touch points (see deploy/README.md), not guessed.
    Config.set("input", "%(name)s", "probesysfs,provider=mtdev,param=rotation=90")

# This is a kiosk app with no exit button anywhere in the UI, so the
# default "Escape key quits the app" shortcut must be turned off in both
# DEV_MODE and deployment -- otherwise a stray Escape press closes the app.
Config.set("kivy", "exit_on_escape", "0")

# --- Only safe to import kivy.app / kivy.core.window / kivy.uix.* below ---

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scatter import Scatter

import email_sender
import translations
from app_state import AppState
from canvas_widgets import CanvasArea
from intro_screen import IntroScreen
from menu_widgets import BottomBar, CategoryBar, CategoryPickerPanel, EmailSendBar, TopBar, TutorialPanel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, theme.ASSETS_DIR_NAME)
EXPORT_DIR = os.path.join(BASE_DIR, theme.EXPORT_DIR_NAME)


class GalandaApp(App):

    def build(self):
        self.title = "Galanda"

        self.state = AppState(ASSETS_DIR)
        # (widget, translation_key, attribute_name) triples -- see
        # register_i18n()/refresh_all_text() below.
        self.i18n_registry = []
        self.state.bind(current_language=self.refresh_all_text)

        # `content` is always laid out at the exact kiosk resolution
        # (theme.SCREEN_WIDTH x SCREEN_HEIGHT), regardless of the actual
        # window size. It's wrapped in a Scatter below, which scales (and
        # centers) it to fit whatever window/screen it's actually shown
        # in -- so every size in theme.py keeps meaning "pixels at kiosk
        # resolution" even while dev-testing in a smaller window.
        content = FloatLayout(size=(theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT), size_hint=(None, None))
        with content.canvas.before:
            Color(rgba=theme.BACKGROUND_COLOR)
            self._background_rect = Rectangle(pos=content.pos, size=content.size)
        content.bind(pos=self._update_background_rect, size=self._update_background_rect)

        # -- canvas, centered in the space between the bars ---------------------
        canvas_area = CanvasArea(ASSETS_DIR, pos_hint={"center_x": 0.5, "center_y": 0.5})
        self.state.canvas_area = canvas_area

        canvas_holder = FloatLayout(size_hint=(1, 1))
        canvas_holder.add_widget(canvas_area)

        # -- top bar / category bar / canvas / bottom bar, stacked -----------
        top_bar = TopBar()
        category_bar = CategoryBar()
        bottom_bar = BottomBar()

        self.compose_screen = BoxLayout(orientation="vertical", size_hint=(1, 1))
        self.compose_screen.add_widget(top_bar)
        self.compose_screen.add_widget(category_bar)
        self.compose_screen.add_widget(canvas_holder)
        self.compose_screen.add_widget(bottom_bar)

        # -- intro screen: shown on first launch, and again after a send ----
        self.intro_screen = IntroScreen()

        self.root_layout = content

        # Only one of compose_screen/intro_screen is ever a child of
        # `content` at a time -- see _refresh_screen(), which also runs
        # once now to add whichever AppState.screen starts as ("intro").
        self.state.bind(screen=self._refresh_screen)
        self._refresh_screen()

        # The tutorial dropdown and category picker both float directly on
        # `content`, on top of compose_screen -- each only added while
        # visible, so neither blocks touches to the rest of the app while
        # hidden. Being added (and so re-added to the front of `content`'s
        # children) after compose_screen already exists is what makes them
        # draw on top of the canvas rather than underneath it.
        self.tutorial_panel = TutorialPanel()
        self.state.bind(tutorial_open=self._refresh_tutorial_panel)
        self._refresh_tutorial_panel()

        self.category_picker_panel = CategoryPickerPanel()
        self.category_picker_panel.pos_hint = {"x": 0}
        self.category_picker_panel.top = theme.SCREEN_HEIGHT - (theme.TOP_BAR_HEIGHT + theme.CATEGORY_BAR_HEIGHT)
        self.state.bind(open_category=self._refresh_category_picker)
        self._refresh_category_picker()

        # The email-send bar also floats above everything in `content`,
        # only added while visible.
        self.email_send_bar = EmailSendBar()
        self.email_send_bar.pos_hint = {"x": 0}
        self.email_send_bar.y = 0
        self.state.bind(email_bar_open=self._refresh_email_bar)

        # -- scale `content` to fit whatever window it actually ends up in --
        scaler = Scatter(
            size=(theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT),
            size_hint=(None, None),
            do_translation=False,
            do_rotation=False,
            do_scale=False,
        )
        scaler.add_widget(content)
        Window.bind(size=lambda *_a: self._fit_content_to_window(scaler))
        self._fit_content_to_window(scaler)
        return scaler

    def _fit_content_to_window(self, scaler):
        """Scale+center `scaler` (holding the fixed SCREEN_WIDTH x
        SCREEN_HEIGHT `content`) so it fits entirely inside the current
        window, preserving its aspect ratio (letterboxed if the window's
        aspect ratio doesn't match). On the real kiosk, the window IS
        SCREEN_WIDTH x SCREEN_HEIGHT, so this ends up being a no-op scale
        of 1."""
        scale = min(Window.width / theme.SCREEN_WIDTH, Window.height / theme.SCREEN_HEIGHT)
        scaler.scale = scale
        scaler.pos = (
            (Window.width - theme.SCREEN_WIDTH * scale) / 2,
            (Window.height - theme.SCREEN_HEIGHT * scale) / 2,
        )

    def _update_background_rect(self, instance, _value):
        self._background_rect.pos = instance.pos
        self._background_rect.size = instance.size

    # -- language / translation --------------------------------------------

    def register_i18n(self, widget, text_key, attr="text"):
        """Register a widget so its `attr` (almost always "text") is kept in
        sync with translations.py whenever the language changes. Also sets
        it immediately, so callers don't need to set the text themselves."""
        self.i18n_registry.append((widget, text_key, attr))
        setattr(widget, attr, translations.get_text(self.state.current_language, text_key))

    def refresh_all_text(self, *_args):
        for widget, text_key, attr in self.i18n_registry:
            setattr(widget, attr, translations.get_text(self.state.current_language, text_key))

    # -- screen switching -----------------------------------------------------

    def _refresh_screen(self, *_args):
        screen = self.state.screen
        shown, hidden = (self.compose_screen, self.intro_screen) if screen == "compose" else (
            self.intro_screen,
            self.compose_screen,
        )
        if hidden.parent is not None:
            self.root_layout.remove_widget(hidden)
        if shown.parent is None:
            self.root_layout.add_widget(shown)

    # -- tutorial dropdown ---------------------------------------------------

    def _refresh_tutorial_panel(self, *_args):
        if self.state.tutorial_open:
            if self.tutorial_panel.parent is None:
                self.root_layout.add_widget(self.tutorial_panel)
        elif self.tutorial_panel.parent is not None:
            self.root_layout.remove_widget(self.tutorial_panel)

    # -- category picker -------------------------------------------------------

    def _refresh_category_picker(self, *_args):
        category = self.state.open_category
        if category:
            self.category_picker_panel.show_category(category)
            if self.category_picker_panel.parent is None:
                self.root_layout.add_widget(self.category_picker_panel)
        elif self.category_picker_panel.parent is not None:
            self.root_layout.remove_widget(self.category_picker_panel)

    # -- email send bar ---------------------------------------------------

    def _refresh_email_bar(self, *_args):
        if self.state.email_bar_open:
            # Added to the tree BEFORE show() focuses the email TextInput --
            # focusing it is what triggers Kivy's docked on-screen keyboard
            # (see keyboard_mode in main.py's kiosk Config), and that request
            # needs the widget's get_root_window() to already resolve, which
            # it can't do while still parentless.
            if self.email_send_bar.parent is None:
                self.root_layout.add_widget(self.email_send_bar)
            self.email_send_bar.show()
        elif self.email_send_bar.parent is not None:
            self.root_layout.remove_widget(self.email_send_bar)

    def confirm_send(self, email_address):
        """Called by EmailSendBar once a validated email address is
        confirmed: exports the current canvas as a timestamped PNG, emails
        it to that address, then shows the intro screen again with the
        Nová kompozícia button. Raises email_sender.EmailSendError (which
        EmailSendBar catches and displays) if sending fails -- the bar
        stays open either way, so the composition itself is untouched
        until a send actually succeeds."""
        import datetime

        # Deselecting first hides the selection highlight and the X delete
        # badge on whatever image was selected -- both are drawn as part
        # of that image's own canvas/children, so without this they'd show
        # up in the exported picture too.
        self.state.select_target("canvas")

        os.makedirs(EXPORT_DIR, exist_ok=True)
        filename = "galanda_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        filepath = os.path.join(EXPORT_DIR, filename)
        # export_to_png is called on the canvas widget specifically (not the
        # whole window), so the exported image contains only the picture,
        # not the side panels/bars around it.
        self.state.canvas_area.export_to_png(filepath)

        email_sender.send_image(email_address, filepath)

        self.state.close_send_bar()
        # In case the tutorial dropdown or a category picker was left open
        # behind the email bar -- both float independently of which screen
        # is showing, so they must be closed explicitly or they'd stay
        # stuck open on top of the intro screen we're about to switch to.
        self.state.close_tutorial()
        self.state.close_category_picker()
        self.state.intro_button_key = "new_session_button"
        self.state.screen = "intro"


if __name__ == "__main__":
    GalandaApp().run()
