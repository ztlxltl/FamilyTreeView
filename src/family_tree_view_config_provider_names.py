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

from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.lib import Name, Surname, NameOriginType
from gramps.gen.utils.keyword import (
    get_keywords,
    get_translation_from_keyword,
)

if TYPE_CHECKING:
    from family_tree_view import FamilyTreeView


_ = GRAMPS_LOCALE.translation.gettext

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

def names_page(ftv: "FamilyTreeView", configdialog):
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
    for num, name, fmt_str, act in name_formats:
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
    def _cb_combo_changed(combo, constant):
        ftv._config.set(constant, name_format_options[combo.get_active()][0])
        _fill_preview_model(ftv, preview_model)
    name_format_combo = configdialog.add_combo(
        grid,
        _("Default name format for the tree"),
        row,
        "names.familytreeview-abbrev-name-format-id",
        name_format_options,
        callback=_cb_combo_changed
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
        _("Use always this name format (never name-specific \"Display as:\" name format)"),
        row,
        "names.familytreeview-abbrev-name-format-always",
        stop=3 # same width as spinners and combos
    )

    row += 1
    label = configdialog.add_text(
        grid,
        _("Name Abbreviation"),
        row, stop=3, bold=True
    )
    label.set_xalign(0)
    label.set_margin_top(20)

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
        ftv._config.set("names.familytreeview-name-abbrev-rules", deepcopy(DEFAULT_ABBREV_RULES))
        # update rule model
        _fill_abbrev_rules_model_from_config(ftv, abbrev_rules_model)
        # deselect rule
        abbrev_rules_tree_view.get_selection().unselect_all()

        _fill_preview_model(ftv, preview_model)

        # cb_update_config connected doesn't work, even when using a shallow or deep copy.
        # Update explicitly:
        ftv.cb_update_config(None, None, None, None)
    button.connect("clicked", _cb_reset_rules)
    button.set_margin_top(20) # same as label
    grid.attach(button, 3, row-1, 1, 2)

    row += 1
    rules_hbox = Gtk.Box()

    rules_scrolled = Gtk.ScrolledWindow()
    rules_scrolled.set_vexpand(True)
    rules_scrolled.set_hexpand(True)
    abbrev_rules_model = Gtk.ListStore(int, str, str, str, bool, str)
    _fill_abbrev_rules_model_from_config(ftv, abbrev_rules_model)
    abbrev_rules_tree_view = Gtk.TreeView(model=abbrev_rules_model)
    def _cb_rule_selection_changed(selection):
        if selection.count_selected_rows() > 0:
            selected_path = selection.get_selected_rows()[1][0].to_string()
            rule_i = int(selected_path)
            rules_config = ftv._config.get("names.familytreeview-name-abbrev-rules")
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
        abbrev_rules_model[path][1] = action_model[new_iter][0]
        abbrev_rules_model[path][2] = action_model[new_iter][1] # update translated which is displayed
        rules_config = ftv._config.get("names.familytreeview-name-abbrev-rules")
        rule = list(rules_config[int(path)]) # tuple, no item assignment
        rule[0] = abbrev_rules_model[path][1]
        rules_config[int(path)] = tuple(rule)
        ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
        _fill_abbrev_rules_model_from_config(ftv, abbrev_rules_model)
        abbrev_rules_tree_view.get_selection().unselect_all()

        _fill_preview_model(ftv, preview_model)

        # cb_update_config connected doesn't work, even when using a shallow or deep copy.
        # Update explicitly:
        ftv.cb_update_config(None, None, None, None)
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
        abbrev_rules_model[path][4] = not abbrev_rules_model[path][4]
        rules_config = ftv._config.get("names.familytreeview-name-abbrev-rules")
        rule = list(rules_config[int(path)]) # tuple, no item assignment
        rule[2] = abbrev_rules_model[path][4]
        rules_config[int(path)] = tuple(rule)
        ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
        _fill_abbrev_rules_model_from_config(ftv, abbrev_rules_model)
        abbrev_rules_tree_view.get_selection().unselect_all()

        _fill_preview_model(ftv, preview_model)

        # cb_update_config connected doesn't work, even when using a shallow or deep copy.
        # Update explicitly:
        ftv.cb_update_config(None, None, None, None)
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
        rules_config = ftv._config.get("names.familytreeview-name-abbrev-rules")
        new_rule = ("abbrev", ["given"], True)
        selection = abbrev_rules_tree_view.get_selection()
        if selection.count_selected_rows() == 0:
            rule_i = len(rules_config)
        else:
            # insert after current selection
            rule_i = int(selection.get_selected_rows()[1][0].to_string())+1
        rules_config.insert(rule_i, new_rule)
        ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
        _fill_abbrev_rules_model_from_config(ftv, abbrev_rules_model)
        abbrev_rules_tree_view.get_selection().select_iter(abbrev_rules_model.get_iter((rule_i,)))

        _fill_preview_model(ftv, preview_model)

        # cb_update_config connected doesn't work, even when using a shallow or deep copy.
        # Update explicitly:
        ftv.cb_update_config(None, None, None, None)
    add_button.connect("clicked", _cb_add_button_clicked)
    button_box.add(add_button)
    duplicate_button = Gtk.Button(image=Gtk.Image(icon_name="edit-copy"))
    duplicate_button.set_sensitive(False) # initially no selection
    def _cb_duplicate_button_clicked(button):
        selection = abbrev_rules_tree_view.get_selection()
        if selection.count_selected_rows() > 0:
            rules_config = ftv._config.get("names.familytreeview-name-abbrev-rules")
            rule_i = int(selection.get_selected_rows()[1][0].to_string())
            new_rule = deepcopy(rules_config[rule_i])
            rules_config.insert(rule_i, new_rule)
            ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
            _fill_abbrev_rules_model_from_config(ftv, abbrev_rules_model)
            abbrev_rules_tree_view.get_selection().select_iter(abbrev_rules_model.get_iter((rule_i+1,)))

            _fill_preview_model(ftv, preview_model)

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            ftv.cb_update_config(None, None, None, None)
    duplicate_button.connect("clicked", _cb_duplicate_button_clicked)
    button_box.add(duplicate_button)
    up_button = Gtk.Button(image=Gtk.Image(icon_name="go-up-symbolic"))
    up_button.set_sensitive(False) # initially no selection
    def _cb_up_button_clicked(button):
        selection = abbrev_rules_tree_view.get_selection()
        if selection.count_selected_rows() > 0:
            rules_config = ftv._config.get("names.familytreeview-name-abbrev-rules")
            rule_i = int(selection.get_selected_rows()[1][0].to_string())
            rules_config.insert(rule_i-1, rules_config.pop(rule_i))
            ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
            _fill_abbrev_rules_model_from_config(ftv, abbrev_rules_model)
            abbrev_rules_tree_view.get_selection().select_iter(abbrev_rules_model.get_iter((rule_i-1,)))

            _fill_preview_model(ftv, preview_model)

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            ftv.cb_update_config(None, None, None, None)
    up_button.connect("clicked", _cb_up_button_clicked)
    button_box.add(up_button)
    down_button = Gtk.Button(image=Gtk.Image(icon_name="go-down-symbolic"))
    down_button.set_sensitive(False) # initially no selection
    def _cb_down_button_clicked(button):
        selection = abbrev_rules_tree_view.get_selection()
        if selection.count_selected_rows() > 0:
            rules_config = ftv._config.get("names.familytreeview-name-abbrev-rules")
            rule_i = int(selection.get_selected_rows()[1][0].to_string())
            rules_config.insert(rule_i+1, rules_config.pop(rule_i))
            ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
            _fill_abbrev_rules_model_from_config(ftv, abbrev_rules_model)
            abbrev_rules_tree_view.get_selection().select_iter(abbrev_rules_model.get_iter((rule_i+1,)))

            _fill_preview_model(ftv, preview_model)

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            ftv.cb_update_config(None, None, None, None)
    down_button.connect("clicked", _cb_down_button_clicked)
    button_box.add(down_button)
    remove_button = Gtk.Button(image=Gtk.Image(icon_name="list-remove"))
    remove_button.set_sensitive(False) # initially no selection
    def _cb_remove_button_clicked(button):
        selection = abbrev_rules_tree_view.get_selection()
        if selection.count_selected_rows() > 0:
            rules_config = ftv._config.get("names.familytreeview-name-abbrev-rules")
            rule_i = int(selection.get_selected_rows()[1][0].to_string())
            rules_config.pop(rule_i)
            ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)
            _fill_abbrev_rules_model_from_config(ftv, abbrev_rules_model)
            abbrev_rules_tree_view.get_selection().unselect_all()

            _fill_preview_model(ftv, preview_model)

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            ftv.cb_update_config(None, None, None, None)
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
        abbrev_rules_model[rule_i][3] = _get_name_part_types_str(name_part_types)
        rules_config = ftv._config.get("names.familytreeview-name-abbrev-rules")
        rule = list(rules_config[rule_i]) # tuple, no item assignment
        rule[1] = name_part_types
        rules_config[rule_i] = tuple(rule)
        ftv._config.set("names.familytreeview-name-abbrev-rules", rules_config)

        # cb_update_config connected doesn't work, even when using a shallow or deep copy.
        # Update explicitly:
        ftv.cb_update_config(None, None, None, None)
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
    preview_model = Gtk.ListStore(str, str, str, str, str)

    _fill_preview_model(ftv, preview_model)
    ftv.uistate.connect("nameformat-changed", lambda *_: _fill_preview_model(ftv, preview_model))

    preview_tree_view = Gtk.TreeView(model=preview_model)
    preview_tree_view.get_selection().set_mode(Gtk.SelectionMode.NONE)

    renderer = Gtk.CellRendererText()
    column = Gtk.TreeViewColumn("Abbreviated Name", renderer, text=0)
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

    return (_("Names"), grid)

def _fill_abbrev_rules_model_from_config(ftv: "FamilyTreeView", abbrev_rules_model):
    abbrev_rules_model.clear()
    rules_config = ftv._config.get("names.familytreeview-name-abbrev-rules")
    for rule_i, (action, name_part_types, reverse) in enumerate(rules_config):
        if action == "abbrev":
            translation = _("abbreviate")
        elif action == "remove":
            translation = _("remove")
        name_part_types_str = _get_name_part_types_str(name_part_types)
        abbrev_rules_model.append([rule_i+1, action, translation, name_part_types_str, reverse, ""])

def _get_name_part_types_str(name_part_types):
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

def _fill_preview_model(ftv: "FamilyTreeView", preview_model):
    preview_model.clear()
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

    num = ftv.abbrev_name_display.get_num_for_name_abbrev(example_name)
    abbr_name_list, step_descriptions = ftv.abbrev_name_display.get_abbreviated_names(example_name, num=num, return_step_description=True)
    for abbrev_name, step_info in zip(abbr_name_list, step_descriptions):
        preview_model.append([
            abbrev_name,
            "-" if step_info[0] is None else str(step_info[0]+1), # rule
            "-" if step_info[1] is None else str(step_info[1]+1), # rule step
            step_info[9], # description
            ""
        ])