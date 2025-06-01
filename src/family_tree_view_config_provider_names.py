#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2025-      ztlxltl
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#


from copy import deepcopy
from typing import TYPE_CHECKING

from gi.repository import Gtk, Pango

from gramps.gen.display.name import _F_FN, displayer as name_displayer
from gramps.gen.lib import Name, Surname, NameOriginType
from gramps.gen.utils.keyword import (
    get_keywords,
    get_translation_from_keyword,
)

from family_tree_view_utils import get_gettext
if TYPE_CHECKING:
    from family_tree_view_config_provider import FamilyTreeViewConfigProvider


_ = get_gettext()

NAME_PART_TYPES = [
    ("given", _("Given")),
    ("given[ncnf]", _("Given (non-call, non-first)")),
    ("given0", _("First Given")),
    ("call", _("Call Name")),
    ("title", _("Title")),
    ("suffix", _("Suffix")),
    ("nick", _("Nick Name")),
    ("primary-prefix", _("Primary Prefix")),
    ("primary-surname", _("Primary Surname")),
    ("primary-connector", _("Primary Connector")),
    ("prefix", _("Prefix")),
    ("surname", _("Surname")),
    ("connector", _("Connector")),
    ("famnick", _("Family Nick Name")),
]

DEFAULT_ABBREV_RULES = [
    ("abbrev", ["given[ncnf]", "nick", "given0", "call"], True),
    ("abbrev", ["given"], True),
    ("abbrev", ["prefix", "connector", "primary-connector"], True),
    ("abbrev", ["primary-prefix"], True),
    ("abbrev", ["surname", "famnick"], True),
    ("remove", ["given[ncnf]"], True),
    ("remove", ["prefix", "connector"], True),
    ("remove", ["title", "suffix"], True),
    ("remove", ["primary-prefix", "primary-connector"], True),
    ("remove", ["surname", "famnick"], True),
    ("abbrev", ["primary-surname"], True),
    ("remove", ["given", "nick", "given0", "call"], True),
]

class FamilyTreeViewConfigProviderNames:
    def __init__(self, config_provider: "FamilyTreeViewConfigProvider"):
        self.config_provider = config_provider
        self.ftv = self.config_provider.ftv

        self.abbrev_rules_model = None
        self.preview_model = None

    def names_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        # TODO Is this list constructed correctly?
        name_format_options = []
        name_formats = [
            (0, _("Default format (defined by Gramps preferences)"), "", True)
        ]
        name_formats.extend(name_displayer.get_name_format())
        active_num = self.ftv._config.get("names.familytreeview-abbrev-name-format-id")
        active_i = None
        for i, (num, name, fmt_str, act) in enumerate(name_formats):
            if active_i is None and num == active_num:
                active_i = i
            if num == 0:
                name_format_options.append((num, name))
                continue

            translation = fmt_str
            for key in get_keywords():
                if key in translation:
                    translation = translation.replace(
                        key, get_translation_from_keyword(key)
                    )
            name_format_options.append((num, translation))

        row += 1
        def _cb_name_format_combo_changed(combo, constant):
            self.ftv._config.set(constant, name_format_options[combo.get_active()][0])
            self.ftv.emit("abbrev-rules-changed")
            self._update_name_preview()
            self._fill_preview_model()
        name_format_combo = configdialog.add_combo(
            grid,
            _("Default name format for the tree"),
            row,
            "names.familytreeview-abbrev-name-format-id",
            name_format_options,
            callback=_cb_name_format_combo_changed,
            setactive=active_i,
        )
        name_format_combo.get_cells()[0].set_property("ellipsize", Pango.EllipsizeMode.END)
        combo_label = grid.get_child_at(1, row)
        # move 1 grid column to the right
        grid.remove(combo_label)
        grid.remove(name_format_combo)
        grid.attach(combo_label, 1, row, 1, 1)
        grid.attach(name_format_combo, 2, row, 2, 1)

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Use always this name format in the tree (never name-specific \"Display as:\" name format)"),
            row,
            "names.familytreeview-abbrev-name-format-always",
            stop=4,
            extra_callback=lambda *args: self.ftv.emit("abbrev-rules-changed"),
        )

        row += 1
        label = Gtk.Label()
        label.set_markup(_("<b>Custom formatting/emphasis for the tree</b>"))
        label.set_halign(Gtk.Align.START)
        label.set_margin_top(20)
        grid.attach(label, 1, row, 1, 1)

        row += 1
        label = Gtk.Label(_("Display ALL CAPS name parts in the tree as:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 1, 1)
        all_caps_style_options = [
            ("ignore", _("Ignore all caps")),
            ("all_caps", _("ALL CAPS (keep as defined)")),
            # Use <small> since proper small caps doesn't work with canvas zooming.
            ("small_caps", _("S<small>MALL</small> C<small>APS</small>")),
            ("petite_caps", _("P<small><small>ETITE</small></small> C<small><small>APS</small></small>")),
            ("bold", _("<b>Bold</b>")),
            ("italic", _("<i>Italic</i>")),
            ("underline", _("<u>Underline</u>")),
        ]
        all_caps_style_list_store = Gtk.ListStore(str, str)
        for opt in all_caps_style_options:
            all_caps_style_list_store.append(opt)
        all_caps_combo = Gtk.ComboBox.new_with_model(all_caps_style_list_store)
        renderer = Gtk.CellRendererText()
        all_caps_combo.pack_start(renderer, True)
        all_caps_combo.add_attribute(renderer, "markup", 1)
        try:
            active_index = [opt[0] for opt in all_caps_style_options].index(
                self.ftv._config.get("names.familytreeview-abbrev-name-all-caps-style")
            )
        except ValueError:
            active_index = 1 # all_caps
        all_caps_combo.set_active(active_index)
        def _cb_all_caps_combo_changed(combo):
            self.ftv._config.set(
                "names.familytreeview-abbrev-name-all-caps-style",
                all_caps_style_options[combo.get_active()][0]
            )
            self.ftv.emit("abbrev-rules-changed")
            self._update_name_preview()
            self._fill_preview_model()
        all_caps_combo.connect("changed", _cb_all_caps_combo_changed)
        grid.attach(all_caps_combo, 2, row, 2, 1)

        row += 1
        label = Gtk.Label(_("Emphasize call name in the tree with:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 1, 1)
        call_name_style_options = [
            ("none", _("None")),
            ("all_caps", _("ALL CAPS")),
            # Use <small> since proper small caps doesn't work with canvas zooming.
            ("small_caps", _("S<small>MALL</small> C<small>APS</small>")),
            ("petite_caps", _("P<small><small>ETITE</small></small> C<small><small>APS</small></small>")),
            ("bold", _("<b>Bold</b>")),
            ("italic", _("<i>Italic</i>")),
            ("underline", _("<u>Underline</u>")),
        ]
        call_name_style_list_store = Gtk.ListStore(str, str)
        for opt in call_name_style_options:
            call_name_style_list_store.append(opt)
        call_name_style_combo = Gtk.ComboBox.new_with_model(call_name_style_list_store)
        renderer = Gtk.CellRendererText()
        call_name_style_combo.pack_start(renderer, True)
        call_name_style_combo.add_attribute(renderer, "markup", 1)
        try:
            active_index = [opt[0] for opt in call_name_style_options].index(
                self.ftv._config.get("names.familytreeview-abbrev-name-call-name-style")
            )
        except ValueError:
            active_index = 0 # none
        call_name_style_combo.set_active(active_index)
        def _cb_call_name_style_combo_changed(combo):
            self.ftv._config.set(
                "names.familytreeview-abbrev-name-call-name-style",
                call_name_style_options[combo.get_active()][0]
            )
            self.ftv.emit("abbrev-rules-changed")
            self._update_name_preview()
            self._fill_preview_model()
        call_name_style_combo.connect("changed", _cb_call_name_style_combo_changed)
        grid.attach(call_name_style_combo, 2, row, 2, 1)

        row += 1
        label = Gtk.Label(_("When emphasizing, consider as call name:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 1, 1)
        call_name_mode_options = [
            ("call_not_given0", _("Call name if it's not the first given name")),
            ("call_not_only_given", _("Call name if it's not the only given name")),
            ("call", _("Call name")),
            ("call_or_given0", _("Call name or first given name")),
        ]
        call_name_mode_list_store = Gtk.ListStore(str, str)
        for opt in call_name_mode_options:
            call_name_mode_list_store.append(opt)
        call_name_mode_combo = Gtk.ComboBox.new_with_model(call_name_mode_list_store)
        renderer = Gtk.CellRendererText()
        call_name_mode_combo.pack_start(renderer, True)
        call_name_mode_combo.add_attribute(renderer, "text", 1)
        try:
            active_index = [opt[0] for opt in call_name_mode_options].index(
                self.ftv._config.get("names.familytreeview-abbrev-name-call-name-mode")
            )
        except ValueError:
            active_index = 3 # call_or_given0
        call_name_mode_combo.set_active(active_index)
        def _cb_call_name_mode_combo_changed(combo):
            self.ftv._config.set(
                "names.familytreeview-abbrev-name-call-name-mode",
                call_name_mode_options[combo.get_active()][0]
            )
            self.ftv.emit("abbrev-rules-changed")
            self._update_name_preview()
            self._fill_preview_model()
        call_name_mode_combo.connect("changed", _cb_call_name_mode_combo_changed)
        grid.attach(call_name_mode_combo, 2, row, 2, 1)

        row += 1
        label = Gtk.Label(_("Emphasize primary surname in the tree with:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 1, 1)
        primary_surname_style_options = [
            ("none", _("None")),
            ("all_caps", _("ALL CAPS")),
            # Use <small> since proper small caps doesn't work with canvas zooming.
            ("small_caps", _("S<small>MALL</small> C<small>APS</small>")),
            ("petite_caps", _("P<small><small>ETITE</small></small> C<small><small>APS</small></small>")),
            ("bold", _("<b>Bold</b>")),
            ("italic", _("<i>Italic</i>")),
            ("underline", _("<u>Underline</u>")),
        ]
        primary_surname_style_list_store = Gtk.ListStore(str, str)
        for opt in primary_surname_style_options:
            primary_surname_style_list_store.append(opt)
        primary_surname_style_combo = Gtk.ComboBox.new_with_model(primary_surname_style_list_store)
        renderer = Gtk.CellRendererText()
        primary_surname_style_combo.pack_start(renderer, True)
        primary_surname_style_combo.add_attribute(renderer, "markup", 1)
        try:
            active_index = [opt[0] for opt in primary_surname_style_options].index(
                self.ftv._config.get("names.familytreeview-abbrev-name-primary-surname-style")
            )
        except ValueError:
            active_index = 0 # none
        primary_surname_style_combo.set_active(active_index)
        def _cb_primary_surname_style_combo_changed(combo):
            self.ftv._config.set(
                "names.familytreeview-abbrev-name-primary-surname-style",
                primary_surname_style_options[combo.get_active()][0]
            )
            self.ftv.emit("abbrev-rules-changed")
            self._update_name_preview()
            self._fill_preview_model()
        primary_surname_style_combo.connect("changed", _cb_primary_surname_style_combo_changed)
        grid.attach(primary_surname_style_combo, 2, row, 2, 1)

        row += 1
        label = Gtk.Label(_("When emphasizing, consider as primary surname:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 1, 1)
        primary_surname_mode_options = [
            ("primary_surname", _("Primary surname")),
            ("primary_surname_prefix", _("Primary surname and its prefix")),
        ]
        primary_surname_mode_list_store = Gtk.ListStore(str, str)
        for opt in primary_surname_mode_options:
            primary_surname_mode_list_store.append(opt)
        primary_surname_mode_combo = Gtk.ComboBox.new_with_model(primary_surname_mode_list_store)
        renderer = Gtk.CellRendererText()
        primary_surname_mode_combo.pack_start(renderer, True)
        primary_surname_mode_combo.add_attribute(renderer, "text", 1)
        try:
            active_index = [opt[0] for opt in primary_surname_mode_options].index(
                self.ftv._config.get("names.familytreeview-abbrev-name-primary-surname-mode")
            )
        except ValueError:
            active_index = 0 # none
        primary_surname_mode_combo.set_active(active_index)
        def _cb_primary_surname_mode_combo_changed(combo):
            self.ftv._config.set(
                "names.familytreeview-abbrev-name-primary-surname-mode",
                primary_surname_mode_options[combo.get_active()][0]
            )
            self.ftv.emit("abbrev-rules-changed")
            self._update_name_preview()
            self._fill_preview_model()
        primary_surname_mode_combo.connect("changed", _cb_primary_surname_mode_combo_changed)
        grid.attach(primary_surname_mode_combo, 2, row, 2, 1)

        row += 1
        label = Gtk.Label(_("Example:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 1, 1)

        row += 1
        label = Gtk.Label(_("Just the name format:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 1, 1)

        self.name_without_style_label = Gtk.Label()
        self.name_without_style_label.set_halign(Gtk.Align.START)
        grid.attach(self.name_without_style_label, 2, row, 1, 1)

        row += 1
        label = Gtk.Label(_("With custom formatting/emphasis:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 1, 1)

        self.name_with_style_label = Gtk.Label()
        self.name_with_style_label.set_halign(Gtk.Align.START)
        grid.attach(self.name_with_style_label, 2, row, 1, 1)

        self._update_name_preview()

        return grid

    def _update_name_preview(self):
        example_name = self._get_example_name()
        num = self.ftv.abbrev_name_display.get_num_for_name_abbrev(example_name)

        # There is no display_name_format (only display_format for
        # person).
        text = name_displayer.name_formats[num][_F_FN](example_name)
        self.name_without_style_label.set_text(text)

        abbr_name_list = self.ftv.abbrev_name_display.get_abbreviated_names(example_name, num=num)
        markup = abbr_name_list[0] # full name
        self.name_with_style_label.set_markup(markup)

    def name_abbr_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        row += 1
        label = configdialog.add_text(
            grid,
            _("Name Abbreviation"),
            row, stop=3, bold=True
        )
        label.set_xalign(0)

        row += 1
        label = configdialog.add_text(
            grid,
            _("Specify the rules for name abbreviation below"),
            row, stop=3
        )
        label.set_xalign(0)
        label.set_hexpand(True)

        button = Gtk.Button(label=_("Reset abbreviation rules to default"))
        def _cb_reset_rules(button):
            self.ftv._config.set("names.familytreeview-name-abbrev-rules", deepcopy(DEFAULT_ABBREV_RULES))
            self.ftv.emit("abbrev-rules-changed")
            # update rule model
            self._fill_abbrev_rules_model_from_config()
            # deselect rule
            abbrev_rules_tree_view.get_selection().unselect_all()

            self._fill_preview_model()

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            self.ftv.cb_update_config(None, None, None, None)
        button.connect("clicked", _cb_reset_rules)
        button.set_margin_top(20) # same as label
        grid.attach(button, 3, row-1, 1, 2)

        row += 1
        rules_hbox = Gtk.Box()

        rules_scrolled = Gtk.ScrolledWindow()
        rules_scrolled.set_vexpand(True)
        rules_scrolled.set_hexpand(True)
        self.abbrev_rules_model = Gtk.ListStore(int, str, str, str, bool, str)
        self._fill_abbrev_rules_model_from_config()
        abbrev_rules_tree_view = Gtk.TreeView(model=self.abbrev_rules_model)
        def _cb_rule_selection_changed(selection):
            if selection.count_selected_rows() > 0:
                selected_path = selection.get_selected_rows()[1][0].to_string()
                rule_i = int(selected_path)
                rules_config = self.ftv._config.get("names.familytreeview-name-abbrev-rules")
                rule = rules_config[rule_i]
                rule_name_part_types = rule[1]
                for name_part_types_row in name_part_types_model:
                    name_part_types_row[2] = name_part_types_row[0] in rule_name_part_types
                    name_part_types_row[3] = True # activatable
                duplicate_button.set_sensitive(True)
                up_button.set_sensitive(rule_i>0)
                down_button.set_sensitive(rule_i<len(rules_config)-1)
                remove_button.set_sensitive(True)
            else:
                for name_part_types_row in name_part_types_model:
                    name_part_types_row[2] = False # not active
                    name_part_types_row[3] = False # not activatable
                duplicate_button.set_sensitive(False)
                up_button.set_sensitive(False)
                down_button.set_sensitive(False)
                remove_button.set_sensitive(False)
        abbrev_rules_tree_view.get_selection().connect("changed", _cb_rule_selection_changed)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("No."), renderer, text=0)
        abbrev_rules_tree_view.append_column(column)

        # name column
        action_model = Gtk.ListStore(str, str)
        action_model.append(("abbrev", _("abbreviate")))
        action_model.append(("remove", _("remove")))
        renderer = Gtk.CellRendererCombo(model=action_model, editable=True, text_column=1, has_entry=False)
        def _cb_rule_action_changed(renderer, path, new_iter):
            self.abbrev_rules_model[path][1] = action_model[new_iter][0]
            self.abbrev_rules_model[path][2] = action_model[new_iter][1] # update translated which is displayed
            rules_config = self.ftv._config.get("names.familytreeview-name-abbrev-rules")
            rule = list(rules_config[int(path)]) # tuple, no item assignment
            rule[0] =  self.abbrev_rules_model[path][1]
            rules_config[int(path)] = tuple(rule)
            self.ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
            self.ftv.emit("abbrev-rules-changed")
            self._fill_abbrev_rules_model_from_config()
            abbrev_rules_tree_view.get_selection().unselect_all()

            self._fill_preview_model()

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            self.ftv.cb_update_config(None, None, None, None)
        renderer.connect("changed", _cb_rule_action_changed)
        column = Gtk.TreeViewColumn(_("Action"), renderer, text=2)
        abbrev_rules_tree_view.append_column(column)

        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn(_("Name Part Types"), renderer, text=3)
        column.set_resizable(True)
        column.set_expand(True)
        abbrev_rules_tree_view.append_column(column)

        renderer = Gtk.CellRendererToggle()
        def _cb_rule_reverse_toggled(widget, path):
            self.abbrev_rules_model[path][4] = not self.abbrev_rules_model[path][4]
            rules_config = self.ftv._config.get("names.familytreeview-name-abbrev-rules")
            rule = list(rules_config[int(path)]) # tuple, no item assignment
            rule[2] = self.abbrev_rules_model[path][4]
            rules_config[int(path)] = tuple(rule)
            self.ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
            self.ftv.emit("abbrev-rules-changed")
            self._fill_abbrev_rules_model_from_config()
            abbrev_rules_tree_view.get_selection().unselect_all()

            self._fill_preview_model()

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            self.ftv.cb_update_config(None, None, None, None)
        renderer.connect("toggled", _cb_rule_reverse_toggled)
        column = Gtk.TreeViewColumn(_("Start at End of Name"), renderer, active=4)
        abbrev_rules_tree_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=5)
        abbrev_rules_tree_view.append_column(column)

        rules_scrolled.add(abbrev_rules_tree_view)
        rules_hbox.add(rules_scrolled)

        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        add_button = Gtk.Button(image=Gtk.Image(icon_name="list-add"))
        def _cb_add_button_clicked(button):
            rules_config = self.ftv._config.get("names.familytreeview-name-abbrev-rules")
            new_rule = ("abbrev", ["given"], True)
            selection = abbrev_rules_tree_view.get_selection()
            if selection.count_selected_rows() == 0:
                rule_i = len(rules_config)
            else:
                # insert after current selection
                rule_i = int(selection.get_selected_rows()[1][0].to_string())+1
            rules_config.insert(rule_i, new_rule)
            self.ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
            self.ftv.emit("abbrev-rules-changed")
            self._fill_abbrev_rules_model_from_config()
            abbrev_rules_tree_view.get_selection().select_iter(self.abbrev_rules_model.get_iter((rule_i,)))

            self._fill_preview_model()

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            self.ftv.cb_update_config(None, None, None, None)
        add_button.connect("clicked", _cb_add_button_clicked)
        button_box.add(add_button)
        duplicate_button = Gtk.Button(image=Gtk.Image(icon_name="edit-copy"))
        duplicate_button.set_sensitive(False) # initially no selection
        def _cb_duplicate_button_clicked(button):
            selection = abbrev_rules_tree_view.get_selection()
            if selection.count_selected_rows() > 0:
                rules_config = self.ftv._config.get("names.familytreeview-name-abbrev-rules")
                rule_i = int(selection.get_selected_rows()[1][0].to_string())
                new_rule = deepcopy(rules_config[rule_i])
                rules_config.insert(rule_i, new_rule)
                self.ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
                self.ftv.emit("abbrev-rules-changed")
                self._fill_abbrev_rules_model_from_config()
                abbrev_rules_tree_view.get_selection().select_iter(self.abbrev_rules_model.get_iter((rule_i+1,)))

                self._fill_preview_model()

                # cb_update_config connected doesn't work, even when using a shallow or deep copy.
                # Update explicitly:
                self.ftv.cb_update_config(None, None, None, None)
        duplicate_button.connect("clicked", _cb_duplicate_button_clicked)
        button_box.add(duplicate_button)
        up_button = Gtk.Button(image=Gtk.Image(icon_name="go-up-symbolic"))
        up_button.set_sensitive(False) # initially no selection
        def _cb_up_button_clicked(button):
            selection = abbrev_rules_tree_view.get_selection()
            if selection.count_selected_rows() > 0:
                rules_config = self.ftv._config.get("names.familytreeview-name-abbrev-rules")
                rule_i = int(selection.get_selected_rows()[1][0].to_string())
                rules_config.insert(rule_i-1, rules_config.pop(rule_i))
                self.ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
                self.ftv.emit("abbrev-rules-changed")
                self._fill_abbrev_rules_model_from_config()
                abbrev_rules_tree_view.get_selection().select_iter(self.abbrev_rules_model.get_iter((rule_i-1,)))

                self._fill_preview_model()

                # cb_update_config connected doesn't work, even when using a shallow or deep copy.
                # Update explicitly:
                self.ftv.cb_update_config(None, None, None, None)
        up_button.connect("clicked", _cb_up_button_clicked)
        button_box.add(up_button)
        down_button = Gtk.Button(image=Gtk.Image(icon_name="go-down-symbolic"))
        down_button.set_sensitive(False) # initially no selection
        def _cb_down_button_clicked(button):
            selection = abbrev_rules_tree_view.get_selection()
            if selection.count_selected_rows() > 0:
                rules_config = self.ftv._config.get("names.familytreeview-name-abbrev-rules")
                rule_i = int(selection.get_selected_rows()[1][0].to_string())
                rules_config.insert(rule_i+1, rules_config.pop(rule_i))
                self.ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
                self.ftv.emit("abbrev-rules-changed")
                self._fill_abbrev_rules_model_from_config()
                abbrev_rules_tree_view.get_selection().select_iter(self.abbrev_rules_model.get_iter((rule_i+1,)))

                self._fill_preview_model()

                # cb_update_config connected doesn't work, even when using a shallow or deep copy.
                # Update explicitly:
                self.ftv.cb_update_config(None, None, None, None)
        down_button.connect("clicked", _cb_down_button_clicked)
        button_box.add(down_button)
        remove_button = Gtk.Button(image=Gtk.Image(icon_name="list-remove"))
        remove_button.set_sensitive(False) # initially no selection
        def _cb_remove_button_clicked(button):
            selection = abbrev_rules_tree_view.get_selection()
            if selection.count_selected_rows() > 0:
                rules_config = self.ftv._config.get("names.familytreeview-name-abbrev-rules")
                rule_i = int(selection.get_selected_rows()[1][0].to_string())
                rules_config.pop(rule_i)
                self.ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
                self.ftv.emit("abbrev-rules-changed")
                self._fill_abbrev_rules_model_from_config()
                abbrev_rules_tree_view.get_selection().unselect_all()

                self._fill_preview_model()

                # cb_update_config connected doesn't work, even when using a shallow or deep copy.
                # Update explicitly:
                self.ftv.cb_update_config(None, None, None, None)
        remove_button.connect("clicked", _cb_remove_button_clicked)
        button_box.add(remove_button)
        rules_hbox.add(button_box)

        grid.attach(rules_hbox, 1, row, 3, 1)

        row += 1
        name_part_types_scrolled = Gtk.ScrolledWindow()
        name_part_types_scrolled.set_vexpand(True)
        name_part_types_scrolled.set_hexpand(True)
        name_part_types_model = Gtk.ListStore(str, str, bool, bool, str)
        for name_part_type, name_part_type_translated in NAME_PART_TYPES:
            name_part_types_model.append([
                name_part_type,
                name_part_type_translated,
                False, # no rule selected
                False, # no rule selected
                ""
            ])

        name_part_types_tree_view = Gtk.TreeView(model=name_part_types_model)
        name_part_types_tree_view.get_selection().set_mode(Gtk.SelectionMode.NONE)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Name Part"), renderer, text=1)
        name_part_types_tree_view.append_column(column)

        renderer = Gtk.CellRendererToggle()
        def _cb_name_part_toggled(widget, path):
            # Toggled name part type needs to be added to or removed from selected rule.
            name_part_types_model[path][2] = not name_part_types_model[path][2]
            name_part_types = [
                name_part_types_row[0]
                for name_part_types_row in name_part_types_model
                if name_part_types_row[2]
            ]
            selected_path = abbrev_rules_tree_view.get_selection().get_selected_rows()[1][0].to_string()
            rule_i = int(selected_path)
            self.abbrev_rules_model[rule_i][3] = self._get_name_part_types_str(name_part_types)
            rules_config = self.ftv._config.get("names.familytreeview-name-abbrev-rules")
            rule = list(rules_config[rule_i]) # tuple, no item assignment
            rule[1] = name_part_types
            rules_config[rule_i] = tuple(rule)
            self.ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
            self.ftv.emit("abbrev-rules-changed")

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            self.ftv.cb_update_config(None, None, None, None)
        renderer.connect("toggled", _cb_name_part_toggled)
        column = Gtk.TreeViewColumn(_("Use in selected Rule"), renderer, active=2, activatable=3)
        name_part_types_tree_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=4)
        name_part_types_tree_view.append_column(column)

        name_part_types_scrolled.add(name_part_types_tree_view)
        grid.attach(name_part_types_scrolled, 1, row, 3, 1)

        row += 1
        preview_scrolled = Gtk.ScrolledWindow()
        preview_scrolled.set_vexpand(True)
        preview_scrolled.set_hexpand(True)
        self.preview_model = Gtk.ListStore(str, str, str, str, str)

        self._fill_preview_model()
        self.ftv.uistate.connect("nameformat-changed", lambda *_: self._fill_preview_model())

        preview_tree_view = Gtk.TreeView(model=self.preview_model)
        preview_tree_view.get_selection().set_mode(Gtk.SelectionMode.NONE)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Abbreviated Name", renderer, markup=0)
        preview_tree_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Rule", renderer, text=1)
        preview_tree_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Rule Step", renderer, text=2)
        preview_tree_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Description", renderer, text=3)
        preview_tree_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=4)
        preview_tree_view.append_column(column)

        preview_scrolled.add(preview_tree_view)
        grid.attach(preview_scrolled, 1, row, 3, 1)

        return grid

    def _fill_abbrev_rules_model_from_config(self):
        if self.abbrev_rules_model is None:
            return

        self.abbrev_rules_model.clear()
        rules_config = self.ftv._config.get("names.familytreeview-name-abbrev-rules")
        for rule_i, (action, name_part_types, reverse) in enumerate(rules_config):
            if action == "abbrev":
                translation = _("abbreviate")
            elif action == "remove":
                translation = _("remove")
            name_part_types_str = self._get_name_part_types_str(name_part_types)
            self.abbrev_rules_model.append([rule_i+1, action, translation, name_part_types_str, reverse, ""])

    def _get_name_part_types_str(self, name_part_types):
        active_name_part_types = []
        for part_type in name_part_types:
            x = [
                PART_TYPE[1]
                for PART_TYPE in NAME_PART_TYPES
                if PART_TYPE[0] == part_type
            ]
            if len(x) > 0:
                active_name_part_types.append(x[0])
        name_part_types_str = ", ".join(active_name_part_types)
        return name_part_types_str

    def _fill_preview_model(self):
        if self.preview_model is None:
            return

        self.preview_model.clear()
        example_name = self._get_example_name()

        num = self.ftv.abbrev_name_display.get_num_for_name_abbrev(example_name)
        abbr_name_list, step_descriptions = self.ftv.abbrev_name_display.get_abbreviated_names(example_name, num=num, return_step_description=True)
        for abbrev_name, step_info in zip(abbr_name_list, step_descriptions):
            self.preview_model.append([
                abbrev_name,
                "-" if step_info[0] is None else str(step_info[0]+1), # rule
                "-" if step_info[1] is None else str(step_info[1]+1), # rule step
                step_info[9], # description
                ""
            ])

    def _get_example_name(self):
        example_name = Name()
        example_name.set_first_name("Edwin Jose")
        example_name.set_call_name("Jose")
        example_name.set_title("Dr.")
        example_name.set_suffix("Sr")
        example_name.set_nick_name("Ed")

        example_surname_1 = Surname()
        example_surname_1.set_primary(True)
        example_surname_1.set_prefix("von der")
        example_surname_1.set_surname("Smith")
        example_surname_1.set_connector("and")
        example_name.add_surname(example_surname_1)

        example_surname_2 = Surname()
        example_surname_2.set_primary(False)
        example_surname_2.set_surname("Weston")
        example_name.add_surname(example_surname_2)

        example_surname_3 = Surname()
        example_surname_3.set_primary(False)
        example_surname_3.set_surname("Wilson")
        example_surname_3.set_origintype(NameOriginType(NameOriginType.PATRONYMIC))
        example_name.add_surname(example_surname_3)

        example_name.set_family_nick_name("Underhills")

        return example_name