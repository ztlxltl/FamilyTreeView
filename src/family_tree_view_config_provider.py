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


from typing import TYPE_CHECKING

from gi.repository import Gtk

from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.lib.eventtype import EventType

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
            ("appearance.familytreeview-show-deceased-ribbon", True),
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

            ("badges.familytreeview-badges-active", { # examples are turned off by default
                'num_citations': {'person': False, 'family': False},
                'num_events_without_citations': {'person': False, 'family': False},
                'num_children': {'person': False, 'family': False},
                'num_other_families': {'person': False, 'family': False},
            }),

            ("experimental.familytreeview-adaptive-ancestor-generation-dist", False),
            ("experimental.familytreeview-connection-follow-on-click", False),
            ("experimental.familytreeview-canvas-font-size-ppi", 96),
        )

    @staticmethod
    def config_connect(_config, cb_update_config):
        for config_name, *_ in FamilyTreeViewConfigProvider.get_config_settings():
            _config.connect(config_name, cb_update_config)

    def get_configure_page_funcs(self):
        return [
            self.appearance_page,
            self.interaction_page,
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
            (0, 100) # more might be possible
        )

        row += 1
        configdialog.add_spinner(
            grid,
            _("Default number of descendant generations to show"),
            row,
            "appearance.familytreeview-num-descendant-generations-default",
            (0, 100) # more might be possible
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

        event_type_liststore = Gtk.TreeStore(str, str, bool, bool, bool, str)
        for group, events in EventType._MENU:
            treeiter = event_type_liststore.append(None, [
                group,
                _(group),
                False, # no checkboxes
                False, # placeholder
                False, # placeholder
                "" # empty column
            ])
            for event_i in events:
                event_str = EventType._I2SMAP[event_i]
                event_name = EventType._I2EMAP[event_i]
                event_type_visible = config_event_types_visible.get(event_name, True) # default: visible
                event_type_show_description = config_event_types_show_description.get(event_name, False) # default: no description
                event_type_liststore.append(treeiter, [
                    event_name,
                    event_str,
                    True, # visible checkboxes
                    event_type_visible,
                    event_type_show_description,
                    "" # empty column
                ])

        event_type_list_view = Gtk.TreeView(model=event_type_liststore)

        # name column
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=1)
        event_type_list_view.append_column(column)

        def _cb_event_type_toggled(widget, path, i, config_name, default):
            event_type_liststore[path][i] = not event_type_liststore[path][i]
            config_val = self.ftv._config.get(config_name)
            event_name = event_type_liststore[path][0]
            if event_name not in config_val:
                config_val[event_name] = default
            config_val[event_name] = event_type_liststore[path][i]
            self.ftv._config.set(config_name, config_val)

            # cb_update_config connected doesn't work, even when using a shallow or deep copy.
            # Update explicitly:
            self.ftv.cb_update_config(None, None, None, None)

        # visible column
        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", _cb_event_type_toggled, 3, "appearance.familytreeview-timeline-event-types-visible", True)
        column = Gtk.TreeViewColumn("Visible", renderer, active=3, visible=2)
        event_type_list_view.append_column(column)

        # show description column
        renderer = Gtk.CellRendererToggle()
        renderer.connect("toggled", _cb_event_type_toggled, 4, "appearance.familytreeview-timeline-event-types-show-description", False)
        column = Gtk.TreeViewColumn("Show description", renderer, active=4, visible=2)
        event_type_list_view.append_column(column)

        # empty column to fill the remaining space
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=5)
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
            (2, _("Open side padel")),
            (3, _("Edit person")),
            (4, _("Set as active person")),
            (5, _("Set as home person")),
        ]
        familyOptions = [
            (0, _("Do nothing")),
            (1, _("Open info box")),
            (2, _("Open side padel")),
            (3, _("Edit family")),
        ]

        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

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

        return (_("Interaction"), grid)

    def badges_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)

        badge_liststore = Gtk.ListStore(str, bool, bool, bool, bool, str)
        config_badges_active = self.ftv._config.get("badges.familytreeview-badges-active")
        for badge_id, badge_name, person_callback, family_callback in self.badge_manager.badges:
            badge_active = config_badges_active.get(badge_id, {
                # by default, turn all badges on, if they are provided
                "person": person_callback is not None,
                "family": family_callback is not None
            })
            badge_liststore.append([
                badge_name,
                badge_active["person"], # person active
                person_callback is not None, # person available
                badge_active["family"], # family active
                family_callback is not None, # family available
                "" # empty column
            ])

        badge_list_view = Gtk.TreeView(model=badge_liststore)

        # name column
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Name", renderer, text=0)
        badge_list_view.append_column(column)

        def _get_cb_badge_toggled(i):
            def _cb_badge_toggled(widget, path):
                badge_liststore[path][2*i+1] = not badge_liststore[path][2*i+1] # +1 to skip name column, factor 2 because of available columns
                config_badges_active = self.ftv._config.get("badges.familytreeview-badges-active")
                badge_id = self.badge_manager.badges[int(path)][0]
                if badge_id not in config_badges_active:
                    config_badges_active[badge_id] = {
                        # by default, turn all badges on, if they are provided
                        "person": person_callback is not None,
                        "family": family_callback is not None
                    }
                config_badges_active[badge_id][["person", "family"][i]] = badge_liststore[path][2*i+1]
                self.ftv._config.set("badges.familytreeview-badges-active", config_badges_active)

                # cb_update_config connected doesn't work, even when using a shallow or deep copy.
                # Update explicitly:
                self.ftv.cb_update_config(None, None, None, None)
            return _cb_badge_toggled

        # checkbox column
        for i, column_title in enumerate(["Person", "Family"]):
            renderer = Gtk.CellRendererToggle()
            renderer.connect("toggled", _get_cb_badge_toggled(i))
            column = Gtk.TreeViewColumn(column_title, renderer, active=2*i+1, activatable=2*i+2)
            badge_list_view.append_column(column)

        # empty column to fill the remaining space
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=5)
        badge_list_view.append_column(column)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(badge_list_view)
        grid.attach(scrolled_window, 1, 0, 8, 1) # these are the default with of widgets created by configdialog's methods

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
