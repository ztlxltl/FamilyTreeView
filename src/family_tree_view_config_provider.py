#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2024-      ztlxltl
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

from gi.repository import Gtk

from gramps.gen.config import config
from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.lib.eventtype import EventType

from family_tree_view_config_provider_names import names_page, DEFAULT_ABBREV_RULES
if TYPE_CHECKING:
    from family_tree_view import FamilyTreeView


_ = GRAMPS_LOCALE.translation.gettext

class FamilyTreeViewConfigProvider:
    def __init__(self, ftv: "FamilyTreeView"):
        self.ftv = ftv
        self.badge_manager = ftv.badge_manager

    @staticmethod
    def get_config_settings():
        default_event_types_show_description = [
            EventType.RELIGION,
            EventType.OCCUPATION,
        ]
        return (
            ("appearance.familytreeview-num-ancestor-generations-default", 2),
            ("appearance.familytreeview-num-descendant-generations-default", 2),
            ("appearance.familytreeview-highlight-root-person", True),
            ("appearance.familytreeview-show-deceased-ribbon", True),
            ("appearance.familytreeview-filter-person-gray-out", True),
            ("appearance.familytreeview-person-image-filter", 0),
            ("appearance.familytreeview-timeline-mode-default-person", 3),
            ("appearance.familytreeview-timeline-mode-default-family", 3),
            ("appearance.familytreeview-timeline-short-age", True),
            ("appearance.familytreeview-timeline-event-types-visible", {
                event_name: True
                for i, event_str, event_name in EventType._DATAMAP
            }),
            ("appearance.familytreeview-timeline-event-types-show-description", {
                event_name: i in default_event_types_show_description
                for i, event_str, event_name in EventType._DATAMAP
            }),

            ("interaction.familytreeview-person-single-click-action", 1),
            ("interaction.familytreeview-person-double-click-action", 3),
            ("interaction.familytreeview-family-single-click-action", 1),
            ("interaction.familytreeview-family-double-click-action", 3),
            ("interaction.familytreeview-double-click-timeout-milliseconds", 200),
            ("interaction.familytreeview-family-info-box-set-active-button", False),
            ("interaction.familytreeview-printing-scale-to-page", False),

            ("badges.familytreeview-badges-active", { # most examples are turned off by default
                "num_citations": {"person": False, "family": False},
                "num_events_without_citations": {"person": False, "family": False},
                "num_children": {"person": False, "family": False},
                "num_other_families": {"person": False, "family": False},
                "filter_result": {"person": True, "family": False},
                "gramps_id": {"person": False, "family": False},
                "gramps_handle": {"person": False, "family": False},
            }),

            ("names.familytreeview-abbrev-name-format-id", 0),
            ("names.familytreeview-abbrev-name-format-always", True),
            ("names.familytreeview-abbrev-name-all-caps-style", 0),
            ("names.familytreeview-name-abbrev-rules", deepcopy(DEFAULT_ABBREV_RULES)),

            ("expanders.familytreeview-expander-types-shown", {
                "parents": {"default_shown": True, "default_hidden": True},
                "other_parents": {"default_shown": True, "default_hidden": True},
                "siblings": {"default_shown": True, "default_hidden": True},
                "other_families": {"default_shown": True, "default_hidden": True},
                "spouses_other_families": {"default_shown": True, "default_hidden": True},
                "children": {"default_shown": True, "default_hidden": True},
            }),
            ("expanders.familytreeview-expander-types-expanded", {
                "parents": None, # controlled by generation num-ancestor-generations-default
                "other_parents": False,
                "siblings": False,
                "other_families": False,
                "spouses_other_families": False,
                "children": None, # controlled by generation num-descendant-generations-default
            }),

            ("experimental.familytreeview-adaptive-ancestor-generation-dist", False),
            ("experimental.familytreeview-connection-follow-on-click", False),
            ("experimental.familytreeview-canvas-font-size-ppi", 96),
        )

    @staticmethod
    def config_connect(_config, cb_update_config):
        for config_name, *_ in FamilyTreeViewConfigProvider.get_config_settings():
            _config.connect(config_name, cb_update_config)

        FamilyTreeViewConfigProvider.ensure_valid_config(_config)

    @staticmethod
    def ensure_valid_config(_config):
        for key in [
            "appearance.familytreeview-timeline-event-types-visible",
            "appearance.familytreeview-timeline-event-types-show-description",
        ]:
            event_types_config = _config.get(key)
            default_value = FamilyTreeViewConfigProvider.get_default_value(key)
            if not isinstance(event_types_config, dict):
                _config.set(key, default_value)
            else:
                changed = False
                for i, s, event_type_name in EventType._DATAMAP:
                    if event_type_name not in event_types_config:
                        event_types_config[event_type_name] = default_value[event_type_name]
                        changed = True
                if changed:
                    _config.set(key, event_types_config)

        key = "badges.familytreeview-badges-active"
        badge_config = _config.get(key)
        default_value = FamilyTreeViewConfigProvider.get_default_value(key)
        if not isinstance(badge_config, dict):
            _config.set(key, default_value)
        else:
            changed = False
            for badge_id in badge_config:
                if not isinstance(badge_config[badge_id], dict):
                    if badge_id in default_value:
                        badge_config[badge_id] = default_value[badge_id]
                    else:
                        badge_config[badge_id] = {"person": False, "family": False}
                    changed = True
                else:
                    for badge_loc in ["person", "family"]:
                        if badge_loc not in badge_config[badge_id]:
                            badge_config[badge_id][badge_loc] = False # default
                            changed = True
            if changed:
                _config.set(key, badge_config)

        for key in [
            "expanders.familytreeview-expander-types-shown",
            "expanders.familytreeview-expander-types-expanded"
        ]:
            expander_config = _config.get(key)
            default_value = FamilyTreeViewConfigProvider.get_default_value(key)
            if not isinstance(expander_config, dict):
                _config.set(key, default_value)
            else:
                changed = False
                for expander_type in [
                    "parents",
                    "other_parents",
                    "siblings",
                    "other_families",
                    "spouses_other_families",
                    "children",
                ]:
                    if (
                        expander_type not in expander_config
                        or (isinstance(default_value[expander_type], dict) and not isinstance(expander_config[expander_type], dict))
                    ):
                        expander_config[expander_type] = default_value[expander_type]
                        changed = True
                    elif isinstance(expander_config[expander_type], dict):
                        # "expanders.familytreeview-expander-types-shown"
                        for sub_key in ["default_shown", "default_hidden"]:
                            if sub_key not in expander_config[expander_type]:
                                expander_config[expander_type][sub_key] = default_value[expander_type][sub_key]
                                changed = True
                if changed:
                    _config.set(key, expander_config)

    @staticmethod
    def get_default_value(key):
        for key_, value in FamilyTreeViewConfigProvider.get_config_settings():
            if key_ == key:
                return value

    def get_configure_page_funcs(self):
        return [
            self.appearance_page,
            self.interaction_page,
            self.names_page,
            self.expanders_page,
            self.badges_page,
            self.experimental_page,
        ]

    def appearance_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        row += 1
        configdialog.add_spinner(
            grid,
            _("Default number of ancestor generations to show"),
            row,
            "appearance.familytreeview-num-ancestor-generations-default",
            (0, 20) # more might can performance issues, expanders can be used
        )

        row += 1
        configdialog.add_spinner(
            grid,
            _("Default number of descendant generations to show"),
            row,
            "appearance.familytreeview-num-descendant-generations-default",
            (0, 20) # more might can performance issues, expanders can be used
        )

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Highlight the root (active) person with a thick outline"),
            row,
            "appearance.familytreeview-highlight-root-person",
            stop=3 # same width as spinners and combos
        )

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Show black ribbon for deceased persons"),
            row,
            "appearance.familytreeview-show-deceased-ribbon",
            stop=3 # same width as spinners and combos
        )

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Gray out people who do not match the sidebar filter"),
            row,
            "appearance.familytreeview-filter-person-gray-out",
            stop=3 # same width as spinners and combos
        )

        row += 1
        configdialog.add_combo(
            grid,
            _("Person image filter"),
            row,
            "appearance.familytreeview-person-image-filter",
            [
                (0, _("No filter")),
                (1, _("Apply grayscale to dead persons")),
                (2, _("Apply grayscale to all persons")),
            ]
        )

        row += 1
        configdialog.add_combo(
            grid,
            _("Default timeline mode in person panel"),
            row,
            "appearance.familytreeview-timeline-mode-default-person",
            [
                (0, _("Primary own events")),
                (1, _("All own events")),
                (2, _("Primary own and relatives' events")),
                (3, _("All own and relatives' events")),
            ]
        )

        row += 1
        configdialog.add_combo(
            grid,
            _("Default timeline mode in family panel"),
            row,
            "appearance.familytreeview-timeline-mode-default-family",
            [
                (0, _("Family events")),
                (1, _("Family and parents' event")),
                (2, _("Family and children's events")),
                (3, _("Family, parents' and children's events")),
            ]
        )

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Use short age representation (much shorter for uncertain dates)"),
            row,
            "appearance.familytreeview-timeline-short-age",
            stop=3 # same width as spinners and combos
        )

        row += 1
        label = configdialog.add_text(
            grid,
            _("Select which event types should be visible in the timeline and for which to show the description for:"),
            row, stop=3
        )
        label.set_xalign(0)
        label.set_margin_top(20)

        row += 1
        config_event_types_visible = self.ftv._config.get("appearance.familytreeview-timeline-event-types-visible")
        config_event_types_show_description = self.ftv._config.get("appearance.familytreeview-timeline-event-types-show-description")

        event_type_tree_store = Gtk.TreeStore(str, str, bool, bool, bool, bool, str)
        for group, events in EventType._MENU:
            all_visible = all(config_event_types_visible.get(EventType._I2EMAP[event_i], True) for event_i in events)
            none_visible = all(not config_event_types_visible.get(EventType._I2EMAP[event_i], True) for event_i in events)
            all_show_description = all(config_event_types_show_description.get(EventType._I2EMAP[event_i], False) for event_i in events)
            none_show_description = all(not config_event_types_show_description.get(EventType._I2EMAP[event_i], False) for event_i in events)
            treeiter = event_type_tree_store.append(None, [
                group,
                _(group),
                all_visible,
                not all_visible and not none_visible, # inconsistent
                all_show_description,
                not all_show_description and not none_show_description, # inconsistent
                "" # empty column
            ])
            for event_i in events:
                event_str = EventType._I2SMAP[event_i]
                event_name = EventType._I2EMAP[event_i]
                event_type_visible = config_event_types_visible.get(event_name, True) # default: visible
                event_type_show_description = config_event_types_show_description.get(event_name, False) # default: no description
                event_type_tree_store.append(treeiter, [
                    event_name,
                    event_str,
                    event_type_visible,
                    False, # not inconsistent
                    event_type_show_description,
                    False, # not inconsistent
                    "" # empty column
                ])

        event_type_list_view = Gtk.TreeView(model=event_type_tree_store)
        event_type_list_view.get_selection().set_mode(Gtk.SelectionMode.NONE)

        # name column
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=1)
        event_type_list_view.append_column(column)

        def _cb_event_type_toggled(widget, path, i, config_name, default):
            config_val = self.ftv._config.get(config_name)
            if ":" in path:
                # event type (not event type group)
                event_type_tree_store[path][i] = not event_type_tree_store[path][i]
                event_name = event_type_tree_store[path][0]
                if event_name not in config_val:
                    config_val[event_name] = default
                config_val[event_name] = event_type_tree_store[path][i]
                self.ftv._config.set(config_name, config_val)

                # update checkboxes of parent / group
                parent_path = path.rsplit(":", 1)[0]
                group = event_type_tree_store[parent_path][0]
                group_events = [events for gr, events in EventType._MENU if gr == group][0]
                all_ = all(config_val.get(EventType._I2EMAP[event_i], default) for event_i in group_events)
                none_ = all(not config_val.get(EventType._I2EMAP[event_i], default) for event_i in group_events)
                event_type_tree_store[parent_path][i] = all_
                event_type_tree_store[parent_path][i+1] = not all_ and not none_ # inconsistent
            else:
                # event type group clicked
                # if in intermediate, select all checkboxes
                if event_type_tree_store[path][i+1]:
                    event_type_tree_store[path][i] = True
                    event_type_tree_store[path][i+1] = False
                else:
                    event_type_tree_store[path][i] = not event_type_tree_store[path][i]
                
                # update all
                for child_row in event_type_tree_store[path].iterchildren():
                    # child_row is event_type_tree_store[child_path]
                    # Apply checked/unchecked to child ui element and child's config.
                    child_row[i] = event_type_tree_store[path][i]
                    event_name = child_row[0]
                    if event_name not in config_val:
                        config_val[event_name] = default
                    config_val[event_name] = event_type_tree_store[path][i]
                self.ftv._config.set(config_name, config_val)

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            self.ftv.cb_update_config(None, None, None, None)

        # visible column
        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", _cb_event_type_toggled, 2, "appearance.familytreeview-timeline-event-types-visible", True)
        column = Gtk.TreeViewColumn("Visible", renderer, active=2, inconsistent=3)
        event_type_list_view.append_column(column)

        # show description column
        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", _cb_event_type_toggled, 4, "appearance.familytreeview-timeline-event-types-show-description", False)
        column = Gtk.TreeViewColumn("Show description", renderer, active=4, inconsistent=5)
        event_type_list_view.append_column(column)

        # empty column to fill the remaining space
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=6)
        event_type_list_view.append_column(column)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(event_type_list_view)
        grid.attach(scrolled_window, 1, row, 2, 1)

        row += 1
        label = configdialog.add_text(
            grid,
            _(
                "In order for an event to appear on the timeline, it must have a valid date, "
                "the selected timeline mode must allow it to be displayed, "
                "and it's type must be checked in the Visible column above."
            ),
            row, stop=3
        )
        label.set_xalign(0)

        return (_("Appearance"), grid)

    def interaction_page(self, configdialog):
        personOptions = [
            (0, _("Do nothing")),
            (1, _("Open info box")),
            (2, _("Open side panel")),
            (3, _("Edit person")),
            (4, _("Set as active person")),
            (5, _("Set as home person")),
        ]
        familyOptions = [
            (0, _("Do nothing")),
            (1, _("Open info box")),
            (2, _("Open side panel")),
            (3, _("Edit family")),
        ]

        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        row += 1
        checkbox = configdialog.add_checkbox(
            grid,
            _(
                "Prepend FamilyTreeView to the plugin list instead of appending it. (Requires restart.)\n"
                "If no other chart view is prepended, this makes FamilyTreeView the first and default chart view.\n"
                "Since FamilyTreeView is still in beta stage, be cautious with this option."
            ),
            row,
            "interface.familytreeview-order-start",
            stop=3, # same width as spinners and combos
            config=config, # This is stored in Gramps' config to be available when registering the plugin.
        )
        label = checkbox.get_child()
        label.set_line_wrap(True)

        row += 1
        configdialog.add_combo(
            grid,
            _("Person single click action"),
            row,
            "interaction.familytreeview-person-single-click-action",
            personOptions
        )

        row += 1
        configdialog.add_combo(
            grid,
            _("Person double click action"),
            row,
            "interaction.familytreeview-person-double-click-action",
            personOptions
        )

        row += 1
        configdialog.add_combo(
            grid,
            _("Family single click action"),
            row,
            "interaction.familytreeview-family-single-click-action",
            familyOptions
        )

        row += 1
        configdialog.add_combo(
            grid,
            _("Family double click action"),
            row,
            "interaction.familytreeview-family-double-click-action",
            familyOptions
        )

        row += 1
        configdialog.add_spinner(
            grid,
            _("Timeout to wait for second click of double click in milliseconds"),
            row,
            "interaction.familytreeview-double-click-timeout-milliseconds",
            (1, 5000) # large value: accessibility
        )

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Show \"Set active\" button in family info box (it has no effect on FamilyTreeView)"),
            row,
            "interaction.familytreeview-family-info-box-set-active-button",
            stop=3 # same width as spinners and combos
        )

        row += 1
        configdialog.add_checkbox(
            grid,
            _(
                "Printing: Scale down tree to fit on Letter and A4 paper. "
                "Uncheck to print at 1:1 scale.\n"
                "Note that scaling down can cause distorted text on some systems."
            ),
            row,
            "interaction.familytreeview-printing-scale-to-page",
            stop=3 # same width as spinners and combos
        )

        return (_("Interaction"), grid)

    def names_page(self, configdialog):
        return names_page(self.ftv, configdialog)

    def expanders_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        row += 1
        label = configdialog.add_text(
            grid,
            _(
                "The expansion of 'Other parents' is a mutually exclusive "
                "alternative to 'Siblings' and to 'Other families'. "
                "You cannot set 'Other parents' to expand together with one "
                "(or both) of the others by default, because there would be "
                "overlapping connections."
            ),
            row, stop=2
        )
        label.set_xalign(0)

        row += 1
        expander_list_store = Gtk.ListStore(str, str, bool, bool, bool, bool, bool, bool, str)
        expander_types_shown = self.ftv._config.get("expanders.familytreeview-expander-types-shown")
        expander_types_expanded = self.ftv._config.get("expanders.familytreeview-expander-types-expanded")
        expander_types = [
            ("parents", _("Parents")),
            ("other_parents", _("Other parents")),
            ("siblings", _("Siblings")),
            ("other_families", _("Other families")),
            ("spouses_other_families", _("Other families of spouses")),
            ("children", _("Children")),
        ]
        for expander_type_name, expander_type_translated in expander_types:
            expander_type_shown = expander_types_shown.get(expander_type_name, {
                "default_shown": True,
                "default_hidden": True
            })
            expander_type_expanded = expander_types_expanded.get(expander_type_name, False)
            # These are the only subtree types where other criteria (such as the generation they are in)
            # determine whether they are shown by default.
            separate_default_handling = expander_type_name in ["parents", "children"]
            expander_list_store.append([
                expander_type_name,
                expander_type_translated,
                expander_type_shown["default_shown"] if separate_default_handling else False,
                separate_default_handling, # activatable
                expander_type_shown["default_hidden"],
                True, # activatable
                False if separate_default_handling else expander_type_expanded,
                not separate_default_handling, # activatable
                "" # empty column
            ])

        expander_tree_view = Gtk.TreeView(model=expander_list_store)
        expander_tree_view.get_selection().set_mode(Gtk.SelectionMode.NONE)

        # expander type column
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Expander type"), renderer, text=1)
        expander_tree_view.append_column(column)

        def _cb_expander_toggled(widget, path, i, config_key, sub_key=None):
            expander_list_store[path][i] = not expander_list_store[path][i]
            config = self.ftv._config.get(config_key)
            expander_type = expander_list_store[path][0]
            if sub_key is None:
                config[expander_type] = expander_list_store[path][i]
            else:
                if expander_type not in config:
                    assert config_key == "expanders.familytreeview-expander-types-shown"
                    default_value = {"default_shown": True, "default_hidden": True}
                    config[expander_type] = default_value
                config[expander_type][sub_key] = expander_list_store[path][i]
            if expander_list_store[path][i]:
                # Some expanders cannot expand together, checkboxes are mutually exclusive alternatives.
                if config_key == "expanders.familytreeview-expander-types-expanded":
                    if expander_type == "other_parents":
                        expander_types_to_uncheck = [
                            "siblings",
                            "other_families"
                        ]
                    elif expander_type == "other_families":
                        expander_types_to_uncheck = ["other_parents"]
                    elif expander_type == "siblings":
                        expander_types_to_uncheck = ["other_parents"]
                    else:
                        expander_types_to_uncheck = []
                    for expander_type_ in expander_types_to_uncheck:
                        path_ = str([t[0] for t in expander_types].index(expander_type_))
                        expander_list_store[path_][i] = False
                        config[expander_type_] = expander_list_store[path_][i]
            self.ftv._config.set(config_key, config)

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            self.ftv.cb_update_config(None, None, None, None)

        # checkbox column
        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", _cb_expander_toggled, 2, "expanders.familytreeview-expander-types-shown", "default_shown")
        column = Gtk.TreeViewColumn(_("Show expanders\nfor subtrees\nvisible by default"), renderer, active=2, activatable=3)
        expander_tree_view.append_column(column)
        renderer = Gtk.CellRendererToggle()

        renderer.connect("toggled", _cb_expander_toggled, 4, "expanders.familytreeview-expander-types-shown", "default_hidden")
        column = Gtk.TreeViewColumn(_("Show expanders\nfor subtrees\nhidden by default"), renderer, active=4, activatable=5)
        expander_tree_view.append_column(column)
        renderer = Gtk.CellRendererToggle()

        renderer.connect("toggled", _cb_expander_toggled, 6, "expanders.familytreeview-expander-types-expanded")
        column = Gtk.TreeViewColumn(_("Expand subtrees\nby default"), renderer, active=6, activatable=7)
        expander_tree_view.append_column(column)

        # empty column to fill the remaining space
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=8)
        expander_tree_view.append_column(column)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(expander_tree_view)
        grid.attach(scrolled_window, 1, row, 8, 1) # these are the default with of widgets created by configdialog's methods

        return (_("Expanders"), grid)

    def badges_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        row += 1
        label = configdialog.add_text(
            grid,
            _("Choose which badges to display where:"),
            row, stop=3
        )
        label.set_xalign(0)

        row += 1
        badge_list_store = Gtk.ListStore(str, bool, bool, bool, bool, str)
        config_badges_active = self.ftv._config.get("badges.familytreeview-badges-active")
        for badge_id, badge_name, person_callback, family_callback, default_active_person, default_active_family in self.badge_manager.badges:
            badge_active = config_badges_active.get(badge_id, {
                # by default, turn all badges on, if they are provided
                "person": default_active_person and person_callback is not None,
                "family": default_active_family and family_callback is not None
            })
            badge_list_store.append([
                badge_name,
                badge_active["person"], # person active
                person_callback is not None, # person available
                badge_active["family"], # family active
                family_callback is not None, # family available
                "" # empty column
            ])

        badge_tree_view = Gtk.TreeView(model=badge_list_store)
        badge_tree_view.get_selection().set_mode(Gtk.SelectionMode.NONE)

        # name column
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Name"), renderer, text=0)
        badge_tree_view.append_column(column)

        def _cb_badge_toggled(widget, path, i):
            badge_list_store[path][2*i+1] = not badge_list_store[path][2*i+1] # +1 to skip name column, factor 2 because of available columns
            config_badges_active = self.ftv._config.get("badges.familytreeview-badges-active")
            badge_id = self.badge_manager.badges[int(path)][0]
            if badge_id not in config_badges_active:
                config_badges_active[badge_id] = {
                    # by default, turn all badges on, if they are provided
                    "person": person_callback is not None,
                    "family": family_callback is not None
                }
            config_badges_active[badge_id][["person", "family"][i]] = badge_list_store[path][2*i+1]
            self.ftv._config.set("badges.familytreeview-badges-active", config_badges_active)

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            self.ftv.cb_update_config(None, None, None, None)

        # checkbox column
        for i, column_title in enumerate([_("Person box"), _("Family box")]):
            renderer = Gtk.CellRendererToggle()
            renderer.connect("toggled", _cb_badge_toggled, i)
            column = Gtk.TreeViewColumn(column_title, renderer, active=2*i+1, activatable=2*i+2)
            badge_tree_view.append_column(column)

        # empty column to fill the remaining space
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=5)
        badge_tree_view.append_column(column)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(badge_tree_view)
        grid.attach(scrolled_window, 1, row, 8, 1) # these are the default with of widgets created by configdialog's methods

        return (_("Badges"), grid)

    def experimental_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        row += 1
        label = configdialog.add_text(
            grid,
            _(
                "These are experimental features. "
                "Only activate them after double checking your backup!"
            ),
            row, stop=3, bold=True
        )
        label.set_margin_top(10)
        label.set_margin_bottom(10)

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Use adaptive distances between ancestor generations"),
            row,
            "experimental.familytreeview-adaptive-ancestor-generation-dist",
            stop=3 # same width as spinners and combos
        )

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Double click one end of a connection to move to the person or family at the other end"),
            row,
            "experimental.familytreeview-connection-follow-on-click",
            stop=3 # same width as spinners and combos
        )

        row += 1
        configdialog.add_spinner(
            grid,
            _(
                "PPI (pixels per inch) to calculate font size in pixels for name display on canvas"
                "(increase if there is only one line, decrease if there are more that two lines, default: 96)"
            ),
            row,
            "experimental.familytreeview-canvas-font-size-ppi",
            (20, 1000)
        )
        label = grid.get_child_at(1, row)
        label.set_line_wrap(True)
        label.set_xalign(0)

        return (_("Experimental"), grid)
