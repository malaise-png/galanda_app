# translations.py
#
# Every piece of text shown in the app lives in this one dictionary, in both
# English ("en") and Slovak ("sk"). If you want to change wording, or write
# the real tutorial text (the current tutorial text below is just a
# placeholder), this is the only file you need to edit.
#
# How it's used: each widget that shows text registers itself with a "key"
# (see menu_widgets.py). When the language is switched, every registered
# widget looks up its key in TEXT[current_language] and updates itself.

TEXT = {
    "en": {
        "tutorial_button": "INFO",
        # Placeholder tutorial body -- replace this with the real instructions
        # whenever they're ready. Use \n\n for a paragraph break.
        "tutorial_body": (
            "Hi, welcome, \n\n"
            "Create your own artwork inspired by the paintings of Mikuláš Galanda. "
            "First, choose a background, and then gradually add the body, arms, "
            "head, eyes, or various objects.You can move, rotate, "
            "and arrange the individual parts however your imagination leads you. \n\n"
            "When your artwork is finished, you can send it to yourself "
            "and save it as a keepsake. \n\n"
        ),
        "category_pozadie": "CANVAS",
        "category_telo": "BODY",
        "category_ruky": "HANDS",
        "category_hlava": "HEAD",
        "category_predmet": "ITEM",
        "category_empty": "No images yet",
        "undo_button": "BACK",
        "new_session_button": "NEW COMPOSITION",
        "sent_success": "AWESOME, SENT!",
        "export_button": "SEND",
        "start_button": "START",
        "start_image_missing": "Add a start image",
        "aftersent_image_missing": "Add an after-sent image",
        "email_bar_label": "ENTER YOUR EMAIL ADDRESS:",
        "email_bar_cancel": "CANCEL",
        "email_invalid": "PLEASE ENTER A VALID EMAIL ADRESS",
    },
    "sk": {
        "tutorial_button": "INFO",
        # Placeholder text -- rovnaký text ako v angličtine, len preložený.
        # Nahraď skutočným návodom, keď bude pripravený.
        "tutorial_body": (
            "Ahoj, vitaj, \n\n"
            "Vytvor si vlastné dielo inšpirované obrazmi Mikuláša Galandu. "
            "Najskôr si vyber pozadie a potom postupne pridávaj telo, ruky, "
            "hlavu, oči alebo rôzne predmety. Jednotlivé časti môžeš presúvať, "
            "otáčať a skladať podľa vlastnej fantázie. \n\n"
            "Keď bude tvoje dielo hotové, môžeš si ho poslať a odložiť na pamiatku. \n\n"
        ),
        "category_pozadie": "POZADIE",
        "category_telo": "TELO",
        "category_ruky": "RUKY",
        "category_hlava": "HLAVA",
        "category_predmet": "PREDMET",
        "category_empty": "Zatiaľ žiadne obrázky",
        "undo_button": "SPÄŤ",
        "new_session_button": "NOVÁ KOMPOZÍCIA",
        "sent_success": "SUPER, POSLANÉ!",
        "export_button": "POSLAŤ",
        "start_button": "ŠTART",
        "start_image_missing": "Pridaj úvodný obrázok",
        "aftersent_image_missing": "Pridaj obrázok po odoslaní",
        "email_bar_label": "ZADAJ SVOJU EMAILOVÚ ADRESU:",
        "email_bar_cancel": "ZRUŠIŤ",
        "email_invalid": "ZADAJ PLATNÚ EMAILOVÚ ADRESU",
    },
}


def get_text(language, key):
    """Look up TEXT[language][key], falling back to the key itself if it's
    missing (so a typo or a not-yet-translated key shows up as visibly wrong
    text instead of crashing the app)."""
    return TEXT.get(language, {}).get(key, key)
