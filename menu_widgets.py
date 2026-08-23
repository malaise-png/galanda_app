# menu_widgets.py
#
# The "chrome" widgets around the canvas:
#   TopBar              - Info/Tutorial button + EN/SK language switch button.
#   TutorialPanel        - the floating text panel the Tutorial button shows/hides.
#   CategoryBar          - row of 5 buttons: POZADIE / TELO / RUKY / HLAVA / PREDMET.
#   CategoryPickerPanel   - the floating horizontal-scrolling picker of PNG
#                          options for whichever category is currently open.
#   BottomBar            - Späť (undo) / Nová kompozícia (new session) / Poslať (send).
#   EmailSendBar          - the floating email-entry bar POSLAŤ opens.
#
# All buttons in this file are flat text with no background frame -- just
# the bar strip behind them keeps its background color.
#
# All user-visible text is looked up from translations.py via
# App.get_running_app().register_i18n(widget, key) -- see main.py for how
# that registry is used to re-translate everything when the language
# switches. Widgets in this file never talk to each other directly; they
# only call methods on App.get_running_app().state (see app_state.py).

import re

from kivy.app import App
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import email_sender
import image_assets
import theme
import translations

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _add_flat_background(widget, color):
    """Give a plain Widget/Layout a solid background color that keeps
    following the widget if it's ever moved or resized."""
    with widget.canvas.before:
        Color(rgba=color)
        rect = Rectangle(pos=widget.pos, size=widget.size)

    def _update(*_args):
        rect.pos = widget.pos
        rect.size = widget.size

    widget.bind(pos=_update, size=_update)


def _add_underline(widget, color):
    """Add a thin horizontal line along the bottom of `widget`, initially
    invisible. Returns a setter(visible: bool) to show/hide it -- used to
    mark whichever option is currently "chosen" (the open category, the
    active language), since flat borderless buttons have no other visual
    way to show which one is selected."""
    with widget.canvas.after:
        line_color = Color(rgba=(*color[:3], 0))
        line = Line(width=theme.UNDERLINE_WIDTH)

    def _update(*_args):
        line.points = [widget.x, widget.y, widget.right, widget.y]

    widget.bind(pos=_update, size=_update)
    _update()

    def _set_visible(visible):
        line_color.a = color[3] if visible else 0

    return _set_visible


def _make_button(text_key, on_press, color=None):
    """A themed, borderless (no background frame) Button -- just its label
    floating on whatever it's placed on -- whose text is registered for
    translation, so it updates automatically when the language switches."""
    button = Button(
        font_size=theme.FONT_SIZE_NORMAL,
        **theme.font_kwargs(),
        background_normal="",
        background_down="",
        background_color=(0, 0, 0, 0),
        color=color or theme.ACCENT_COLOR,
    )
    button.bind(on_press=lambda *_args: on_press())
    App.get_running_app().register_i18n(button, text_key)
    return button


# ---------------------------------------------------------------------------
# Top bar: info/tutorial + language switch
# ---------------------------------------------------------------------------


class TopBar(BoxLayout):
    """Top strip: an Info/Tutorial button in the left corner (tapping it
    toggles AppState.tutorial_open -- see TutorialPanel, which floats over
    the app when open), and an "SK/EN" language switch in the right
    corner: both language codes are always shown, and whichever one is
    currently active is underlined. Tapping a code switches to it directly
    (there's no toggle/flip -- tapping the already-active one does
    nothing)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", theme.TOP_BAR_HEIGHT)
        kwargs.setdefault("padding", 8)
        kwargs.setdefault("spacing", 8)
        super().__init__(**kwargs)
        _add_flat_background(self, theme.PANEL_BACKGROUND_COLOR)

        state = App.get_running_app().state

        self.tutorial_button = _make_button("tutorial_button", state.toggle_tutorial)
        self.tutorial_button.size_hint_x = None
        self.tutorial_button.width = 160
        self.add_widget(self.tutorial_button)

        self.add_widget(Widget())  # spacer: pushes the language switch to the right

        lang_row = BoxLayout(orientation="horizontal", size_hint=(None, 1), width=150, spacing=6)

        self._sk_button = self._make_lang_button("SK")
        self._sk_button.bind(on_press=lambda *_a: self._set_language("sk"))
        self._sk_underline = _add_underline(self._sk_button, theme.TEXT_COLOR)
        lang_row.add_widget(self._sk_button)

        separator = Label(
            text="/",
            font_size=theme.FONT_SIZE_NORMAL,
            **theme.font_kwargs(),
            color=theme.TEXT_COLOR,
            size_hint=(None, 1),
            width=14,
        )
        lang_row.add_widget(separator)

        self._en_button = self._make_lang_button("EN")
        self._en_button.bind(on_press=lambda *_a: self._set_language("en"))
        self._en_underline = _add_underline(self._en_button, theme.TEXT_COLOR)
        lang_row.add_widget(self._en_button)

        self.add_widget(lang_row)

        state.bind(current_language=self._refresh_language)
        self._refresh_language()

    @staticmethod
    def _make_lang_button(text):
        # Not built with _make_button()/register_i18n() -- "SK"/"EN" are
        # language codes, not translated UI text.
        return Button(
            text=text,
            font_size=theme.FONT_SIZE_NORMAL,
            **theme.font_kwargs(),
            size_hint=(None, 1),
            width=60,
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            color=theme.TEXT_COLOR,
        )

    def _set_language(self, language):
        App.get_running_app().state.current_language = language

    def _refresh_language(self, *_args):
        current = App.get_running_app().state.current_language
        self._sk_underline(current == "sk")
        self._en_underline(current == "en")


class TutorialPanel(BoxLayout):
    """The info/tutorial dropdown. main.py adds/removes this widget
    directly on the root layout to show/hide it (see
    GalandaApp.toggle_tutorial), floating flush against the top of the
    screen and overlaying the top bar/category bar/canvas beneath it,
    rather than pushing them down -- so it doesn't block touches to the
    canvas underneath while it's supposed to be invisible.

    A plain white line along its bottom edge is its only border, and it's
    narrower than the screen by DROPDOWN_SIDE_MARGIN on each side."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("width", theme.SCREEN_WIDTH - 2 * theme.DROPDOWN_SIDE_MARGIN)
        kwargs.setdefault("height", theme.TUTORIAL_PANEL_HEIGHT)
        kwargs.setdefault("pos_hint", {"center_x": 0.5, "top": 1})
        kwargs.setdefault("padding", 16)
        kwargs.setdefault("spacing", 8)
        super().__init__(**kwargs)
        _add_flat_background(self, theme.PANEL_BACKGROUND_COLOR)

        with self.canvas.after:
            Color(rgba=theme.DROPDOWN_OUTLINE_COLOR)
            self._outline = Line(width=theme.DROPDOWN_OUTLINE_WIDTH)
        self.bind(pos=self._update_outline, size=self._update_outline)
        self._update_outline()

        self.title_label = Label(
            font_size=theme.FONT_SIZE_LARGE,
            **theme.font_kwargs(),
            color=theme.ACCENT_COLOR,
            size_hint_y=None,
            height=40,
            halign="left",
            valign="middle",
        )
        self.title_label.bind(size=lambda *_a: setattr(self.title_label, "text_size", self.title_label.size))
        App.get_running_app().register_i18n(self.title_label, "tutorial_title")
        self.add_widget(self.title_label)

        self.body_label = Label(
            font_size=theme.FONT_SIZE_NORMAL,
            **theme.font_kwargs(),
            color=theme.TEXT_COLOR,
            halign="left",
            valign="top",
        )
        self.body_label.bind(size=lambda *_a: setattr(self.body_label, "text_size", self.body_label.size))
        App.get_running_app().register_i18n(self.body_label, "tutorial_body")
        self.add_widget(self.body_label)

    def _update_outline(self, *_args):
        self._outline.points = [self.x, self.y, self.right, self.y]


# ---------------------------------------------------------------------------
# Category bar: POZADIE / TELO / RUKY / HLAVA / PREDMET
# ---------------------------------------------------------------------------


class CategoryBar(BoxLayout):
    """Row of 5 buttons, one per category. Tapping one opens (or, if it's
    already open, closes) that category's picker panel -- see
    AppState.toggle_category / open_category, and CategoryPickerPanel."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", theme.CATEGORY_BAR_HEIGHT)
        kwargs.setdefault("padding", 8)
        kwargs.setdefault("spacing", 6)
        super().__init__(**kwargs)
        _add_flat_background(self, theme.PANEL_BACKGROUND_COLOR)

        state = App.get_running_app().state
        self._underlines = {}
        for category in theme.CATEGORIES:
            button = _make_button(f"category_{category}", lambda c=category: state.toggle_category(c))
            self._underlines[category] = _add_underline(button, theme.TEXT_COLOR)
            self.add_widget(button)

        state.bind(open_category=self._refresh_highlight)
        self._refresh_highlight()

    def _refresh_highlight(self, *_args):
        open_category = App.get_running_app().state.open_category
        for category, set_underline in self._underlines.items():
            set_underline(category == open_category)


# ---------------------------------------------------------------------------
# Category picker: horizontal scroll of PNG options for the open category
# ---------------------------------------------------------------------------


class AssetThumbnailButton(ButtonBehavior, Image):
    """One tappable PNG preview inside an open category picker."""

    def __init__(self, path, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", theme.CATEGORY_THUMBNAIL_SIZE)
        kwargs.setdefault("allow_stretch", True)
        kwargs.setdefault("keep_ratio", True)
        super().__init__(source=path, **kwargs)


class CategoryPickerPanel(BoxLayout):
    """Floating horizontal scroller shown right under the category bar
    while a category is open. main.py adds/removes this from the root
    layout, and calls show_category() to (re)build its thumbnails, each
    time AppState.open_category changes."""

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", theme.CATEGORY_PICKER_HEIGHT)
        super().__init__(**kwargs)
        _add_flat_background(self, theme.PANEL_BACKGROUND_COLOR)

        # Shown when the category has no PNGs yet: a plain full-panel
        # AnchorLayout, which centers its one child exactly -- no fighting
        # with ScrollView viewport/content-width quirks.
        self._empty_label = Label(
            font_size=theme.FONT_SIZE_NORMAL,
            **theme.font_kwargs(),
            color=theme.TEXT_COLOR,
            halign="center",
            valign="middle",
        )
        # text_size must match the label's own size for halign/valign to
        # take effect at all (otherwise Kivy just centers the raw texture
        # on self.center, which happens to look right but isn't the same
        # thing) -- explicit here rather than relying on that default.
        self._empty_label.bind(size=lambda *_a: setattr(self._empty_label, "text_size", self._empty_label.size))
        App.get_running_app().register_i18n(self._empty_label, "category_empty")
        self._empty_container = AnchorLayout(anchor_x="center", anchor_y="center", size_hint=(1, 1))
        self._empty_container.add_widget(self._empty_label)

        # Shown once the category has PNGs: a plain left-to-right
        # scrolling row. In practice a populated category has enough
        # thumbnails to overflow the panel width anyway, so scrolling
        # (not centering) is what actually matters here.
        self._scroll = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=False)
        self._row = BoxLayout(orientation="horizontal", spacing=16, padding=16, size_hint_x=None)
        self._row.bind(minimum_width=self._row.setter("width"))
        self._scroll.add_widget(self._row)

    def show_category(self, category):
        state = App.get_running_app().state
        assets = image_assets.get_category_assets(state.assets_dir, category)

        self.clear_widgets()
        if not assets:
            self.add_widget(self._empty_container)
            return

        self._row.clear_widgets()
        for _name, path in assets:
            thumb = AssetThumbnailButton(path=path)
            thumb.bind(
                on_press=lambda *_args, p=path: App.get_running_app().state.select_category_option(category, p)
            )
            self._row.add_widget(thumb)
        self.add_widget(self._scroll)


# ---------------------------------------------------------------------------
# Bottom bar: undo / new composition / send
# ---------------------------------------------------------------------------


class BottomBar(BoxLayout):
    """Bottom strip, left to right: Späť (undo last selection), Nová
    kompozícia (clear everything and start over), Poslať (opens
    EmailSendBar)."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", theme.BOTTOM_BAR_HEIGHT)
        kwargs.setdefault("padding", 8)
        kwargs.setdefault("spacing", 8)
        super().__init__(**kwargs)
        _add_flat_background(self, theme.PANEL_BACKGROUND_COLOR)

        app = App.get_running_app()

        self.undo_button = _make_button("undo_button", app.state.undo)
        self.add_widget(self.undo_button)

        self.new_session_button = _make_button("new_session_button", app.state.new_session)
        self.add_widget(self.new_session_button)

        self.send_button = _make_button("export_button", app.state.open_send_bar)
        self.add_widget(self.send_button)

        app.state.bind(undo_available=self._refresh_undo_button)
        self._refresh_undo_button()

    def _refresh_undo_button(self, *_args):
        self.undo_button.disabled = not App.get_running_app().state.undo_available


# ---------------------------------------------------------------------------
# Email send bar: shown when POSLAŤ is tapped
# ---------------------------------------------------------------------------


class EmailSendBar(BoxLayout):
    """Floating bar shown when POSLAŤ is tapped: a label, an email
    TextInput (Kivy's own on-screen keyboard docks under the window
    automatically when focused, on the kiosk -- see keyboard_mode in
    main.py), an inline error message, and Cancel/Poslať buttons.

    main.py adds/removes this from the root layout and calls show() to
    reset it, each time AppState.email_bar_open changes."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", theme.EMAIL_BAR_HEIGHT)
        kwargs.setdefault("padding", 24)
        kwargs.setdefault("spacing", 16)
        super().__init__(**kwargs)
        _add_flat_background(self, theme.PANEL_BACKGROUND_COLOR)

        self._label = Label(
            font_size=theme.FONT_SIZE_NORMAL,
            **theme.font_kwargs(),
            color=theme.TEXT_COLOR,
            size_hint_y=None,
            height=36,
        )
        App.get_running_app().register_i18n(self._label, "email_bar_label")
        self.add_widget(self._label)

        self._email_input = TextInput(
            multiline=False,
            font_size=theme.FONT_SIZE_NORMAL,
            size_hint_y=None,
            height=72,
            write_tab=False,
        )
        self.add_widget(self._email_input)

        self._error_label = Label(
            font_size=theme.FONT_SIZE_SMALL,
            **theme.font_kwargs(),
            color=(0.9, 0.3, 0.3, 1),
            size_hint_y=None,
            height=28,
        )
        self.add_widget(self._error_label)

        self.add_widget(Widget())  # spacer

        buttons_row = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=70)
        buttons_row.add_widget(_make_button("email_bar_cancel", self._cancel))
        buttons_row.add_widget(_make_button("export_button", self._confirm))
        self.add_widget(buttons_row)

    def show(self):
        """Called every time the bar is opened, to reset it to a blank
        state (rather than showing the last attempt's leftover text)."""
        self._email_input.text = ""
        self._error_label.text = ""
        self._email_input.focus = True

    def _cancel(self):
        App.get_running_app().state.close_send_bar()

    def _confirm(self):
        address = self._email_input.text.strip()
        if not _EMAIL_RE.match(address):
            self._set_error("email_invalid")
            return
        try:
            App.get_running_app().confirm_send(address)
        except email_sender.EmailSendError as error:
            self._error_label.text = str(error)

    def _set_error(self, text_key):
        state = App.get_running_app().state
        self._error_label.text = translations.get_text(state.current_language, text_key)
