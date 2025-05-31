
from copy import deepcopy
from typing import TYPE_CHECKING

from gi.repository import GLib, GObject, Gtk, Pango

from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.lib.attrtype import AttributeType
from gramps.gen.lib.eventtype import EventType
from gramps.gen.utils.keyword import (
    get_keywords,
    get_translation_from_keyword,
)
from gramps.gui.widgets.monitoredwidgets import MonitoredDataType

from family_tree_view_utils import get_gettext
if TYPE_CHECKING:
    from family_tree_view_config_provider import FamilyTreeViewConfigProvider


_ = get_gettext()

IMAGE_PARAMS = {
    "max_height": 80,
    "max_width": 80,
    "fallback_avatar": True,
    "resolution": "thumbnail_normal",
    "filter": "none",
    "media_tag_sel_type": "starts_with",
    "media_tag_sel": "",
}

EVENT_PARAMS = {
    "event_type_visualization": "symbol",
    "date": True,
    "date_only_year": False,
    "date_compact": False,
    "place": False,
    "description": False,
    "tags": False,
    "tag_visualization": "text_colors_counted"
}

BIRTH_DEATH_PARAMS = dict(
    EVENT_PARAMS,
    **{
        "date_only_year": True,
        "date_compact": True,
        "event_type_visualization": "symbol_only_if_empty"
    }
) # No full dates for birth and death as they wouldn't fit.

BOX_ITEMS = {
    "person": [
        ("gutter", _("Gutter"), _("Space between other elements of specified size"), {"size": 5}),
        ("image", _("Image"), _("Image associated with the person"), {**IMAGE_PARAMS}), # TODO maybe move image options here? # TODO once available: ref_type_sel, ref_tag_sel
        ("name", _("Name"), _("The preferred name of the person"), {"lines": 2}),
        ("alt_name", _("Alternative name"), _("The first alternative name of the person"), {"lines": 2}),
        ("birth_or_fallback", _("Birth or fallback"), _("Different information of birth or fallback"), {"lines": 1, **EVENT_PARAMS}),
        ("death_or_fallback", _("Death or fallback"), _("Different information of death or fallback"), {"lines": 1, **EVENT_PARAMS}),
        ("birth_death_or_fallbacks", _("Birth and death or fallbacks"), _("Different information of birth and death or fallbacks"), {"lines": 1, **BIRTH_DEATH_PARAMS}),
        ("event", _("Event"), _("Different information of the first event of the specified type"), {"event_type": "Birth", "lines": 1, "index": 0, **EVENT_PARAMS}),
        ("relationship", _("Relationship"), _("Relationship to the specified person"), {"rel_base": "active", "lines": 1}),
        ("attribute", _("Attribute"), _("The value of the attribute of the specified type"), {"attribute_type": "Nickname", "lines": 1}),
        ("gender", _("Gender"), _("The gender of the person"), {"word_or_symbol": "word"}), # TODO are the symbols always available?
        ("gramps_id", _("Gramps ID"), _("The Gramps ID of the person"), {"lines": 1}),
        ("generation_num", _("Generation number"), _("The number of the generation of the person"), {"lines": 1}),
        ("genealogical_num", _("Ahnentafel number"), _("The Ahnentafel number of the person"), {"lines": 1}),
        ("tags", _("Tags"), _("The tags of the person"), {"lines": 1, "tag_visualization": "text_colors_counted"}),
        # TODO custom items (like badges)
    ],
    "family": [
        ("gutter", _("Gutter"), _("Space between other elements of specified size"), {"size": 5}),
        ("rel_type", _("Relationship type of the family"), _("The type of the family"), {"lines": 1}),
        ("image", _("Image"), _("Image associated with the family"), dict(IMAGE_PARAMS, **{"max_width": 160})),
        ("names", _("Names"), _("The preferred names of the spouses"), {"lines": 1, "name_format": 0}),
        ("marriage_or_fallback", _("Marriage or fallback"), _("Different information of marriage or fallback"), {"lines": 1, **EVENT_PARAMS}),
        ("divorce_or_fallback", _("Divorce or fallback"), _("Different information of divorce or fallback"), {"lines": 1, **EVENT_PARAMS}),
        ("marriage_divorce_or_fallbacks", _("Marriage and divorce or fallbacks"), _("Different information of marriage and divorce or fallbacks"), {"lines": 1, **EVENT_PARAMS}), # Full dates and places for both events since families are wider.
        ("event", _("Event"), _("Different information of the first event of the specified type"), {"event_type": "Marriage", "lines": 1, "index": 0, **EVENT_PARAMS}),
        ("attribute", _("Attribute"), _("The value of the attribute of the specified type"), {"attribute_type": "Number of Children", "lines": 1}),
        ("gramps_id", _("Gramps ID"), _("The Gramps ID of the family"), {"lines": 1}),
        ("tags", _("Tags"), _("The tags of the family"), {"lines": 1, "tag_visualization": "text_colors_counted"}),
        # TODO custom items (like badges)
    ],
}

PREDEF_BOXES_CONTENT_PROFILES = {
    "minimal": (
        "Minimal",
        125,
        [
            ("name", {"lines": 1}),
        ],
        [] # empty family box
    ),
    "compact": (
        "Compact",
        125,
        [
            ("name", {"lines": 2}),
            ("gutter", {"size": 5}),
            ("birth_death_or_fallbacks", {"lines": 1, **BIRTH_DEATH_PARAMS}),
        ],
        [
            ("marriage_or_fallback", {"lines": 1, **EVENT_PARAMS}),
        ]
    ),
    "regular": (
        "Regular",
        125,
        [
            ("image", dict(IMAGE_PARAMS, **{"max_width": 105})),
            ("gutter", {"size": 5}),
            ("name", {"lines": 2}),
            ("gutter", {"size": 5}),
            ("birth_or_fallback", {"lines": 1, **EVENT_PARAMS}),
            ("death_or_fallback", {"lines": 1, **EVENT_PARAMS}),
        ],
        [
            ("marriage_or_fallback", {"lines": 1, **EVENT_PARAMS}),
        ]
    ),
    "detailed": (
        "Detailed",
        250,
        [
            ("image", dict(IMAGE_PARAMS, **{"max_height": 100, "max_width": 200})),
            ("gutter", {"size": 5}),
            ("name", {"lines": 2}),
            ("gutter", {"size": 5}),
            ("alt_name", {"lines": 1}),
            ("gutter", {"size": 5}),
            ("attribute", {"attribute_type": "Nickname", "lines": 1}),
            ("gutter", {"size": 5}),
            ("birth_or_fallback", dict({"lines": 2, **EVENT_PARAMS}, **{"place": True})),
            ("event", dict({"event_type": "Death", "lines": 2, "index": 0, **EVENT_PARAMS}, **{"place": True})),
            ("event", dict({"event_type": "Burial", "lines": 2, "index": 0, **EVENT_PARAMS}, **{"place": True})),
            ("gutter", {"size": 5}),
            ("gramps_id", {"lines": 1}),
            ("tags", {"lines": 1, "tag_visualization": "text_colors_counted"}),
        ],
        [
            ("image", dict(IMAGE_PARAMS, **{"max_height": 100, "max_width": 400})),
            ("gutter", {"size": 5}),
            ("rel_type", {"lines": 1}),
            ("gutter", {"size": 5}),
            ("marriage_or_fallback", dict({"lines": 1, **EVENT_PARAMS}, **{"place": True})),
            ("divorce_or_fallback", dict({"lines": 1, **EVENT_PARAMS}, **{"place": True})),
            ("gutter", {"size": 5}),
            ("gramps_id", {"lines": 1}),
            ("tags", {"lines": 1, "tag_visualization": "text_colors_counted"}),
        ]
    ),
}

BOX_ITEM_PARAMS = {
    "max_height": _("Max. height"),
    "max_width": _("Max. width"),
    "fallback_avatar": _("Fallback to avatar"),
    "resolution": _("Resolution"),
    "filter": _("Filter"),
    "media_tag_sel_type": _("Only use images\nwith a tag that..."),
    "media_tag_sel": "", # for item param preview in item list
    "size": _("Size"),
    "lines": _("Number of lines"),
    "name_format": _("Name format"),
    "event_type": _("Event type"),
    "attribute_type": _("Attribute type"),
    "word_or_symbol": _("Visualization"),
    "event_type_visualization": _("Event type visualization"),
    "tag_visualization": _("Visualization"),
    "date": _("Display date"),
    "date_only_year": _("only display year"),
    "date_compact": _("compact format"),
    "place": _("Display place"),
    "description": _("Display description"),
    "tags": _("Display tags"),
    "index": _("Index"),
    "rel_base": _("Base person")
}

BOX_ITEM_PARAM_VALS = {
    "thumbnail_normal": _("Normal resolution"),
    "thumbnail_large": _("High resolution"),
    "contains": _("contains:"),
    "starts_with": _("starts with:"),
    "ends_with": _("ends with:"),
    "exact_match": _("exactly matches:"),
    "regex_match": _("matches regex:"),
    "original": _("Original"),
    "none": _("None"),
    "grayscale_dead": _("Apply grayscale to dead people"),
    "grayscale_all": _("Apply grayscale to all"),
    "text_colors_unique": _("Colors (unique)"),
    "text_colors_counted": _("Colors (unique, counted)"),
    "text_colors": _("Colors"),
    "text_names": _("Name"),
    "text_names_colors": _("Name and color"),
    "symbol_only_if_empty": _("Symbol (only if no information to display)"),
    "symbol": _("Symbol"),
    "word_only_if_empty": _("Word (only if no information to display)"),
    "word": _("Word"),
    "active": _("Active person"),
    "home": _("Home person"),
}

class FamilyTreeViewConfigPageManagerBoxes:
    def __init__(self, config_provider: "FamilyTreeViewConfigProvider"):
        self.config_provider = config_provider
        self.ftv = self.config_provider.ftv

        self.current_content_profile = None

    def boxes_page(self, configdialog):
        self.config_dialog = configdialog
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        row += 1
        label = Gtk.Label(_("Boxes content profile used in the tree chart:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 2, 1)
        content_profile_button_box = Gtk.ButtonBox()
        content_profile_button_box.set_layout(Gtk.ButtonBoxStyle.EXPAND)
        content_profile_button_box.set_homogeneous(False)
        self.content_profiles = [
            (k, _(v[0]))
            for k, v in PREDEF_BOXES_CONTENT_PROFILES.items()
        ] + [
            (k, v[0])
            for k, v in self.ftv._config.get("boxes.familytreeview-boxes-custom-defs").items()
        ]
        self.content_profile_list_store = Gtk.ListStore(str, str)
        for content_profile in self.content_profiles:
            self.content_profile_list_store.append(content_profile)
        self.content_profile_combo = Gtk.ComboBox(model=self.content_profile_list_store)
        self.content_profile_combo.set_hexpand(True)
        renderer = Gtk.CellRendererText()
        self.content_profile_combo.pack_start(renderer, True)
        self.content_profile_combo.add_attribute(renderer, "text", 1)
        sel_profile = self.ftv._config.get("boxes.familytreeview-boxes-selected-def-key")
        try:
            active_idx = [e[0] for e in self.content_profiles].index(sel_profile)
        except ValueError:
            active_idx = 2 # regular
        self.content_profile_combo.set_active(active_idx)
        def _cb_content_profile_combo_changed(combo):
            self.ftv._config.set(
                "boxes.familytreeview-boxes-selected-def-key",
                self.content_profiles[combo.get_active()][0]
            )
            _update_content_profile_buttons()
            self.ftv.cb_update_config(None, None, None, None)
        self.content_profile_combo.connect("changed", _cb_content_profile_combo_changed)
        content_profile_button_box.add(self.content_profile_combo)
        add_content_profile_button = Gtk.Button(image=Gtk.Image(icon_name="list-add"))
        add_content_profile_button.set_tooltip_text(_(
            "Add a new boxes content profile. It will be a copy of the "
            "'Regular' profile. You can modify it using the edit button."
        ))
        def _cb_content_profile_add(button):
            self._duplicate_content_profile("regular", show_message=False)
        add_content_profile_button.connect("clicked", _cb_content_profile_add)
        content_profile_button_box.pack_start(add_content_profile_button, False, False, 0)
        duplicate_content_profile_button = Gtk.Button(image=Gtk.Image(icon_name="edit-copy"))
        duplicate_content_profile_button.set_tooltip_text(_(
            "Duplicate this boxes content profile. You can modify it using "
            "the edit button."
        ))
        def _cb_content_profile_duplicate(button):
            self._duplicate_content_profile(show_message=False)
        duplicate_content_profile_button.connect("clicked", _cb_content_profile_duplicate)
        content_profile_button_box.pack_start(duplicate_content_profile_button, False, False, 0)
        edit_content_profile_button = Gtk.Button(image=Gtk.Image(icon_name="gtk-edit"))
        edit_content_profile_button.set_tooltip_text(_("Edit this boxes content profile"))
        def _cb_content_profile_edit(button):
            key_to_edit = self.ftv._config.get("boxes.familytreeview-boxes-selected-def-key")
            self._open_content_profile_edit_dialog(key_to_edit)
        edit_content_profile_button.connect("clicked", _cb_content_profile_edit)
        content_profile_button_box.pack_start(edit_content_profile_button, False, False, 0)
        remove_content_profile_button = Gtk.Button(image=Gtk.Image(icon_name="list-remove"))
        def _cb_content_profile_remove(button):
            key_to_remove = self.ftv._config.get("boxes.familytreeview-boxes-selected-def-key")
            if self._is_predef_content_profile(key_to_remove):
                # Predefined content profile cannot be removed.
                return
            active_idx = self.content_profile_combo.get_active()
            active_iter = self.content_profile_combo.get_active_iter()
            self.content_profile_list_store.remove(active_iter)
            self.content_profile_combo.set_active(active_idx-1)
            self.content_profiles.pop(active_idx)
            self._remove_content_profile(key_to_remove)
        remove_content_profile_button.connect("clicked", _cb_content_profile_remove)
        content_profile_button_box.pack_start(remove_content_profile_button, False, False, 0)
        grid.attach(content_profile_button_box, 3, row, 2, 1)

        def _update_content_profile_buttons():
            is_predef = self._is_predef_content_profile()
            remove_content_profile_button.set_sensitive(not is_predef)
            if is_predef:
                remove_tooltip = _(
                    "This boxes content profile cannot be removed because it "
                    "is predefined"
                )
            else:
                remove_tooltip = _("Remove this boxes config profile")
            remove_content_profile_button.set_tooltip_text(remove_tooltip)
        _update_content_profile_buttons()

        return grid

    def _open_content_profile_edit_dialog(self, content_profile_key):
        if self._is_predef_content_profile():
            self.current_content_profile = list(deepcopy(PREDEF_BOXES_CONTENT_PROFILES[content_profile_key]))
        else:
            custom_defs = self.ftv._config.get("boxes.familytreeview-boxes-custom-defs")
            self.current_content_profile = list(deepcopy(custom_defs[content_profile_key]))

        dialog = Gtk.Dialog(
            title=_("Edit FTV Boxes Content Profile"),
            transient_for=self.config_dialog.window
        )

        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        row += 1
        label = Gtk.Label()
        label.set_markup("<i>"+_(
            "A boxes content profile defines the contents of person and "
            "family boxes."
        )+"</i>")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 4, 1)

        row += 1
        label = Gtk.Label(_("Name of this boxes content profile:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 2, 1)
        self.content_profile_name_entry = Gtk.Entry()
        self.content_profile_name_entry.set_hexpand(True)
        self.content_profile_name_entry.set_text(self._get_content_profile_name())
        grid.attach(self.content_profile_name_entry, 3, row, 2, 1)

        row +=1
        person_width_label = Gtk.Label(_(
            "Width of each person box in the tree chart:"
        ))
        person_width_label.set_halign(Gtk.Align.START)
        grid.attach(person_width_label, 1, row, 2, 1)
        adjustment = Gtk.Adjustment(
            value=self._get_person_width(),
            lower=70.0, # smaller is strange when there are expanders
            upper=500.0,
            step_increment=1.0,
            page_increment=0.0,
            page_size=0.0,
        )
        self.person_width_spin_button = Gtk.SpinButton(adjustment=adjustment, climb_rate=0.0, digits=0)
        def _cb_person_box_width_changed(spin_button):
            # TODO for all images in person and family boxes: reduce
            # image width to box width without margins, if they are too
            # wide
            pass 
        self.person_width_spin_button.connect("value-changed", _cb_person_box_width_changed)
        grid.attach(self.person_width_spin_button, 3, row, 2, 1)

        row += 1
        family_width_label = Gtk.Label()
        family_width_label.set_markup("<i>"+_(
            "The width of family boxes is calculated based on the width of "
            "person boxes."
        )+"</i>")
        family_width_label.set_halign(Gtk.Align.START)
        grid.attach(family_width_label, 1, row, 4, 1)

        row += 1
        label = Gtk.Label()
        label.set_margin_top(20)
        label.set_markup("<i>"+_(
            "You can customize the contents of the person and family boxes "
            "below."
        )+"</i>")
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 4, 1)

        notebook = Gtk.Notebook()
        notebook_row = row + 1

        self.item_defs_list_stores = {}
        self.item_defs_tree_views = {}
        self.add_item_def_buttons = {}
        self.content_item_selection_changed_handler_ids = {}
        self.duplicate_item_def_buttons = {}
        self.up_item_def_buttons = {}
        self.down_item_def_buttons = {}
        self.remove_item_def_buttons = {}
        self.item_def_type_params_boxes = {}
        self.item_def_type_params_grids = {}
        for box_type in ["person", "family"]:
            box_type_def_grid = Gtk.Grid()
            box_type_def_grid.set_border_width(12)
            box_type_def_grid.set_column_spacing(6)
            box_type_def_grid.set_row_spacing(6)
            box_type_def_grid.set_column_homogeneous(True)
            row = -1

            row += 1
            item_defs_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            item_defs_vbox.set_spacing(6)

            if box_type == "person":
                title = _("List of person box item definitions")
            else:
                title = _("List of family box item definitions")
            items_title = Gtk.Label(title)
            item_defs_vbox.add(items_title)

            item_defs_list_store = Gtk.ListStore(str, str, str)
            self.item_defs_list_stores[box_type] = item_defs_list_store
            self._fill_item_defs_list_store_from_config(box_type)
            item_defs_tree_view = Gtk.TreeView(model=item_defs_list_store)
            self.item_defs_tree_views[box_type] = item_defs_tree_view

            renderer = Gtk.CellRendererText()
            # TODO Ellipsization changes column width.
            # renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            column = Gtk.TreeViewColumn("Item type", renderer, text=1)
            column.set_resizable(True)
            item_defs_tree_view.append_column(column)

            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn("Item params", renderer, text=2)
            item_defs_tree_view.append_column(column)

            items_scrolled_window = Gtk.ScrolledWindow()
            items_scrolled_window.set_hexpand(True)
            items_scrolled_window.set_vexpand(True)
            items_scrolled_window.add(item_defs_tree_view)

            item_defs_hbox = Gtk.Box()
            item_defs_hbox.set_spacing(6)
            item_defs_hbox.add(items_scrolled_window)

            item_def_button_box = Gtk.ButtonBox(orientation=Gtk.Orientation.VERTICAL)
            item_def_button_box.set_layout(Gtk.ButtonBoxStyle.EXPAND)
            item_def_button_box.set_homogeneous(False)

            add_item_def_button = Gtk.Button(image=Gtk.Image(icon_name="list-add"))
            add_item_def_button.set_halign(Gtk.Align.START) # prevent wide button
            add_item_def_button.set_tooltip_text(_("Add a new box item definition"))
            self.add_item_def_buttons[box_type] = add_item_def_button
            add_item_def_button.connect("clicked", self._cb_add_item_def_button_clicked, box_type)
            item_def_button_box.pack_start(add_item_def_button, False, False, 0)

            duplicate_item_def_button = Gtk.Button(image=Gtk.Image(icon_name="edit-copy"))
            duplicate_item_def_button.set_halign(Gtk.Align.START)
            duplicate_item_def_button.set_tooltip_text(_("Duplicate the selected item definition"))
            self.duplicate_item_def_buttons[box_type] = duplicate_item_def_button
            duplicate_item_def_button.set_sensitive(False)
            duplicate_item_def_button.connect("clicked", self._cb_duplicate_item_def_button_clicked, box_type)
            item_def_button_box.pack_start(duplicate_item_def_button, False, False, 0)

            up_item_def_button = Gtk.Button(image=Gtk.Image(icon_name="go-up-symbolic"))
            up_item_def_button.set_halign(Gtk.Align.START)
            up_item_def_button.set_tooltip_text(_("Move the selected item definition up"))
            self.up_item_def_buttons[box_type] = up_item_def_button
            up_item_def_button.set_sensitive(False)
            up_item_def_button.connect("clicked", self._cb_up_item_def_button_clicked, box_type)
            item_def_button_box.pack_start(up_item_def_button, False, False, 0)

            down_item_def_button = Gtk.Button(image=Gtk.Image(icon_name="go-down-symbolic"))
            down_item_def_button.set_halign(Gtk.Align.START)
            down_item_def_button.set_tooltip_text(_("Move the selected item definition down"))
            self.down_item_def_buttons[box_type] = down_item_def_button
            down_item_def_button.set_sensitive(False)
            down_item_def_button.connect("clicked", self._cb_down_item_def_button_clicked, box_type)
            item_def_button_box.pack_start(down_item_def_button, False, False, 0)

            remove_item_def_button = Gtk.Button(image=Gtk.Image(icon_name="list-remove"))
            remove_item_def_button.set_halign(Gtk.Align.START)
            remove_item_def_button.set_tooltip_text(_("Remove the selected item definition"))
            self.remove_item_def_buttons[box_type] = remove_item_def_button
            remove_item_def_button.set_sensitive(False)
            remove_item_def_button.connect("clicked", self._cb_remove_item_def_button_clicked, box_type)
            item_def_button_box.pack_start(remove_item_def_button, False, False, 0)

            item_defs_hbox.add(item_def_button_box)
            item_defs_vbox.add(item_defs_hbox)
            box_type_def_grid.attach(item_defs_vbox, 1, row, 1, 1)

            outer_item_def_type_params_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            outer_item_def_type_params_vbox.set_spacing(6)
            if box_type == "person":
                title = _("Parameters for selected person box item definition")
            else:
                title = _("Parameters for selected family box item definition")
            params_title = Gtk.Label(title)
            params_title.set_hexpand(True)
            outer_item_def_type_params_vbox.add(params_title)

            item_def_type_params_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.item_def_type_params_boxes[box_type] = item_def_type_params_box
            outer_item_def_type_params_vbox.add(item_def_type_params_box)

            selection = item_defs_tree_view.get_selection()
            self.content_item_selection_changed_handler_ids[box_type] = (
                selection.connect("changed", self._cb_item_def_selection_changed, box_type)
            )
            self._cb_item_def_selection_changed(selection, box_type)

            outer_item_def_type_params_hbox = Gtk.Box()
            outer_item_def_type_params_hbox.set_spacing(6)
            separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            outer_item_def_type_params_hbox.add(separator)
            outer_item_def_type_params_hbox.add(outer_item_def_type_params_vbox)
            box_type_def_grid.attach(outer_item_def_type_params_hbox, 2, row, 1, 1)

            if box_type == "person":
                title = _("Person boxes")
            else:
                title = _("Family boxes")
            notebook.append_page(box_type_def_grid, Gtk.Label(label=title))

        grid.attach(notebook, 1, notebook_row, 4, 1)
        dialog.get_content_area().add(grid)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK,
        )

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            # save definition

            # name
            name = self.content_profile_name_entry.get_text().strip()
            new_content_profile_key = self._duplicate_content_profile_if_predef(name=name)
            if new_content_profile_key != content_profile_key:
                # name may have changed: "(copy)". The duplicate
                # function stored it.
                name = self._get_content_profile_name()
            else:
                # Otherwise, name from _get_content_profile_name is not
                # based on the entry and we keep the value from the
                # entry. The value needs to be stored.
                self._set_content_profile_name(name)

            # Update the list store for combo in main config window.
            for row in self.content_profile_list_store:
                if row[0] == new_content_profile_key:
                    row[1] = name
                    # combo updates automatically
                    break

            # width
            self._set_person_width(int(self.person_width_spin_button.get_value()))

            # content items
            custom_defs = self.ftv._config.get("boxes.familytreeview-boxes-custom-defs")
            custom_defs[new_content_profile_key] = tuple(self.current_content_profile)
            self.ftv._config.set("boxes.familytreeview-boxes-custom-defs", custom_defs)

            # general
            self.ftv.widget_manager.canvas_manager.reset_abbrev_names() # due to person width # TODO make this conditional
            self.ftv.cb_update_config(None, None, None, None)

        # Ignore response == Gtk.ResponseType.CANCEL, discard changes.
        self.current_content_profile = None

        dialog.close()

    def _fill_item_defs_list_store_from_config(self, box_type):
        self.item_defs_list_stores[box_type].clear()
        item_defs = self._get_box_content_item_defs(box_type)
        for item_def_type, item_def_params in item_defs:
            item_def_type_translated = "?"
            for item in BOX_ITEMS[box_type]:
                if item[0] == item_def_type:
                    item_def_type_translated = item[1]
            item_def_params_str = self._get_item_def_params_str(item_def_params)
            self.item_defs_list_stores[box_type].append((item_def_type, item_def_type_translated, item_def_params_str))

    def _get_item_def_params_str(self, params):
        s = ""
        remove_if_last = 0
        for key, value in params.items():
            p = key # fallback
            for param, translated in BOX_ITEM_PARAMS.items():
                if param == key:
                    p = translated
                    break
            p = p.replace("\n", " ")
            value = str(value)
            if key == "media_tag_sel":
                # a value from an entry
                val = '"{}"'.format(value)
            else:
                val = BOX_ITEM_PARAM_VALS.get(value, value)
            if p.endswith("..."):
                p = p[:-3] # remove "..."
                s += "%s %s " % (p, val)
                remove_if_last = 1
            elif len(p) == 0:
                s += val
                remove_if_last = 0
            else:
                s += "%s: %s, " % (p, val)
                remove_if_last = 2
        if len(s) == 0 or remove_if_last == 0:
            return s
        return s[:-remove_if_last] # remove last comma or space

    def _item_list_changed(self, box_type, select_index=None, item_def_type_changed=False):
        # Use GLib.idle_add to prevent segmentation fault on macOS.
        GLib.idle_add(self._update_item_list, box_type, select_index, item_def_type_changed)

    def _update_item_list(self, box_type, select_index=None, item_def_type_changed=False):
        selection = self.item_defs_tree_views[box_type].get_selection()

        # Params need to be updated when the item type changed or the
        # selection changed. Updating every time a change is made resets
        # the scroll position and focus settings before the user has
        # finished configuring them.
        update_params = item_def_type_changed
        if not update_params and select_index is not None:
            select_path = Gtk.TreePath.new_from_indices([select_index])
            selection_changes = not selection.path_is_selected(select_path)
            update_params = selection_changes

        # Temporarily block the callback to update the params
        if not update_params:
            GObject.signal_handler_block(
                selection,
                self.content_item_selection_changed_handler_ids[box_type]
            )

        selection.unselect_all()
        self._fill_item_defs_list_store_from_config(box_type)
        selection = self.item_defs_tree_views[box_type].get_selection()

        if select_index is not None:
            selection.select_path(str(select_index))

        if not update_params:
            GObject.signal_handler_unblock(
                selection,
                self.content_item_selection_changed_handler_ids[box_type]
            )

    def _cb_item_def_selection_changed(self, selection, box_type):
        for child in self.item_def_type_params_boxes[box_type].get_children():
            self.item_def_type_params_boxes[box_type].remove(child)
        if selection.count_selected_rows() > 0:
            item_defs_list_store, selected_tree_iter = selection.get_selected()
            selected_path = selection.get_selected_rows()[1][0].to_string()
            item_def_idx = int(selected_path)

            item_defs_tree_view = selection.get_tree_view()
            item_defs_list_store = item_defs_tree_view.get_model()

            item_def_types_list_store = Gtk.ListStore(str, str)
            for item_def_type in BOX_ITEMS[box_type]:
                item_def_types_list_store.append(item_def_type[:2])
            item_def_type_combo = Gtk.ComboBox.new_with_model(item_def_types_list_store)
            item_def_type_of_selection = item_defs_list_store[selected_tree_iter][0]
            all_item_def_types = [item[0] for item in BOX_ITEMS[box_type]]
            selected_item_def_type_idx = all_item_def_types.index(item_def_type_of_selection)
            cell_renderer_text = Gtk.CellRendererText()
            item_def_type_combo.pack_start(cell_renderer_text, True)
            item_def_type_combo.add_attribute(cell_renderer_text, "text", 1)
            item_def_type_combo.set_active(selected_item_def_type_idx)
            self.item_def_type_params_boxes[box_type].add(item_def_type_combo)

            item_def_type_descr = BOX_ITEMS[box_type][selected_item_def_type_idx][2]
            item_def_type_descr_label = Gtk.Label(item_def_type_descr)
            item_def_type_descr_label.set_halign(Gtk.Align.START)
            item_def_type_descr_label.set_margin_top(10)
            self.item_def_type_params_boxes[box_type].add(item_def_type_descr_label)

            item_type_def_params_scrolled = Gtk.ScrolledWindow()
            item_type_def_params_scrolled.set_margin_top(20)
            item_type_def_params_scrolled.set_vexpand(True)
            item_type_def_params_grid = Gtk.Grid()
            self.item_def_type_params_grids[box_type] = item_type_def_params_grid
            item_type_def_params_scrolled.add(item_type_def_params_grid)
            self.item_def_type_params_boxes[box_type].add(item_type_def_params_scrolled)
            self._create_item_def_params(box_type, item_def_idx)

            item_def_type_combo.connect("changed", self._cb_item_def_type_changed, box_type, item_def_type_descr_label, item_def_idx)

            num_item_defs = item_defs_list_store.iter_n_children()
            self.duplicate_item_def_buttons[box_type].set_sensitive(True)
            self.up_item_def_buttons[box_type].set_sensitive(item_def_idx>0)
            self.down_item_def_buttons[box_type].set_sensitive(item_def_idx<num_item_defs-1)
            self.remove_item_def_buttons[box_type].set_sensitive(True)
        else:
            label = Gtk.Label(_(
                "Select an item definition on the left to modify its parameters."
            ))
            label.set_halign(Gtk.Align.START)
            label.set_line_wrap(True)
            self.item_def_type_params_boxes[box_type].add(label)

            self.duplicate_item_def_buttons[box_type].set_sensitive(False)
            self.up_item_def_buttons[box_type].set_sensitive(False)
            self.down_item_def_buttons[box_type].set_sensitive(False)
            self.remove_item_def_buttons[box_type].set_sensitive(False)
        # For some reason children are hidden:
        self.item_def_type_params_boxes[box_type].show_all()

    def _create_item_def_params(self, box_type, item_i):
        for child in self.item_def_type_params_grids[box_type].get_children():
            self.item_def_type_params_grids[box_type].remove(child)
        scrolled_window = self.item_def_type_params_grids[box_type].get_parent()
        def propagate_to_scrolled_window(widget, event):
            Gtk.propagate_event(scrolled_window, event)
            return True # don't propagate further
        box_content_item_types = self._get_box_content_item_defs(box_type)
        item_params = box_content_item_types[item_i][1]
        row = -1
        for item_param, param_value in item_params.items():
            if item_param == "media_tag_sel":
                # was handled together with another param
                continue

            row += 1
            param_translation = item_param # fallback
            for param, translation in BOX_ITEM_PARAMS.items():
                if param == item_param:
                    param_translation = translation
                    break
            if not (
                item_param == "date_only_year"
                or item_param == "date_compact"
                or (
                    # Don't hide tag_visualization if it's a primary
                    # param (of a "tags" item) but hide if it's a
                    # secondary param (e.g. of an "event" item).
                    item_param == "tag_visualization"
                    and box_content_item_types[item_i][0] != "tags"
                )
            ):
                label = Gtk.Label(param_translation)
                label.set_xalign(0)
                label.set_halign(Gtk.Align.START)
                label.set_justify(Gtk.Justification.LEFT)
                label.set_line_wrap(True)
                label.set_margin_right(10)
                self.item_def_type_params_grids[box_type].attach(label, 1, row, 1, 1)

            tip = None

            if item_param in ["fallback_avatar", "date", "place", "description", "tags"]:
                check_button = Gtk.CheckButton()
                check_button.set_active(param_value)
                check_button.connect("toggled", self._cb_param_check_button_toggled, box_type, item_i, item_param)
                check_button.set_margin_top(10)
                self.item_def_type_params_grids[box_type].attach(check_button, 2, row, 1, 1)
                if item_param == "place":
                    tip = _(
                        "You can change the place format on the 'Appearance' "
                        "page."
                    )
            elif item_param in ["date_only_year", "date_compact"]:
                check_button = Gtk.CheckButton(param_translation)
                check_button.set_active(param_value)
                check_button.connect("toggled", self._cb_param_check_button_toggled, box_type, item_i, item_param)
                self.item_def_type_params_grids[box_type].attach(check_button, 2, row, 1, 1)
            elif item_param in ["size", "lines", "max_height", "max_width", "index"]:
                # SpinButton
                lower = 1.0
                if item_param == "size":
                    upper = 200.0
                elif item_param == "lines":
                    upper = 20.0
                elif item_param == "max_height":
                    upper = 500.0
                elif item_param == "max_width":
                    upper = self._get_person_width() - 2*10 # padding
                else: # "index"
                    if param_value >= 0:
                        # For the first item (index 0), the user should
                        # see 1.
                        param_value += 1
                    upper = 100.0
                    lower = -100.0
                    tip = _(
                        "Enter a positive number to get the n-th event.\n"
                        "If the number is negative, it's counted from the "
                        "last item.\n"
                        "Examples:\n"
                        "1 -> the 1st item (if there is at least one)\n"
                        "3 -> the 3rd item (if there are at least three\n"
                        "-1 -> the last item (if there is at least one)\n"
                        "-2 -> the 2nd to last item (if there are at least "
                        "two)\n"
                    )
                adjustment = Gtk.Adjustment(
                    value=param_value,
                    lower=lower,
                    upper=upper,
                    step_increment=1.0,
                    page_increment=0.0,
                    page_size=0.0, # recommended for Gtk.SpinButton (docs)
                )
                spin_button = Gtk.SpinButton(adjustment=adjustment, climb_rate=0.0, digits=0)
                spin_button.connect("value-changed", self._cb_param_spin_button_value_changed, box_type, item_i, item_param)
                spin_button.set_hexpand(True)
                spin_button.connect("scroll-event", propagate_to_scrolled_window) # prevent scrolling
                self.item_def_type_params_grids[box_type].attach(spin_button, 2, row, 1, 1)
            elif item_param in ["event_type", "attribute_type"]:
                combo_box = Gtk.ComboBox(has_entry=True)
                if item_param == "event_type":
                    custom_values = sorted(self.ftv.dbstate.db.get_event_types(), key=lambda s: s.lower())
                    # str(val) would give translated string
                    set_val = (
                        lambda val, box_type=box_type, item_i=item_i, item_param=item_param:
                            self._cb_param_monitored_data_type_set(val, box_type, item_i, item_param)
                    )
                    # GrampsType.__set_str expects translated (as it's using _S2IMAP) so param_value cannot be used directly
                    get_val = lambda param_value=param_value: EventType(EventType._E2IMAP[param_value])
                elif item_param == "attribute_type":
                    if box_type == "person":
                        custom_values = sorted(self.ftv.dbstate.db.get_person_attribute_types(), key=lambda s: s.lower())
                    else:
                        custom_values = sorted(self.ftv.dbstate.db.get_family_attribute_types(), key=lambda s: s.lower())
                    set_val = (
                        lambda val, box_type=box_type, item_i=item_i, item_param=item_param:
                            # str(val) would give translated string
                            self._cb_param_monitored_data_type_set(
                                val[1] if val[0] == -1 else AttributeType._I2EMAP[val[0]],
                                box_type, item_i, item_param
                            )
                    )
                    # GrampsType.__set_str expects translated (as it's using _S2IMAP) so param_value cannot be used directly
                    get_val = lambda param_value=param_value: AttributeType(AttributeType._E2IMAP[param_value])
                MonitoredDataType(
                    combo_box,
                    set_val,
                    get_val,
                    self.ftv.dbstate.db.readonly,
                    custom_values=custom_values
                )
                combo_box.connect("scroll-event", propagate_to_scrolled_window) # prevent scrolling
                self.item_def_type_params_grids[box_type].attach(combo_box, 2, row, 1, 1)
            elif item_param in ["resolution", "filter", "media_tag_sel_type", "name_format", "tag_visualization", "word_or_symbol", "event_type_visualization", "rel_base"]:
                combo_box = Gtk.ComboBox()
                options_include_label = False # for most cases
                if item_param == "name_format":
                    first_col_type = int
                    # TODO Is this list constructed correctly? See also names page.
                    options = []
                    options_include_label = True
                    name_formats = [
                        (0, _("Default format"), "", True)
                    ]
                    name_formats.extend(name_displayer.get_name_format())
                    for num, name, fmt_str, act in name_formats:
                        if num == 0:
                            options.append((num, name))
                            continue

                        translation = fmt_str
                        for key in get_keywords():
                            if key in translation:
                                translation = translation.replace(
                                    key, get_translation_from_keyword(key)
                                )
                        options.append((num, translation))
                    if box_type == "family":
                        tip = _(
                            "Tip: You can create a new name format in the "
                            "Gramps preferences (e.g. 'Surname' to display "
                            "only the surnames) and use it here."
                        )
                elif item_param == "tag_visualization":
                    first_col_type = str
                    options = [
                        "text_colors_unique",
                        "text_colors_counted",
                        "text_colors",
                        "text_names",
                        "text_names_colors",
                        # TODO Maybe other representations which use
                        # separate/multiple canvas items per tag.
                    ]
                elif item_param == "word_or_symbol":
                    first_col_type = str
                    options = [
                        "symbol",
                        "word",
                    ]
                elif item_param == "event_type_visualization":
                    first_col_type = str
                    options = [
                        "none",
                        "symbol_only_if_empty",
                        "symbol",
                        "word_only_if_empty",
                        "word",
                    ]
                elif item_param == "rel_base":
                    first_col_type = str
                    options = [
                        "active",
                        "home",
                    ]
                elif item_param == "resolution":
                    first_col_type = str
                    options = [
                        "thumbnail_normal",
                        "thumbnail_large",
                        "original",
                    ]
                elif item_param == "filter":
                    first_col_type = str
                    if box_type == "person":
                        options = [
                            "none",
                            "grayscale_dead",
                            "grayscale_all",
                        ]
                    else: # family
                        options = [
                            "none",
                            "grayscale_all",
                        ]
                elif item_param == "media_tag_sel_type":
                    first_col_type = str
                    options = [
                        "contains",
                        "starts_with",
                        "ends_with",
                        "exact_match",
                        "regex_match",
                    ]
                    tip = _(
                        "Leave the entry box on the right empty to use any "
                        "image."
                    )
                list_store = Gtk.ListStore(first_col_type, str)
                for opt in options:
                    if options_include_label:
                        list_store.append(opt)
                    else:
                        list_store.append((opt, BOX_ITEM_PARAM_VALS[opt]))
                combo_box = Gtk.ComboBox.new_with_model(list_store)
                renderer = Gtk.CellRendererText()
                renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
                combo_box.pack_start(renderer, True)
                combo_box.add_attribute(renderer, "text", 1)
                try:
                    if options_include_label:
                        active_index = [opt[0] for opt in options].index(param_value)
                    else:
                        active_index = options.index(param_value)
                except ValueError:
                    active_index = 0 # fallback
                combo_box.set_active(active_index)
                combo_box.connect("changed", self._cb_param_combo_box_changed, box_type, item_i, item_param)
                combo_box.connect("scroll-event", propagate_to_scrolled_window) # prevent scrolling
                if item_param != "media_tag_sel_type": # will be used below
                    self.item_def_type_params_grids[box_type].attach(combo_box, 2, row, 1, 1)
            if item_param == "media_tag_sel_type": # also processes media_tag_sel
                button_box = Gtk.ButtonBox()
                button_box.set_layout(Gtk.ButtonBoxStyle.EXPAND)
                button_box.set_homogeneous(False)
                button_box.pack_start(combo_box, False, False, 0)
                entry = Gtk.Entry()
                entry.set_width_chars(1) # this can get very small, dropdown should not shrink
                entry.set_text(item_params["media_tag_sel"])
                entry.connect("changed", self._cb_param_entry_changed, box_type, item_i, "media_tag_sel")
                button_box.add(entry)
                self.item_def_type_params_grids[box_type].attach(button_box, 2, row, 1, 1)

            if tip is not None:
                row += 1
                label = Gtk.Label(tip)
                label.set_xalign(0)
                label.set_halign(Gtk.Align.START)
                label.set_justify(Gtk.Justification.LEFT)
                label.set_line_wrap(True)
                label.set_margin_bottom(10)
                self.item_def_type_params_grids[box_type].attach(label, 2, row, 1, 1)

    # item def option/param callbacks

    def _cb_item_def_type_changed(self, combo, box_type, item_type_description_label, item_i):
        active_iter = combo.get_active_iter()
        if active_iter is None:
            return
        new_item_type = combo.get_model()[active_iter][0]
        box_content_item_types = self._get_box_content_item_defs(box_type)
        default_params = {} # fallback
        for item_type in BOX_ITEMS[box_type]:
            if item_type[0] == new_item_type:
                item_type_description = item_type[2]
                default_params = deepcopy(item_type[3])
                break
        box_content_item_types[item_i] = (new_item_type, default_params)
        self._set_box_content_item_defs(box_type, box_content_item_types)
        item_type_description_label.set_text(item_type_description)
        self._create_item_def_params(box_type, item_i)
        self._item_list_changed(box_type, item_i, item_def_type_changed=True)

    def _cb_param_check_button_toggled(self, check_button, box_type, item_i, item_param):
        box_content_item_types = self._get_box_content_item_defs(box_type)
        box_content_item_types[item_i][1][item_param] = check_button.get_active()
        self._set_box_content_item_defs(box_type, box_content_item_types)

        self._item_list_changed(box_type, item_i)

    def _cb_param_spin_button_value_changed(self, spin_button, box_type, item_i, item_param):
        box_content_item_types = self._get_box_content_item_defs(box_type)
        val = int(spin_button.get_value())
        if item_param == "index" and val > 0:
            # For the first item (index 0), the user should enter 1.
            val -= 1
        box_content_item_types[item_i][1][item_param] = val
        self._set_box_content_item_defs(box_type, box_content_item_types)
        
        if item_param == "lines":
            # TODO also check if current is name or alt_name
            self.ftv.widget_manager.canvas_manager.reset_abbrev_names()
        self._item_list_changed(box_type, item_i)

    def _cb_param_monitored_data_type_set(self, val, box_type, item_i, item_param):
        if isinstance(val, tuple):
            # event
            if val[0] == -1:
                new_value = val[1]
            else:
                new_value = EventType._I2EMAP[val[0]]
        else:
            # attribute
            new_value = val
        box_content_item_types = self._get_box_content_item_defs(box_type)
        box_content_item_types[item_i][1][item_param] = new_value
        self._set_box_content_item_defs(box_type, box_content_item_types)
        self._item_list_changed(box_type, item_i)

    def _cb_param_combo_box_changed(self, combo_box, box_type, item_i, item_param):
        param_model = combo_box.get_model()
        active_iter = combo_box.get_active_iter()
        box_content_item_types = self._get_box_content_item_defs(box_type)
        new_value = param_model[active_iter][0] # 0: non-translated
        box_content_item_types[item_i][1][item_param] = new_value
        self._set_box_content_item_defs(box_type, box_content_item_types)
        self._item_list_changed(box_type, item_i)

    def _cb_param_entry_changed(self, entry, box_type, item_i, item_param):
        box_content_item_types = self._get_box_content_item_defs(box_type)
        box_content_item_types[item_i][1][item_param] = entry.get_text()
        self._set_box_content_item_defs(box_type, box_content_item_types)
        self._item_list_changed(box_type, item_i)

    # item def button callbacks

    def _cb_add_item_def_button_clicked(self, button, box_type):
        box_content_item_defs = self._get_box_content_item_defs(box_type)
        new_item_def_type = "gutter"
        new_item_def_params = {}
        for item in BOX_ITEMS[box_type]:
            if item[0] == new_item_def_type:
                new_item_def_params = deepcopy(item[3])
                break
        new_item_def = (new_item_def_type, new_item_def_params)
        selection = self.item_defs_tree_views[box_type].get_selection()
        if selection.count_selected_rows() == 0:
            item_def_idx = len(box_content_item_defs)
        else:
            # insert after current selection
            item_def_idx = int(selection.get_selected_rows()[1][0].to_string())+1
        box_content_item_defs.insert(item_def_idx, new_item_def)
        self._set_box_content_item_defs(box_type, box_content_item_defs)
        self._item_list_changed(box_type, item_def_idx)

    def _cb_duplicate_item_def_button_clicked(self, button, box_type):
        selection = self.item_defs_tree_views[box_type].get_selection()
        if selection.count_selected_rows() > 0:
            box_content_item_defs = self._get_box_content_item_defs(box_type)
            item_def_idx = int(selection.get_selected_rows()[1][0].to_string())
            new_item_def = deepcopy(box_content_item_defs[item_def_idx])
            box_content_item_defs.insert(item_def_idx, new_item_def)
            self._set_box_content_item_defs(box_type, box_content_item_defs)
            self._item_list_changed(box_type, item_def_idx+1)

    def _cb_up_item_def_button_clicked(self, button, box_type):
        selection = self.item_defs_tree_views[box_type].get_selection()
        if selection.count_selected_rows() > 0:
            box_content_item_defs = self._get_box_content_item_defs(box_type)
            item_def_idx = int(selection.get_selected_rows()[1][0].to_string())
            box_content_item_defs.insert(item_def_idx-1, box_content_item_defs.pop(item_def_idx))
            self._set_box_content_item_defs(box_type, box_content_item_defs)
            self._item_list_changed(box_type, item_def_idx-1)

    def _cb_down_item_def_button_clicked(self, button, box_type):
        selection = self.item_defs_tree_views[box_type].get_selection()
        if selection.count_selected_rows() > 0:
            box_content_item_defs = self._get_box_content_item_defs(box_type)
            item_def_idx = int(selection.get_selected_rows()[1][0].to_string())
            box_content_item_defs.insert(item_def_idx+1, box_content_item_defs.pop(item_def_idx))
            self._set_box_content_item_defs(box_type, box_content_item_defs)
            self._item_list_changed(box_type, item_def_idx+1)

    def _cb_remove_item_def_button_clicked(self, button, box_type):
        selection = self.item_defs_tree_views[box_type].get_selection()
        if selection.count_selected_rows() > 0:
            box_content_item_defs = self._get_box_content_item_defs(box_type)
            item_def_idx = int(selection.get_selected_rows()[1][0].to_string())
            box_content_item_defs.pop(item_def_idx)
            self._set_box_content_item_defs(box_type, box_content_item_defs)
            self._item_list_changed(box_type)

    # predef handling

    def _duplicate_content_profile_if_predef(self, name=None):
        selected_content_profile_key = self.ftv._config.get("boxes.familytreeview-boxes-selected-def-key")
        if not self._is_predef_content_profile(selected_content_profile_key):
            return selected_content_profile_key
        return self._duplicate_content_profile(selected_content_profile_key, name=name)

    def _duplicate_content_profile(self, selected_content_profile_key=None, name=None, show_message=True):
        if selected_content_profile_key is None:
            selected_content_profile_key = self.ftv._config.get("boxes.familytreeview-boxes-selected-def-key")

        custom_defs = self.ftv._config.get("boxes.familytreeview-boxes-custom-defs")
        custom_keys = custom_defs.keys()
        custom_keys = [int(key) for key in custom_keys if key.isdigit()]
        try:
            new_profile_key = max(custom_keys)+1
        except ValueError:
            new_profile_key = 0
        new_profile_key = str(new_profile_key)

        if self.current_content_profile is not None:
            content_profile = self.current_content_profile
        else:
            if self._is_predef_content_profile(selected_content_profile_key):
                content_profile = list(deepcopy(PREDEF_BOXES_CONTENT_PROFILES[selected_content_profile_key]))
            else:
                content_profile = list(deepcopy(custom_defs[selected_content_profile_key]))
        if name is None or name == content_profile[0]:
            new_name = content_profile[0] + " (copy)"
            copy_num = 1
            while new_name in [d[1] for d in self.content_profiles]:
                copy_num += 1
                new_name = content_profile[0] + f" (copy {copy_num})"
        else:
            # e.g. the name was edited
            new_name = name
        content_profile[0] = new_name

        custom_defs[new_profile_key] = tuple(content_profile)
        self.ftv._config.set("boxes.familytreeview-boxes-custom-defs", custom_defs)

        self.ftv._config.set("boxes.familytreeview-boxes-selected-def-key", new_profile_key)

        self.content_profiles.append((new_profile_key, content_profile[0]))
        self.content_profile_list_store.append((new_profile_key, content_profile[0]))
        self.content_profile_combo.set_active(len(self.content_profiles)-1)
        # Person width spin button value doesn't change, since it's a
        # copy.

        if show_message:
            dialog = Gtk.MessageDialog(
                transient_for=self.config_dialog.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=_("Boxes content profile duplicated"),
            )
            dialog.format_secondary_text(_(
                "You edited a predefined boxes content profile, which cannot "
                "be changed by the user. A copy was created and selected. The "
                "changes are applied to that copy."
            ))
            dialog.run()
            dialog.destroy()

        return new_profile_key

    # boxes content profiles getters and setters

    def _is_predef_content_profile(self, def_key=None):
        if def_key is None:
            def_key = self.ftv._config.get("boxes.familytreeview-boxes-selected-def-key")
        return def_key in PREDEF_BOXES_CONTENT_PROFILES

    def _get_content_profile_name(self):
        name = self._get_content_profile_element(0)
        if name is not None:
            if self._is_predef_content_profile():
                return _(name)
            # custom def
            return name
        selected_def_key = self.ftv._config.get("boxes.familytreeview-boxes-selected-def-key")
        return selected_def_key

    def _set_content_profile_name(self, name):
        self._set_content_profile_element(0, name)

    def _get_person_width(self):
        return self._get_content_profile_element(1)

    def _set_person_width(self, person_width):
        self._set_content_profile_element(1, person_width)

    def _get_box_content_item_defs(self, box_type):
        if box_type == "person":
            i = 2
        else:
            i = 3
        return self._get_content_profile_element(i)

    def _set_box_content_item_defs(self, box_type, content_types):
        if box_type == "person":
            i = 2
        else:
            i = 3
        self._set_content_profile_element(i, content_types)

    def _set_content_profile_element(self, i, val):
        self.current_content_profile[i] = val

    def _get_content_profile_element(self, i):
        if self.current_content_profile is not None:
            return deepcopy(self.current_content_profile[i])

        # called before opening the dialog
        selected_def_key = self.ftv._config.get("boxes.familytreeview-boxes-selected-def-key")
        if self._is_predef_content_profile(selected_def_key):
            content_types = PREDEF_BOXES_CONTENT_PROFILES[selected_def_key]
        else:
            custom_defs = self.ftv._config.get("boxes.familytreeview-boxes-custom-defs")
            if selected_def_key in custom_defs:
                content_types = custom_defs[selected_def_key]
            else:
                content_types = PREDEF_BOXES_CONTENT_PROFILES["regular"]
        return deepcopy(content_types[i])

    def _remove_content_profile(self, def_key):
        if self._is_predef_content_profile(def_key):
            # Predefined definitions cannot be removed.
            return
        custom_defs = self.ftv._config.get("boxes.familytreeview-boxes-custom-defs")
        custom_defs.pop(def_key)
        self.ftv._config.set("boxes.familytreeview-boxes-custom-defs", custom_defs)
