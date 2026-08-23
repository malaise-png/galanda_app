# app_state.py
#
# AppState is the single "source of truth" for everything that changes while
# the app is running: which language is active, which category picker (if
# any) is open, what's currently selected on the canvas, the undo history,
# and every image currently placed.
#
# The rule followed everywhere else in the app: widgets never reach into
# each other directly to change things. A button calls a method here (e.g.
# app.state.new_session()), and this file is the only place that needs to
# know how selection, categories, and undo fit together. That keeps every
# individual widget file simple, since it only has to know how to call
# AppState, not how the whole app works.

from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, OptionProperty, StringProperty

import theme


class AppState(EventDispatcher):

    current_language = OptionProperty("sk", options=["en", "sk"])

    # "intro"   -- the start/thank-you screen (image + one big text button).
    # "compose" -- the normal top bar / category bar / canvas / bottom bar UI.
    screen = OptionProperty("intro", options=["intro", "compose"])

    # Whether the info/tutorial dropdown (pushes the bars below it down) is
    # open -- see TopBar's info button and TutorialPanel in menu_widgets.py.
    tutorial_open = BooleanProperty(False)

    # Which translation key the intro screen's button shows: "start_button"
    # on first launch, switched to "new_session_button" once the user has
    # sent a composition (see main.py's confirm_send()).
    intro_button_key = StringProperty("start_button")

    # Whether the floating email-entry bar (opened by POSLAŤ) is showing.
    email_bar_open = BooleanProperty(False)

    # Which category's picker panel is currently open ("" = none open).
    open_category = StringProperty("")

    canvas_color = ListProperty(list(theme.DEFAULT_CANVAS_COLOR))

    # Either the string "canvas", or a DraggableImage widget instance.
    selected_target = ObjectProperty("canvas")

    # True whenever there's at least one action on the undo stack, i.e.
    # whenever the Späť button should be enabled.
    undo_available = BooleanProperty(False)

    def __init__(self, assets_dir, **kwargs):
        super().__init__(**kwargs)
        self.assets_dir = assets_dir
        # Set by main.py immediately after the CanvasArea widget is built,
        # so the methods below can add/remove image widgets on it.
        self.canvas_area = None
        # One entry per undoable action: a zero-arg callable that reverts
        # it. Not a Kivy property -- nothing needs to react to its
        # contents, only to whether it's empty (see undo_available).
        self._undo_stack = []
        # category -> currently-placed DraggableImage, for the single-slot
        # categories (pozadie is handled separately below since it's a
        # whole-canvas background image, not a DraggableImage; telo is the
        # only single-slot DraggableImage category).
        self._slot_widgets = {}
        self._background_asset = None
        # category -> list of DraggableImage, for theme.MULTI_INSTANCE_CATEGORIES
        # (ruky/hlava/predmet) -- picking an option in these ADDS a new
        # instance (up to theme.MAX_INSTANCES_PER_CATEGORY) instead of
        # replacing what's there.
        self._multi_instances = {category: [] for category in theme.MULTI_INSTANCE_CATEGORIES}

    # -- selection -----------------------------------------------------------

    def select_target(self, target):
        """Select either "canvas" or a DraggableImage as the thing that's
        currently highlighted. Also updates the selection highlight on the
        previously/newly selected image, if any."""
        previous = self.selected_target
        if previous != "canvas":
            previous.selected = False
        self.selected_target = target
        if target != "canvas":
            target.selected = True

    # -- screen / email bar ----------------------------------------------------

    def start_composition(self):
        """Called by the intro screen's button -- START on first launch, or
        Nová kompozícia after a sent composition. Always resets to a blank
        canvas before switching to the compose screen."""
        self.new_session()
        self.screen = "compose"

    def open_send_bar(self):
        self.email_bar_open = True

    def close_send_bar(self):
        self.email_bar_open = False

    # -- tutorial dropdown ---------------------------------------------------

    def toggle_tutorial(self):
        self.tutorial_open = not self.tutorial_open

    def close_tutorial(self):
        self.tutorial_open = False

    # -- category picker -------------------------------------------------------

    def toggle_category(self, category):
        """Called when a category button (POZADIE/TELO/RUKY/HLAVA/PREDMET)
        is tapped. Opens its picker, or closes it if it's already open. Can
        be open at the same time as the tutorial dropdown -- they stack in
        a fixed order (dropdown, then category picker, then canvas), each
        pushing what's below it further down; see main.py."""
        self.open_category = "" if self.open_category == category else category

    def close_category_picker(self):
        self.open_category = ""

    def select_category_option(self, category, asset_path):
        """Called when the user taps a thumbnail inside an open category
        picker. Categories in theme.MULTI_INSTANCE_CATEGORIES (ruky/hlava/
        predmet) add a new instance every time, up to
        theme.MAX_INSTANCES_PER_CATEGORY; every other category (pozadie,
        telo) has a single slot and picking a new option swaps it out for
        the previous one."""
        if category == "pozadie":
            self._select_background(asset_path)
        elif category in theme.MULTI_INSTANCE_CATEGORIES:
            self._add_multi_instance(category, asset_path)
        else:
            self._select_slot(category, asset_path)
        self.close_category_picker()

    # -- undo --------------------------------------------------------------

    def _push_undo(self, restore_fn):
        self._undo_stack.append(restore_fn)
        self.undo_available = True

    def undo(self):
        """Revert the most recent category selection (background swap,
        body-part swap, or item added). Does nothing if there's nothing to
        undo."""
        if not self._undo_stack:
            return
        restore_fn = self._undo_stack.pop()
        restore_fn()
        self.undo_available = bool(self._undo_stack)

    def _select_background(self, asset_path):
        previous = self._background_asset
        self.canvas_area.set_background_image(asset_path)
        self._background_asset = asset_path

        def _undo():
            self.canvas_area.set_background_image(previous)
            self._background_asset = previous

        self._push_undo(_undo)

    def _select_slot(self, category, asset_path):
        from canvas_widgets import DraggableImage

        previous_widget = self._slot_widgets.get(category)

        new_widget = DraggableImage(asset_path)
        new_widget.center = self.canvas_area.center
        self.canvas_area.add_widget(new_widget)
        if previous_widget is not None:
            self.canvas_area.remove_widget(previous_widget)
        self._slot_widgets[category] = new_widget
        self.select_target(new_widget)

        def _undo():
            self.canvas_area.remove_widget(new_widget)
            if previous_widget is not None:
                self.canvas_area.add_widget(previous_widget)
            self._slot_widgets[category] = previous_widget
            self.select_target(previous_widget if previous_widget is not None else "canvas")

        self._push_undo(_undo)

    def _add_multi_instance(self, category, asset_path):
        from canvas_widgets import DraggableImage

        instances = self._multi_instances[category]
        if len(instances) >= theme.MAX_INSTANCES_PER_CATEGORY:
            # Already at the cap for this category -- ignore the tap
            # rather than silently replacing or deleting something the
            # user already placed. The X badge on a selected image is how
            # they free up a slot (see delete_selected()).
            return

        new_widget = DraggableImage(asset_path)
        new_widget.center = self.canvas_area.center
        self.canvas_area.add_widget(new_widget)
        instances.append(new_widget)
        self.select_target(new_widget)

        def _undo():
            self.canvas_area.remove_widget(new_widget)
            instances.remove(new_widget)
            self.select_target("canvas")

        self._push_undo(_undo)

    # -- delete ------------------------------------------------------------

    def delete_selected(self):
        """Called from the X badge on a selected DraggableImage. Removes
        it from the canvas and whichever bookkeeping (a single slot, or a
        multi-instance category's list) it belongs to. Does nothing if
        "canvas" itself is selected -- there's nothing to delete."""
        target = self.selected_target
        if target == "canvas":
            return

        for category, instances in self._multi_instances.items():
            if target in instances:
                self._delete_multi_instance(category, target)
                return

        for category, widget in self._slot_widgets.items():
            if widget is target:
                self._delete_slot(category, target)
                return

    def _delete_multi_instance(self, category, widget):
        instances = self._multi_instances[category]
        self.canvas_area.remove_widget(widget)
        instances.remove(widget)
        self.select_target("canvas")

        def _undo():
            self.canvas_area.add_widget(widget)
            instances.append(widget)
            self.select_target(widget)

        self._push_undo(_undo)

    def _delete_slot(self, category, widget):
        self.canvas_area.remove_widget(widget)
        self._slot_widgets[category] = None
        self.select_target("canvas")

        def _undo():
            self.canvas_area.add_widget(widget)
            self._slot_widgets[category] = widget
            self.select_target(widget)

        self._push_undo(_undo)

    # -- new session / export -------------------------------------------------

    def new_session(self):
        """Clears the canvas back to its starting state: no background
        image, no body parts, no items, canvas selected, undo history
        cleared, email bar closed."""
        for widget in list(self._slot_widgets.values()):
            if widget is not None:
                self.canvas_area.remove_widget(widget)
        self._slot_widgets = {}

        for instances in self._multi_instances.values():
            for widget in list(instances):
                self.canvas_area.remove_widget(widget)
        self._multi_instances = {category: [] for category in theme.MULTI_INSTANCE_CATEGORIES}

        self.canvas_area.set_background_image(None)
        self._background_asset = None
        self.canvas_color = list(theme.DEFAULT_CANVAS_COLOR)

        self._undo_stack = []
        self.undo_available = False
        self.open_category = ""
        self.email_bar_open = False
        self.tutorial_open = False
        self.select_target("canvas")
