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

import os
import re

from kivy.app import App
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
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


def _add_space_between(container, widgets):
    """Add `widgets` to `container` (a horizontal BoxLayout) with a flexible
    spacer between each pair -- nothing before the first or after the last.
    Combined with a widget's own width hugging its content (rather than
    filling an equal-width slot), this is what makes the first widget's
    content sit flush against the container's left padding and the last
    widget's flush against its right padding, with the row's `padding`
    setting that shared margin -- while whatever's left over is split evenly
    into the gaps between them."""
    for index, widget in enumerate(widgets):
        if index > 0:
            container.add_widget(Widget(size_hint_x=1))
        container.add_widget(widget)


class _PaddedButton(Button):
    """A Button whose tappable area extends theme.BUTTON_TOUCH_PADDING
    pixels past its visible box on every side. These flat buttons are
    sized to hug just their own text (see _make_button/_make_lang_button),
    which makes for a small, precise tap target -- often sitting right at
    a screen edge, exactly where this kiosk's touchscreen is least
    accurate. Padding the hit area (not the visible size) keeps the look
    unchanged."""

    def collide_point(self, x, y):
        pad = theme.BUTTON_TOUCH_PADDING
        return (
            self.x - pad <= x <= self.right + pad
            and self.y - pad <= y <= self.top + pad
        )


def _make_button(text_key, on_press, color=None):
    """A themed, borderless (no background frame) Button -- just its label
    floating on whatever it's placed on -- whose text is registered for
    translation, so it updates automatically when the language switches."""
    button = _PaddedButton(
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


class _IconButton(ButtonBehavior, FloatLayout):
    """A themed, borderless button like _make_button(), but with an icon to
    the left of its label. Sized to hug the icon+label group exactly
    (size_hint_x=None, width tracks that group's own minimum_width) rather
    than filling whatever slot a parent layout hands it, so a row of these
    can be edge-aligned (see BottomBar) instead of each button's content
    floating centered in its own equal-width share of the row.

    The icon and label are positioned by hand in _relayout() (both centered
    on the button's horizontal axis) rather than by a nested BoxLayout,
    which bottom-aligns children of different heights on its cross axis.

    Dims (via opacity) while disabled, since a custom composite like this
    doesn't get Button's automatic disabled-dimming for free."""

    _ICON_LABEL_SPACING = 8

    def __init__(self, icon_path, text_key, on_press, **kwargs):
        kwargs.setdefault("size_hint", (None, 1))
        super().__init__(**kwargs)
        self.bind(on_press=lambda *_args: on_press())
        self.bind(disabled=self._refresh_disabled_look)

        self.icon = Image(
            source=icon_path,
            size_hint=(None, None),
            size=theme.BUTTON_ICON_SIZE,
            allow_stretch=True,
            keep_ratio=True,
        )
        self.add_widget(self.icon)

        self.label = Label(
            font_size=theme.FONT_SIZE_NORMAL,
            **theme.font_kwargs(),
            color=theme.ACCENT_COLOR,
            size_hint=(None, None),
        )
        self.label.bind(texture_size=self.label.setter("size"))
        App.get_running_app().register_i18n(self.label, text_key)
        self.add_widget(self.label)

        self.bind(pos=self._relayout, height=self._relayout)
        self.icon.bind(size=self._relayout)
        self.label.bind(size=self._relayout)
        self._relayout()

    def _relayout(self, *_args):
        icon, label = self.icon, self.label
        # Hug the icon+label group, so a row of these can be edge-aligned.
        self.width = icon.width + self._ICON_LABEL_SPACING + label.width
        icon.x = self.x
        icon.center_y = self.center_y
        label.x = icon.right + self._ICON_LABEL_SPACING
        label.center_y = self.center_y

    def _refresh_disabled_look(self, _instance, disabled):
        self.opacity = 0.4 if disabled else 1.0


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
        kwargs.setdefault("padding", [theme.SIDE_MARGIN, 8, theme.SIDE_MARGIN, 8])
        kwargs.setdefault("spacing", 8)
        super().__init__(**kwargs)
        _add_flat_background(self, theme.PANEL_BACKGROUND_COLOR)

        state = App.get_running_app().state

        # Sized to hug its own text (rather than a fixed box wider than the
        # word) so "Info" actually sits flush against the bar's left
        # padding -- theme.SIDE_MARGIN from the screen edge -- the same
        # margin used everywhere else, instead of floating in the middle of
        # an oversized button.
        self.tutorial_button = _make_button("tutorial_button", state.toggle_tutorial)
        self.tutorial_button.size_hint_x = None
        self.tutorial_button.bind(texture_size=lambda inst, val: setattr(inst, "width", val[0]))
        self.add_widget(self.tutorial_button)

        self.add_widget(Widget())  # spacer: pushes the language switch to the right

        # Same idea on the right: the row hugs its own content (via
        # minimum_width) instead of a fixed width, so "EN" ends up flush
        # against the bar's right padding -- the same theme.SIDE_MARGIN.
        lang_row = BoxLayout(orientation="horizontal", size_hint=(None, 1), spacing=6)
        lang_row.bind(minimum_width=lang_row.setter("width"))

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
        # language codes, not translated UI text. Width hugs the text
        # itself (via texture_size) rather than a fixed guess, so the
        # lang_row's own minimum_width -- and so the right margin it lines
        # up against -- reflects the actual rendered text.
        button = _PaddedButton(
            text=text,
            font_size=theme.FONT_SIZE_NORMAL,
            **theme.font_kwargs(),
            size_hint=(None, 1),
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            color=theme.TEXT_COLOR,
        )
        button.bind(texture_size=lambda inst, val: setattr(inst, "width", val[0]))
        return button

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
    narrower than the screen by DROPDOWN_SIDE_MARGIN on each side. Its
    height isn't fixed -- it grows to fit however much tutorial_body text
    actually ends up in translations.py (see body_label below), so nothing
    gets clipped no matter how long that text is.

    Swallows any touch that lands within its own bounds (see
    on_touch_down) so the category bar/canvas it's covering can't be
    tapped through it while it's open."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("width", theme.SCREEN_WIDTH - 2 * theme.DROPDOWN_SIDE_MARGIN)
        kwargs.setdefault("pos_hint", {"center_x": 0.5, "top": 1})
        kwargs.setdefault("padding", 16)
        kwargs.setdefault("spacing", 8)
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter("height"))
        _add_flat_background(self, theme.PANEL_BACKGROUND_COLOR)

        with self.canvas.after:
            Color(rgba=theme.DROPDOWN_OUTLINE_COLOR)
            self._outline = Line(width=theme.DROPDOWN_OUTLINE_WIDTH)
        self.bind(pos=self._update_outline, size=self._update_outline)
        self._update_outline()

        self.body_label = Label(
            font_size=theme.FONT_SIZE_NORMAL,
            **theme.font_kwargs(),
            color=theme.TEXT_COLOR,
            halign="left",
            valign="top",
            size_hint_y=None,
        )
        # Constrain wrapping to the label's width only (height=None), then
        # take whatever height that wrapped text naturally needs -- rather
        # than the old size->text_size=self.size, which constrained the
        # text into a box only as tall as the panel's own fixed height
        # allowed, clipping/overflowing it if the text needed more room.
        self.body_label.bind(width=lambda *_a: setattr(self.body_label, "text_size", (self.body_label.width, None)))
        self.body_label.bind(texture_size=lambda *_a: setattr(self.body_label, "height", self.body_label.texture_size[1]))
        App.get_running_app().register_i18n(self.body_label, "tutorial_body")
        self.add_widget(self.body_label)

    def _update_outline(self, *_args):
        self._outline.points = [self.x, self.y, self.right, self.y]

    def on_touch_down(self, touch):
        # Neither label underneath claims touches, so without this, a tap
        # on the dropdown would just fall through to whatever's visually
        # behind it (the category bar, mainly) instead of being swallowed
        # by the dropdown that's covering it.
        handled = super().on_touch_down(touch)
        return handled or self.collide_point(*touch.pos)


# ---------------------------------------------------------------------------
# Category bar: POZADIE / TELO / RUKY / HLAVA / PREDMET
# ---------------------------------------------------------------------------


class CategoryBar(BoxLayout):
    """Row of 5 buttons, one per category. Tapping one opens (or, if it's
    already open, closes) that category's picker panel -- see
    AppState.toggle_category / open_category, and CategoryPickerPanel.

    Each button hugs its own text width and they're spread across the row
    with _add_space_between, so POZADIE sits flush against the left margin
    and PREDMET flush against the right one, matching the top/bottom bars,
    with the other three evenly spaced between."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", theme.CATEGORY_BAR_HEIGHT)
        kwargs.setdefault("padding", [theme.SIDE_MARGIN, 8, theme.SIDE_MARGIN, 8])
        kwargs.setdefault("spacing", 0)
        super().__init__(**kwargs)
        _add_flat_background(self, theme.PANEL_BACKGROUND_COLOR)

        state = App.get_running_app().state
        self._underlines = {}
        buttons = []
        for category in theme.CATEGORIES:
            button = _make_button(f"category_{category}", lambda c=category: state.toggle_category(c))
            button.size_hint_x = None
            button.bind(texture_size=lambda inst, val: setattr(inst, "width", val[0]))
            self._underlines[category] = _add_underline(button, theme.TEXT_COLOR)
            buttons.append(button)
        _add_space_between(self, buttons)

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


class _ScrollArrowButton(ButtonBehavior, Image):
    """The left.png/right.png arrow flanking an open category picker's
    scrolling row -- tapping one nudges the ScrollView by
    theme.SCROLL_STEP."""

    def __init__(self, icon_path, **kwargs):
        kwargs.setdefault("size_hint", (None, 1))
        kwargs.setdefault("width", theme.SCROLL_ARROW_SIZE[0])
        kwargs.setdefault("allow_stretch", True)
        kwargs.setdefault("keep_ratio", True)
        super().__init__(source=icon_path, **kwargs)


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

        # Shown once the category has PNGs: left.png/right.png arrows
        # flanking a plain left-to-right scrolling row. In practice a
        # populated category has enough thumbnails to overflow the panel
        # width anyway, so scrolling (not centering) is what actually
        # matters here.
        self._scroll = ScrollView(size_hint=(1, 1), do_scroll_x=True, do_scroll_y=False)
        self._row = BoxLayout(orientation="horizontal", spacing=16, padding=16, size_hint_x=None)
        self._row.bind(minimum_width=self._row.setter("width"))
        self._scroll.add_widget(self._row)

        self._scroll_row = BoxLayout(orientation="horizontal", size_hint=(1, 1), spacing=8, padding=(8, 0))
        left_arrow = _ScrollArrowButton(os.path.join(theme.ICON_DIR, "left.png"))
        left_arrow.bind(on_press=lambda *_a: self._scroll_by(-theme.SCROLL_STEP))
        right_arrow = _ScrollArrowButton(os.path.join(theme.ICON_DIR, "right.png"))
        right_arrow.bind(on_press=lambda *_a: self._scroll_by(theme.SCROLL_STEP))
        self._scroll_row.add_widget(left_arrow)
        self._scroll_row.add_widget(self._scroll)
        self._scroll_row.add_widget(right_arrow)

    def _scroll_by(self, delta):
        self._scroll.scroll_x = max(0.0, min(1.0, self._scroll.scroll_x + delta))

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
        self.add_widget(self._scroll_row)


# ---------------------------------------------------------------------------
# Bottom bar: undo / new composition / send
# ---------------------------------------------------------------------------


class BottomBar(BoxLayout):
    """Bottom strip, left to right: Späť (undo last selection), Nová
    kompozícia (clear everything and start over), Poslať (opens
    EmailSendBar).

    Each button hugs its own icon+label width and they're spread across the
    row with _add_space_between, so Späť sits flush against the left margin
    and Poslať flush against the right one, matching the top/category bars,
    with Nová kompozícia evenly spaced between."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", theme.BOTTOM_BAR_HEIGHT)
        kwargs.setdefault("padding", [theme.SIDE_MARGIN, 8, theme.SIDE_MARGIN, 8])
        kwargs.setdefault("spacing", 0)
        super().__init__(**kwargs)
        _add_flat_background(self, theme.PANEL_BACKGROUND_COLOR)

        app = App.get_running_app()

        self.undo_button = _IconButton(
            os.path.join(theme.ICON_DIR, "back.png"), "undo_button", app.state.undo
        )

        self.new_session_button = _IconButton(
            os.path.join(theme.ICON_DIR, "new.png"), "new_session_button", app.state.new_session
        )

        self.send_button = _IconButton(
            os.path.join(theme.ICON_DIR, "send.png"), "export_button", app.state.open_send_bar
        )

        _add_space_between(self, [self.undo_button, self.new_session_button, self.send_button])

        app.state.bind(undo_available=self._refresh_undo_button)
        self._refresh_undo_button()

    def _refresh_undo_button(self, *_args):
        self.undo_button.disabled = not App.get_running_app().state.undo_available


# ---------------------------------------------------------------------------
# On-screen keyboard for the email field
# ---------------------------------------------------------------------------

# Only what an email address needs -- lowercase letters, digits, and the
# handful of symbols that show up in one (@ . - _). No shift/caps: emails
# aren't case-sensitive in practice and this keeps the layout simple.
_KEYBOARD_ROWS = ("1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm@.-_")


class _SimpleKeyboard(BoxLayout):
    """A minimal on-screen keyboard built entirely out of this app's own
    widgets, for the email TextInput below.

    Kivy's built-in docked keyboard (Window.request_keyboard, see
    keyboard_mode in main.py) turned out not to render at all on this
    kiosk's Wayland/labwc + portrait setup -- the request succeeds at the
    API level (a real Keyboard object comes back) but nothing ever
    appears on screen, and that's not something fixable from here without
    being able to see the actual display. Building the keyboard as normal
    app widgets instead means it goes through the same touch/rendering
    path already proven to work on this hardware for everything else."""

    def __init__(self, target, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", 6)
        super().__init__(**kwargs)
        self._target = target

        for row in _KEYBOARD_ROWS:
            row_box = BoxLayout(orientation="horizontal", spacing=6)
            for char in row:
                row_box.add_widget(self._make_key(char, self._insert))
            self.add_widget(row_box)

        backspace_row = BoxLayout(orientation="horizontal", spacing=6)
        backspace_row.add_widget(self._make_key("<-", self._backspace))
        self.add_widget(backspace_row)

    @staticmethod
    def _make_key(label, on_press):
        button = _PaddedButton(
            text=label,
            font_size=theme.FONT_SIZE_NORMAL,
            **theme.font_kwargs(),
            background_normal="",
            background_down="",
            background_color=theme.KEYBOARD_KEY_COLOR,
            color=theme.TEXT_COLOR,
        )
        button.bind(on_press=lambda *_a: on_press(label))
        return button

    def _insert(self, char):
        self._target.text += char

    def _backspace(self, _label):
        self._target.text = self._target.text[:-1]


# ---------------------------------------------------------------------------
# Email send bar: shown when POSLAŤ is tapped
# ---------------------------------------------------------------------------


class EmailSendBar(BoxLayout):
    """Floating bar shown when POSLAŤ is tapped: a label, an email
    TextInput, an on-screen keyboard (_SimpleKeyboard -- see its own
    docstring for why this isn't Kivy's built-in one), an inline error
    message, and Cancel/Poslať buttons.

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
            # This kiosk provides its own on-screen keyboard (see
            # _SimpleKeyboard above) rather than Kivy's built-in one --
            # "managed" stops focusing this field from also trying (and
            # failing) to pop up Kivy's own docked keyboard.
            keyboard_mode="managed",
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

        self.add_widget(_SimpleKeyboard(self._email_input, size_hint_y=1))

        buttons_row = BoxLayout(orientation="horizontal", spacing=8, size_hint_y=None, height=70)
        buttons_row.add_widget(_make_button("email_bar_cancel", self._cancel))
        buttons_row.add_widget(_make_button("export_button", self._confirm))
        self.add_widget(buttons_row)

    def show(self):
        """Called every time the bar is opened, to reset it to a blank
        state (rather than showing the last attempt's leftover text)."""
        self._email_input.text = ""
        self._error_label.text = ""

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
