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

from gi.repository import Gdk, Gtk

from gramps.gen.config import config
from gramps.gen.const import SIZE_LARGE, SIZE_NORMAL, USER_HOME
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.lib.eventtype import EventType
from gramps.gen.proxy.living import LivingProxyDb
from gramps.gui.utils import rgb_to_hex

from family_tree_view_config_page_manager_boxes import BOX_ITEMS, PREDEF_BOXES_DEFS, FamilyTreeViewConfigPageManagerBoxes
from family_tree_view_config_provider_names import DEFAULT_ABBREV_RULES, FamilyTreeViewConfigProviderNames
from family_tree_view_utils import get_gettext, get_reloaded_custom_filter_list
if TYPE_CHECKING:
    from family_tree_view import FamilyTreeView


_ = get_gettext()

class FamilyTreeViewConfigProvider:
    def __init__(self, ftv: "FamilyTreeView"):
        self.ftv = ftv
        self.badge_manager = ftv.badge_manager

        self.boxes_page_manager = FamilyTreeViewConfigPageManagerBoxes(self)
        self.names_page_manager = FamilyTreeViewConfigProviderNames(self)

    @staticmethod
    def get_config_settings():
        default_event_types_show_description = [
            # religious
            EventType.RELIGION,
            # vocational
            EventType.OCCUPATION,
            EventType.RETIREMENT,
            EventType.ELECTED,
            EventType.MILITARY_SERV,
            EventType.ORDINATION,
            # academic
            EventType.EDUCATION,
            EventType.DEGREE,
            EventType.GRADUATION,
            # other
            EventType.CAUSE_DEATH,
            EventType.MED_INFO,
            EventType.NOB_TITLE,
            EventType.NUM_MARRIAGES,
        ]
        return (
            ("appearance.familytreeview-num-ancestor-generations-default", 2),
            ("appearance.familytreeview-num-descendant-generations-default", 2),
            ("appearance.familytreeview-highlight-home-person", True),
            ("appearance.familytreeview-highlight-root-person", True),
            ("appearance.familytreeview-show-deceased-ribbon", True),
            ("appearance.familytreeview-filter-person-gray-out", True),
            ("appearance.familytreeview-person-image-resolution", 1),
            ("appearance.familytreeview-person-image-filter", 0),
            ("appearance.familytreeview-place-format", -1),
            ("appearance.familytreeview-box-line-width", 2.0),
            ("appearance.familytreeview-connections-line-width", 2.0),
            ("appearance.familytreeview-connections-dashed-mode", "rel_any_non_birth"),

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

            ("interaction.familytreeview-zoom-level-default", 0),
            ("interaction.familytreeview-zoom-level-step", 0.15),
            ("interaction.familytreeview-family-info-box-set-active-button", False),
            ("interaction.familytreeview-person-add-relative-action", "overlay"),
            ("interaction.familytreeview-family-add-relative-action", "overlay"),

            ("interaction.familytreeview-person-single-primary-click-action", "open_info_box_person"),
            ("interaction.familytreeview-person-double-primary-click-action", "edit_person"),
            ("interaction.familytreeview-person-single-secondary-click-action", "open_context_menu_person"),
            ("interaction.familytreeview-person-double-secondary-click-action", "nothing"),
            ("interaction.familytreeview-person-single-middle-click-action", "nothing"),
            ("interaction.familytreeview-person-double-middle-click-action", "nothing"),
            ("interaction.familytreeview-family-single-primary-click-action", "open_info_box_family"),
            ("interaction.familytreeview-family-double-primary-click-action", "edit_family"),
            ("interaction.familytreeview-family-single-secondary-click-action", "open_context_menu_family"),
            ("interaction.familytreeview-family-double-secondary-click-action", "nothing"),
            ("interaction.familytreeview-family-single-middle-click-action", "nothing"),
            ("interaction.familytreeview-family-double-middle-click-action", "nothing"),
            ("interaction.familytreeview-background-single-primary-click-action", "nothing"),
            ("interaction.familytreeview-background-double-primary-click-action", "nothing"),
            ("interaction.familytreeview-background-single-secondary-click-action", "open_context_menu_background"),
            ("interaction.familytreeview-background-double-secondary-click-action", "nothing"),
            ("interaction.familytreeview-background-single-middle-click-action", "nothing"),
            ("interaction.familytreeview-background-double-middle-click-action", "nothing"),
            ("interaction.familytreeview-double-click-timeout-milliseconds", 200),
            ("interaction.familytreeview-scroll-mode", "map"),

            ("presentation.familytreeview-presentation-active", False),
            ("presentation.familytreeview-presentation-hide-private", False),
            ("presentation.familytreeview-presentation-living-proxy-mode", LivingProxyDb.MODE_INCLUDE_ALL),
            ("presentation.familytreeview-presentation-living-proxy-years-after-death", 0),
            ("presentation.familytreeview-presentation-filter-person", ""), # empty, no filter

            ("boxes.familytreeview-boxes-custom-defs", {}),
            ("boxes.familytreeview-boxes-selected-def-key", "regular"),

            ("names.familytreeview-abbrev-name-format-id", 0),
            ("names.familytreeview-abbrev-name-format-always", True),
            ("names.familytreeview-abbrev-name-all-caps-style", "all_caps"),
            ("names.familytreeview-abbrev-name-call-name-style", "none"),
            ("names.familytreeview-abbrev-name-call-name-mode", "call"),
            ("names.familytreeview-abbrev-name-primary-surname-style", "none"),
            ("names.familytreeview-abbrev-name-primary-surname-mode", "primary_surname"),
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

            ("badges.familytreeview-badges-active", { # example badges are turned off by default
                "num_citations": {"person": False, "family": False},
                "num_events_without_citations": {"person": False, "family": False},
                "num_children": {"person": False, "family": False},
                "num_other_families": {"person": False, "family": False},
                "filter_result": {"person": False, "family": False},
                "gramps_id": {"person": False, "family": False},
                "gramps_handle": {"person": False, "family": False},
            }),
            ("badges.familytreeview-badges-filter-match", {
                "person": {"generic": {}, "custom": {}},
                "family": {"custom": {}}
            }),

            ("interaction.familytreeview-printing-scale-to-page", False),
            ("interaction.familytreeview-printing-export-hide-expanders", True),

            ("experimental.familytreeview-adaptive-ancestor-generation-dist", True),
            ("experimental.familytreeview-connection-follow-on-click", False),
            ("experimental.familytreeview-filter-person-prune", False),
            ("experimental.familytreeview-tree-builder-use-progress", True),

            # without config ui
            ("paths.familytreeview-recent-export-dir", USER_HOME),
        )

    @staticmethod
    def config_connect(_config, cb_update_config):
        for config_name, *_ in FamilyTreeViewConfigProvider.get_config_settings():
            if config_name.split(".")[0] == "presentation":
                # Don't connect those signal. Db will be changed which
                # will trigger a rebuild.
                continue
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

        key = "boxes.familytreeview-boxes-custom-defs"
        content_def_config = _config.get(key)
        default_value = FamilyTreeViewConfigProvider.get_default_value(key)
        if not isinstance(content_def_config, dict):
            _config.set(key, default_value)
        else:
            changed = False
            for k, v in list(content_def_config.items()):
                if not isinstance(k, str):
                    content_def_config[str(k)] = content_def_config.pop(k)
                    k = str(k)
                    changed = True

                if len(v) != 4:
                    del content_def_config[k]
                    changed = True
                    continue

                v = list(v)
                v_changed = False
                if not isinstance(v[0], str):
                    v[0] = str(v[0])
                    v_changed = True
                if not isinstance(v[1], int):
                    try:
                        v[1] = int(v[1])
                    except ValueError:
                        v[1] = deepcopy(PREDEF_BOXES_DEFS["regular"][1])
                    v_changed = True
                for i, box_type in [(2, "person"), (3, "family")]:
                    if not isinstance(v[i], list):
                        v[i] = deepcopy(PREDEF_BOXES_DEFS["regular"][i])
                        v_changed = True
                        continue

                    # Delete all unknown items and fix or delete
                    # corrupted items.
                    js_to_delete = []
                    for j in range(len(v[i])): # loop over items
                        # corrupted or unknown item type
                        if (
                            not isinstance(v[i][j][0], str)
                            or v[i][j][0] not in [item[0] for item in BOX_ITEMS[box_type]]
                        ):
                            js_to_delete.append(j)
                            continue

                        idx = [item[0] for item in BOX_ITEMS[box_type]].index(v[i][j][0])
                        dflt_params = deepcopy(BOX_ITEMS[box_type][idx][3])

                        # no dict with params
                        if not isinstance(v[i][j][1], dict):
                            # direct assignment to tuple: convert to
                            # list
                            v[i][j] = list(v[i][j])
                            v[i][j][1] = dflt_params
                            v[i][j] = tuple(v[i][j])
                            v_changed = True
                            continue

                        # unknown, corrupted params
                        for k_, v_ in list(v[i][j][1].items()):
                            if k_ not in dflt_params.keys():
                                del v[i][j][1][k_]
                                v_changed = True
                            elif type(v_) != type(dflt_params[k_]):
                                v[i][j][1][k_] = dflt_params[k_]
                                v_changed = True

                        # missing params
                        for k_ in dflt_params.keys():
                            if k_ not in v[i][j][1].keys():
                                v[i][j][1][k_] = dflt_params[k_]
                                v_changed = True

                        # ensure item param order, important for order
                        # in UI
                        if list(v[i][j][1].keys()) != list(dflt_params.keys()):
                            # direct assignment to tuple: convert to
                            # list
                            v[i][j] = list(v[i][j])
                            v[i][j][1] = {
                                k: v[i][j][1][k]
                                for k in dflt_params.keys()
                            }
                            v[i][j] = tuple(v[i][j])
                            v_changed = True

                    for j in reversed(js_to_delete):
                        v[i].pop(j)
                        v_changed = True

                if v_changed:
                    content_def_config[k] = tuple(v)
                    changed = True
            if changed:
                _config.set(key, content_def_config)

        for key in [
            "expanders.familytreeview-expander-types-shown",
            "expanders.familytreeview-expander-types-expanded",
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

    @staticmethod
    def get_default_value(key):
        for key_, value in FamilyTreeViewConfigProvider.get_config_settings():
            if key_ == key:
                return value

    def get_configure_page_funcs(self):
        return [self.ftv_page]

    def ftv_page(self, configdialog):
        box = Gtk.Box()

        tree_store = Gtk.TreeStore(str, str, str)
        tree_view = Gtk.TreeView(model=tree_store)
        tree_view.set_margin_top(12)
        tree_view.set_margin_left(12)
        tree_view.set_margin_right(6)
        tree_view.set_margin_bottom(12)
        column = Gtk.TreeViewColumn("Page",  Gtk.CellRendererText(), text=1)
        tree_view.append_column(column)
        column = Gtk.TreeViewColumn("", Gtk.CellRendererText(), text=2) # empty
        tree_view.append_column(column)
        tree_view.set_headers_visible(False)

        selection = tree_view.get_selection()
        selection.set_mode(Gtk.SelectionMode.BROWSE)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(tree_view)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_hexpand(False)
        box.pack_start(scrolled_window, False, False, 0)

        separator = Gtk.Separator()
        box.pack_start(separator, False, False, 6)

        stack = Gtk.Stack()
        box.pack_start(stack, True, True, 0)

        default_page_id = "appearance"
        id_to_iter_dict = {}
        for page_id, parent_id, page_label, page_fcn in [
            ("appearance", None, _("Appearance"), self.appearance_page),
            ("interaction", None, _("Interaction"), self.interaction_page),
            ("mouse", "interaction", _("Mouse"), self.mouse_page),
            ("presentation", None, _("Presentation Mode"), self.presentation_page),
            ("boxes", None, _("Boxes"), self.boxes_page),
            ("names", None, _("Names"), self.names_page),
            ("name_abbr", "names", _("Name Abbreviation"), self.name_abbr_page),
            ("expanders", None, _("Expanders"), self.expanders_page),
            ("badges", None, _("Badges"), self.badges_page),
            ("timeline", None, _("Panel: Timeline"), self.timeline_page),
            ("print_export", None, _("Print/Export"), self.print_export_page),
            ("experimental", None, _("Experimental"), self.experimental_page),
        ]:
            if parent_id is None:
                parent_iter = None
            else:
                parent_iter = id_to_iter_dict[parent_id]
            tree_iter = tree_store.append(parent_iter, (page_id, page_label, ""))
            id_to_iter_dict[page_id] = tree_iter
            page_widget = page_fcn(configdialog)
            stack.add_named(page_widget, page_id)

        def cb_selection_changed(selection, tree_view):
            model, selected_tree_iter = selection.get_selected()
            if selected_tree_iter is not None:
                selected_path = model.get_path(selected_tree_iter)
                tree_view.expand_row(selected_path, False)
                selected_id = model[selected_tree_iter][0]
                stack.set_visible_child_name(selected_id)
        selection.connect("changed", cb_selection_changed, tree_view)

        selection.select_iter(id_to_iter_dict[default_page_id])
        stack.set_visible_child_name(default_page_id)

        return (_("FamilyTreeView"), box)

    def appearance_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        # Since Gramps doesn't freeze while building the tree and the
        # progress dialog (which shows up by default) allows to cancel,
        # it's acceptable to allow huge trees.

        row += 1
        configdialog.add_spinner(
            grid,
            _("Default number of ancestor generations to show"),
            row,
            "appearance.familytreeview-num-ancestor-generations-default",
            (0, 100)
        )

        row += 1
        configdialog.add_spinner(
            grid,
            _("Default number of descendant generations to show"),
            row,
            "appearance.familytreeview-num-descendant-generations-default",
            (0, 100)
        )

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Highlight the home person according to the active Gramps color scheme"),
            row,
            "appearance.familytreeview-highlight-home-person",
            stop=3 # same width as spinners and combos
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
        image_resolution_options = [
            (SIZE_NORMAL, _("Normal")),
            (SIZE_LARGE, _("High")),
            (-1, _("Original")),
        ]
        def _cb_image_resolution_combo_changed(combo, constant):
            self.ftv._config.set(constant, image_resolution_options[combo.get_active()][0])
        active_i = [opt[0] for opt in image_resolution_options].index(
            self.ftv._config.get("appearance.familytreeview-person-image-resolution")
        )
        configdialog.add_combo(
            grid,
            _("Resolution of the images"),
            row,
            "appearance.familytreeview-person-image-resolution",
            image_resolution_options,
            callback=_cb_image_resolution_combo_changed,
            setactive=active_i,
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
        place_format_options = [(-1, _("Default"))]
        for i, place_format in enumerate(place_displayer.get_formats()):
            place_format_options.append((i, place_format.name))
        def _cb_place_format_combo_changed(combo, constant):
            self.ftv._config.set(constant, place_format_options[combo.get_active()][0])
        active = self.ftv._config.get("appearance.familytreeview-place-format")+1
        if active not in [i for i, format_name in place_format_options]:
            active = -1+1
        configdialog.add_combo(
            grid,
            _("Place format in the tree"),
            row,
            "appearance.familytreeview-place-format",
            place_format_options,
            setactive=active,
            callback=_cb_place_format_combo_changed,
        )

        row += 1
        box_line_width_spinner = configdialog.add_spinner(
            grid,
            _("Line width of boxes"),
            row,
            "appearance.familytreeview-box-line-width",
            (0.0, 10.0),
            callback=self.spin_button_float_changed,
        )
        box_line_width_spinner.set_digits(1)
        box_line_width_spinner.get_adjustment().set_step_increment(0.1)

        row += 1
        connection_line_width_spinner = configdialog.add_spinner(
            grid,
            _("Line width of connections"),
            row,
            "appearance.familytreeview-connections-line-width",
            (0.1, 10.0),
            callback=self.spin_button_float_changed,
        )
        connection_line_width_spinner.set_digits(1)
        connection_line_width_spinner.get_adjustment().set_step_increment(0.1)

        row += 1
        dashed_options = [
            ("no_dash", _("No dashed connections")),
            ("rel_any_non_birth", _("Dashed if at least one parent is non-birth")),
            ("rel_both_non_birth", _("Dashed only if both parents are non-birth")),
            ("rel_split_non_birth", _("Dashed on each side based on each parent")),
        ]
        add_rel_label = Gtk.Label(_("Dashed connection lines:"))
        add_rel_label.set_halign(Gtk.Align.START)
        add_rel_label.set_xalign(0)
        add_rel_label.set_line_wrap(True)
        grid.attach(add_rel_label, 1, row, 1, 1)
        add_rel_list_store = Gtk.ListStore(str, str)
        for option_id, option_label in dashed_options:
            add_rel_list_store.append((option_id, option_label))
        add_rel_combo = Gtk.ComboBox(model=add_rel_list_store)
        renderer = Gtk.CellRendererText()
        add_rel_combo.pack_start(renderer, True)
        add_rel_combo.add_attribute(renderer, "text", 1)
        active_option = self.ftv._config.get("appearance.familytreeview-connections-dashed-mode")
        try:
            active_index = [opt[0] for opt in dashed_options].index(active_option)
        except ValueError:
            active_index = 1 # any non birth
        add_rel_combo.set_active(
            active_index
        )
        def cb_add_relative_changed(combo, options):
            self.ftv._config.set(
                "appearance.familytreeview-connections-dashed-mode",
                options[combo.get_active()][0]
            )
        add_rel_combo.connect("changed", cb_add_relative_changed, dashed_options)
        grid.attach(add_rel_combo, 2, row, 1, 1)
        
        row += 1
        label = Gtk.Label()
        label.set_markup(_(
            "Dashed on each side based on each parent:\n"
            "<i>Each half of the connection is dashed if the parent on that "
            "side is non-birth (father: left half, mother: right half)</i>"
        ))
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0)
        label.set_line_wrap(True)
        grid.attach(label, 2, row, 1, 1)

        return grid

    def interaction_page(self, configdialog):
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
        zoom_level_default_spin_button = configdialog.add_spinner(
            grid,
            _("Default zoom level"),
            row,
            "interaction.familytreeview-zoom-level-default",
            (
                self.ftv.widget_manager.canvas_manager.zoom_level_min,
                self.ftv.widget_manager.canvas_manager.zoom_level_max
            ),
            callback=self.spin_button_float_changed,
        )
        zoom_level_default_spin_button.set_digits(2)
        zoom_level_default_spin_button.get_adjustment().set_step_increment(0.1)

        row += 1
        set_default_zoom_button = configdialog.add_button(
            grid,
            _("Set current zoom level as default zoom level"),
            row,
            "",
            extra_callback=lambda button:
                zoom_level_default_spin_button.set_value(round(
                    self.ftv.widget_manager.canvas_manager.get_zoom_level(),
                    2 # two digits, same as displayed
                ))
        )
        # move 1 grid column to the right (under spin button)
        grid.remove(set_default_zoom_button)
        grid.attach(set_default_zoom_button, 2, row, 1, 1)

        row += 1
        zoom_level_step_spin_button = configdialog.add_spinner(
            grid,
            _("Zoom level step size"),
            row,
            "interaction.familytreeview-zoom-level-step",
            (0.01, 2.0),
            callback=self.spin_button_float_changed,
        )
        zoom_level_step_spin_button.set_digits(2)
        zoom_level_step_spin_button.get_adjustment().set_step_increment(0.05)

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Show \"Set active\" button in family info box (it has no effect on FamilyTreeView)"),
            row,
            "interaction.familytreeview-family-info-box-set-active-button",
            stop=3 # same width as spinners and combos
        )

        person_label = _("Menu to open with the person \"Add relatives\" button:")
        family_label = _("Menu to open with the family \"Add relatives\" button:")
        person_options = [
            ("context_menu", _("Context menu")),
            ("overlay", _("Overlay menu")),
            ("overlay_direct", _("Overlay menu (only direct relationships)")),
            ("overlay_main", _("Overlay menu (only main relationships)")),
            ("overlay_all", _("Overlay menu (everything)")),
        ]
        family_options = [
            ("context_menu", _("Context menu")),
            ("overlay", _("Overlay menu")),
        ]
        def cb_add_relative_changed(combo, key, options):
            self.ftv._config.set(
                f"interaction.familytreeview-{key}-add-relative-action",
                options[combo.get_active()][0]
            )
        for key, label_text, options in [
            ("person", person_label, person_options),
            ("family", family_label, family_options)
        ]:
            row += 1
            add_rel_label = Gtk.Label(label_text)
            add_rel_label.set_halign(Gtk.Align.START)
            add_rel_label.set_xalign(0)
            add_rel_label.set_line_wrap(True)
            grid.attach(add_rel_label, 1, row, 1, 1)
            add_rel_list_store = Gtk.ListStore(str, str)
            for option_id, option_label in options:
                add_rel_list_store.append((option_id, option_label))
            add_rel_combo = Gtk.ComboBox(model=add_rel_list_store)
            renderer = Gtk.CellRendererText()
            add_rel_combo.pack_start(renderer, True)
            add_rel_combo.add_attribute(renderer, "text", 1)
            active_option = self.ftv._config.get(f"interaction.familytreeview-{key}-add-relative-action")
            try:
                active_index = [opt[0] for opt in options].index(active_option)
            except ValueError:
                active_index = 1 # overlay
            add_rel_combo.set_active(
                active_index
            )
            add_rel_combo.connect("changed", cb_add_relative_changed, key, options)
            grid.attach(add_rel_combo, 2, row, 1, 1)

        return grid

    def mouse_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        person_click_options = [
            ("nothing", _("Do nothing")),
            ("open_info_box_person", _("Open info box")),
            ("open_panel_person", _("Open panel")),
            ("edit_person", _("Edit person")),
            ("set_active_person", _("Set as active person")),
            ("set_home_person", _("Set as home person")),
            ("open_context_menu_person", _("Open context menu")),
        ]
        family_click_options = [
            ("nothing", _("Do nothing")),
            ("open_info_box_family", _("Open info box")),
            ("open_panel_family", _("Open panel")),
            ("edit_family", _("Edit family")),
            ("set_active_family", _("Set as active family")),
            ("open_context_menu_family", _("Open context menu")),
        ]
        background_click_options = [
            ("nothing", _("Do nothing")),
            ("open_context_menu_background", _("Open context menu")),
            ("zoom_in", _("Zoom in")),
            ("zoom_out", _("Zoom out")),
            ("zoom_reset", _("Reset zoom")),
            ("scroll_to_active_person", _("Move to active person")),
            ("scroll_to_home_person", _("Move to home person")),
            ("scroll_to_active_family", _("Move to active family")),
        ]

        row += 1
        click_grid = Gtk.Grid()
        click_grid.set_column_spacing(6)
        click_grid.set_row_spacing(6)
        click_row = -1

        def _cb_person_click_combo_changed(combo, constant):
            self.ftv._config.set(constant, person_click_options[combo.get_active()][0])
        def _cb_family_click_combo_changed(combo, constant):
            self.ftv._config.set(constant, family_click_options[combo.get_active()][0])
        def _cb_background_click_combo_changed(combo, constant):
            self.ftv._config.set(constant, background_click_options[combo.get_active()][0])

        advanced_click_option_widgets = []
        check_button = Gtk.CheckButton(label=_("Show advanced click options"))
        advanced = any(
            self.ftv._config.get(
                f"interaction.familytreeview-{pfb}-{sd}-{sm}-click-action"
            ) != self.get_default_value(
                f"interaction.familytreeview-{pfb}-{sd}-{sm}-click-action"
            )
            for pfb in ["person", "family", "background"]
            for sm in ["secondary", "middle"] # not primary
            for sd in ["single", "double"]
        )
        check_button.set_active(advanced)
        check_button.get_child().set_line_wrap(True)
        def advanced_click_toggled(check_button):
            advanced = check_button.get_active()
            for widget in advanced_click_option_widgets:
                widget.set_visible(advanced)
        check_button.connect("toggled", advanced_click_toggled)
        click_grid.attach(check_button, 0, 0, 1, 2)

        for col, text in [
            (1, _("Primary mouse button (usually: left mouse button)")),
            (3, _("Secondary mouse button (usually: right mouse button)")),
            (5, _("Middle mouse button")),
        ]:
            label = Gtk.Label(text)
            click_grid.attach(label, col, 0, 2, 1)
            if col > 2:
                advanced_click_option_widgets.append(label)
            for col2, text2 in [(0, "single click"), (1, "double click")]:
                label = Gtk.Label(text2)
                click_grid.attach(label, col+col2, 1, 1, 1)
                if col > 2:
                    advanced_click_option_widgets.append(label)
        for click_row, text, options, callback, config_type in [
            (2, _("Person click action"), person_click_options, _cb_person_click_combo_changed, "person"),
            (3, _("Family click action"), family_click_options, _cb_family_click_combo_changed, "family"),
            (4, _("Background click action"), background_click_options, _cb_background_click_combo_changed, "background"),
        ]:
            label = Gtk.Label(text)
            click_grid.attach(label, 0, click_row, 1, 1)
            for col, config_button in [
                (1, "single-primary"),
                (2, "double-primary"),
                (3, "single-secondary"),
                (4, "double-secondary"),
                (5, "single-middle"),
                (6, "double-middle"),
            ]:
                config_key = f"interaction.familytreeview-{config_type}-{config_button}-click-action"
                active_click_option = self.ftv._config.get(config_key)
                combo_list_store = Gtk.ListStore(str, str)
                for option, x in options:
                    combo_list_store.append((option, x))
                click_combo = Gtk.ComboBox(model=combo_list_store)
                renderer = Gtk.CellRendererText()
                click_combo.pack_start(renderer, True)
                click_combo.add_attribute(renderer, "text", 1)
                click_combo.set_active(
                    [opt[0] for opt in options].index(active_click_option)
                )
                click_combo.connect("changed", callback, config_key)
                click_grid.attach(click_combo, col, click_row, 1, 1)
                if col > 2:
                    advanced_click_option_widgets.append(click_combo)
        click_grid_scrolled_window = Gtk.ScrolledWindow()
        click_grid_scrolled_window.set_hexpand(True)
        click_grid_scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, # horizontal
            Gtk.PolicyType.NEVER # vertical
        )
        click_grid_scrolled_window.add(click_grid)
        grid.attach(click_grid_scrolled_window, 1, row, 2, 1)

        # Hide advanced options (default: check button is unchecked).
        # The function cannot be called here directly, since when the
        # config window is shown, all widgets would be made visible
        # again.
        configdialog.get_window().connect("show", lambda *args:
            advanced_click_toggled(check_button)
        )

        row += 1
        configdialog.add_spinner(
            grid,
            _("Timeout to wait for second click of double click in milliseconds"),
            row,
            "interaction.familytreeview-double-click-timeout-milliseconds",
            (1, 5000) # large value: accessibility
        )
        label = grid.get_child_at(1, row)
        label.set_xalign(0)
        label.set_line_wrap(True)

        row += 1
        label = Gtk.Label()
        label.set_markup(_(
            "Mouse wheel scroll mode\n"
            "<i>Map mode: scroll wheel zooms\n"
            "Document mode: scroll wheel scrolls vertically "
            "(Shift: horizontally, Ctrl: zoom)</i>"
        ))
        label.set_halign(Gtk.Align.START)
        label.set_xalign(0)
        label.set_line_wrap(True)
        grid.attach(label, 1, row, 1, 1)
        scroll_modes = [
            ("map", _("Map mode")),
            ("doc", _("Document mode"))
        ]
        scroll_mode_list_store = Gtk.ListStore(str, str)
        for mode in scroll_modes:
            scroll_mode_list_store.append(mode)
        scroll_mode_combo_box = Gtk.ComboBox(model=scroll_mode_list_store)
        # scroll_mode_combo_box.set_vexpand(False)
        scroll_mode_combo_box.set_valign(Gtk.Align.START)
        renderer = Gtk.CellRendererText()
        scroll_mode_combo_box.pack_start(renderer, True)
        scroll_mode_combo_box.add_attribute(renderer, "text", 1)
        active_scroll_mode = self.ftv._config.get("interaction.familytreeview-scroll-mode")
        active_option = [mode[0] for mode in scroll_modes].index(active_scroll_mode)
        scroll_mode_combo_box.set_active(active_option)
        def _cb_scroll_mode_changed(combo):
            self.ftv._config.set(
                "interaction.familytreeview-scroll-mode",
                scroll_modes[combo.get_active()][0]
            )
        scroll_mode_combo_box.connect("changed", _cb_scroll_mode_changed)
        grid.attach(scroll_mode_combo_box, 2, row, 1, 1)

        return grid

    def presentation_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

        row += 1
        label = Gtk.Label(_(
            "This presentation mode aims to disable database editing and hide "
            "information according to the configurations below."
        ))
        label.set_line_wrap(True)
        label.set_xalign(0)
        grid.attach(label, 1, row, 2, 1)

        row += 1
        label = Gtk.Label()
        label.set_markup("<b>" + _(
            "This presentation mode is a best-effort feature and may not "
            "prevent all forms of exposure of data intended to be hidden. It "
            "is provided 'as is' and without any warranty. Use of this "
            "feature is at your own risk. "
            "See the GNU General Public License for more details."
        ) + "</b>")
        label.set_line_wrap(True)
        label.set_xalign(0)
        grid.attach(label, 1, row, 2, 1)

        row += 1
        label = Gtk.Label()
        label.set_markup("<b>" + _(
            "The presentation mode currently affects most, if not all, of "
            "Gramps. This means that data that should be hidden according to "
            "the configurations below shouldn't be revealed by changing the "
            "view or opening a Gramplet. To modify the database or view all "
            "of its data in other parts of Gramps, return to this page and "
            "disable presentation mode."
        ) + "</b>")
        label.set_line_wrap(True)
        label.set_xalign(0)
        grid.attach(label, 1, row, 2, 1)

        row += 1
        grid.attach(Gtk.Box(), 1, row, 1, 1) # gap

        row += 1
        def cb_presentation_mode_toggled(checkbox):
            active = checkbox.get_active()
            private_checkbox.set_sensitive(active)
            living_proxy_mode_combo.set_sensitive(active)
            active_mode = living_proxy_mode_options[
                living_proxy_mode_combo.get_active()
            ][0]
            years_after_death_spin_button.set_sensitive(
                active and active_mode != LivingProxyDb.MODE_INCLUDE_ALL
            )
            person_filter_combo.set_sensitive(active)
            self.ftv.update_proxy_db()
        presentation_checkbox = configdialog.add_checkbox(
            grid,
            _("Activate presentation mode"),
            row,
            "presentation.familytreeview-presentation-active",
            start=1,
            stop=3,
            extra_callback=cb_presentation_mode_toggled,
        )

        row += 1
        label = Gtk.Label(_(
            "In presentation mode, the database cannot be modified."
        ))
        label.set_line_wrap(True)
        label.set_xalign(0)
        grid.attach(label, 1, row, 2, 1)

        row += 1
        label = Gtk.Label()
        label.set_margin_top(20)
        label.set_markup("<b>" + _(
            "Configure which data to hide:"
        ) + "</b>")
        label.set_line_wrap(True)
        label.set_xalign(0)
        grid.attach(label, 1, row, 2, 1)

        row += 1
        label = Gtk.Label(_(
            "The configurations below are only available in presentation "
            "mode. They can slow down building the tree, using the search etc."
        ))
        label.set_line_wrap(True)
        label.set_xalign(0)
        grid.attach(label, 1, row, 2, 1)

        row += 1
        grid.attach(Gtk.Box(), 1, row, 1, 1) # gap

        row += 1
        private_checkbox = configdialog.add_checkbox(
            grid,
            _("Hide data marked private"),
            row,
            "presentation.familytreeview-presentation-hide-private",
            start=1,
            stop=3,
            extra_callback=self.ftv.update_proxy_db,
        )
        private_checkbox.set_sensitive(presentation_checkbox.get_active())

        row += 1
        grid.attach(Gtk.Box(), 1, row, 1, 1) # gap

        row += 1
        label = Gtk.Label(_("Hiding living people:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 1, 1)
        living_proxy_mode_options = [
            (LivingProxyDb.MODE_INCLUDE_ALL, _("Don't hide living people")),
            (LivingProxyDb.MODE_INCLUDE_FULL_NAME_ONLY, _("Hide data on living people except the name (full name is visible)")),
            (LivingProxyDb.MODE_INCLUDE_LAST_NAME_ONLY, _("Hide data on living people except the surname (only surname is visible)")),
            (LivingProxyDb.MODE_REPLACE_COMPLETE_NAME, _("Hide data on living people (full name is replaced)")),
            (LivingProxyDb.MODE_EXCLUDE_ALL, _("Hide living people altogether")),
        ]
        living_proxy_mode_list_store = Gtk.ListStore(int, str)
        for opt in living_proxy_mode_options:
            living_proxy_mode_list_store.append(opt)
        living_proxy_mode_combo = Gtk.ComboBox.new_with_model(living_proxy_mode_list_store)
        renderer = Gtk.CellRendererText()
        living_proxy_mode_combo.pack_start(renderer, True)
        living_proxy_mode_combo.add_attribute(renderer, "markup", 1)
        try:
            active_index = [opt[0] for opt in living_proxy_mode_options].index(
                self.ftv._config.get("presentation.familytreeview-presentation-living-proxy-mode")
            )
        except ValueError:
            active_index = 0 # include all
        living_proxy_mode_combo.set_active(active_index)
        def cb_living_proxy_mode_combo_changed(combo):
            active_mode = living_proxy_mode_options[combo.get_active()][0]
            self.ftv._config.set(
                "presentation.familytreeview-presentation-living-proxy-mode",
                active_mode
            )
            years_after_death_spin_button.set_sensitive(
                active_mode != LivingProxyDb.MODE_INCLUDE_ALL
            )
            self.ftv.update_proxy_db()
        living_proxy_mode_combo.connect("changed", cb_living_proxy_mode_combo_changed)
        living_proxy_mode_combo.set_sensitive(presentation_checkbox.get_active())
        grid.attach(living_proxy_mode_combo, 2, row, 1, 1)

        row += 1
        def cb_living_proxy_year_after_death_value_changed(*args):
            configdialog.update_spinner(*args)
            self.ftv.update_proxy_db()
        years_after_death_spin_button = configdialog.add_spinner(
            grid,
            _("Years after death for which to consider people as living in the above option"),
            row,
            "presentation.familytreeview-presentation-living-proxy-years-after-death",
            (0, 100),
            callback=cb_living_proxy_year_after_death_value_changed,
        )
        label = grid.get_child_at(1, row)
        label.set_line_wrap(True)
        label.set_xalign(0)
        years_after_death_spin_button.set_valign(Gtk.Align.START) # don't expand with multi-line label
        active_mode = self.ftv._config.get("presentation.familytreeview-presentation-living-proxy-mode")
        years_after_death_spin_button.set_sensitive(
            presentation_checkbox.get_active() and active_mode != LivingProxyDb.MODE_INCLUDE_ALL
        )

        row += 1
        grid.attach(Gtk.Box(), 1, row, 1, 1) # gap

        row += 1
        label = Gtk.Label(_("Hide people not matching the filter:"))
        label.set_halign(Gtk.Align.START)
        grid.attach(label, 1, row, 1, 1)
        custom_filter_list = get_reloaded_custom_filter_list()
        person_filter_list = custom_filter_list.get_filters("Person")
        person_filter_list = [("", _("No filter"))] + [
            (person_filter.get_name(), person_filter.get_name())
            for person_filter in person_filter_list
        ]
        person_filter_list_store = Gtk.ListStore(str, str)
        for person_filter in person_filter_list:
            person_filter_list_store.append(person_filter)
        person_filter_combo = Gtk.ComboBox.new_with_model(person_filter_list_store)
        renderer = Gtk.CellRendererText()
        person_filter_combo.pack_start(renderer, True)
        person_filter_combo.add_attribute(renderer, "markup", 1)
        try:
            active_index = [opt[0] for opt in person_filter_list].index(
                self.ftv._config.get("presentation.familytreeview-presentation-filter-person")
            )
        except ValueError:
            active_index = 0 # no filter, empty string
        person_filter_combo.set_active(active_index)
        def cb_person_filter_combo_changed(combo):
            active_filter = person_filter_list[combo.get_active()][0]
            self.ftv._config.set(
                "presentation.familytreeview-presentation-filter-person",
                active_filter
            )
            self.ftv.update_proxy_db()
        person_filter_combo.connect("changed", cb_person_filter_combo_changed)
        person_filter_combo.set_sensitive(presentation_checkbox.get_active())
        grid.attach(person_filter_combo, 2, row, 1, 1)

        row += 1
        label = Gtk.Label(_(
            "Unlike pruning the tree with a filter, this feature restricts "
            "access to the data altogether and therefore affects the panel, "
            "Gramplets, other views and other parts of Gramps as well."
        ))
        label.set_line_wrap(True)
        label.set_xalign(0)
        grid.attach(label, 1, row, 2, 1)

        # TODO maybe something custom (e.g. only year for dates)

        return grid

    def boxes_page(self, configdialog):
        return self.boxes_page_manager.boxes_page(configdialog)

    def names_page(self, configdialog):
        return self.names_page_manager.names_page(configdialog)

    def name_abbr_page(self, configdialog):
        return self.names_page_manager.name_abbr_page(configdialog)

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

        return grid

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
            row, stop=8, bold=True
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

        badges_tree_view = Gtk.TreeView(model=badge_list_store)
        badges_tree_view.get_selection().set_mode(Gtk.SelectionMode.NONE)

        # name column
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Name"), renderer, text=0)
        badges_tree_view.append_column(column)

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

            self.ftv.cb_update_config(None, None, None, None)

        # checkbox column
        for i, column_title in enumerate([_("Person box"), _("Family box")]):
            renderer = Gtk.CellRendererToggle()
            renderer.connect("toggled", _cb_badge_toggled, i)
            column = Gtk.TreeViewColumn(column_title, renderer, active=2*i+1, activatable=2*i+2)
            badges_tree_view.append_column(column)

        # empty column to fill the remaining space
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=5)
        badges_tree_view.append_column(column)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(badges_tree_view)
        grid.attach(scrolled_window, 1, row, 8, 1) # these are the default with of widgets created by configdialog's methods

        # filter match badges

        DEFAULT_FILTER_MATCH_BADGE_PARAMS = {
            "active": False, # Do not show badge for each new filter.
            "content_text": "◉",
            "text_color": "#000",
            "background_color": "#FFF",
        }
        filter_match_badges_config = self.ftv._config.get("badges.familytreeview-badges-filter-match")

        # NOTE: We use Grid for the filter match badges instead of
        # TreeView, since it seems to be very complicated to get color
        # picker and text entry to work inside of a TreeView.

        def fmt_grid(grid):
            grid.set_border_width(0)
            grid.set_column_spacing(13) # looks similar to TreeView
            grid.set_row_spacing(6) # looks similar to TreeView

        size_groups = [
            Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
            for _ in range(5)
        ]

        custom_filter_list = get_reloaded_custom_filter_list()

        for filter_space in ["Person", "Family"]:
            row += 1
            if filter_space == "Person":
                label_text = _("Badges based on person filters:")
            else:
                label_text = _("Badges based on family filters:")
            label = Gtk.Label()
            label.set_markup(f"<b>{label_text}</b>")
            label.set_xalign(0)
            label.set_margin_top(20)
            grid.attach(label, 1, row, 8, 1)

            if filter_space == "Person":
                filters = [None] # generic filter (sidebar)
            else:
                filters = []
            filters.extend(custom_filter_list.get_filters(filter_space))

            namespace_config = filter_match_badges_config[filter_space.lower()]
            for filt in filters:
                if filt is None:
                    # generic filter
                    if len(namespace_config["generic"]) == 0:
                        namespace_config["generic"] = deepcopy(DEFAULT_FILTER_MATCH_BADGE_PARAMS)
                    continue

                # Use name as filter key.
                # TODO Using a hash would be better, but I haven't found
                # a reliable way to hash a filter yet. 
                filt_name = filt.get_name()
                if filt_name not in namespace_config["custom"]:
                    namespace_config["custom"][filt_name] = deepcopy(DEFAULT_FILTER_MATCH_BADGE_PARAMS)

            row += 1
            filter_header_grid = Gtk.Grid()
            fmt_grid(filter_header_grid)
            for col, col_name in enumerate([
                _("Filter name"),
                _("Active"),
                _("Badge content"),
                _("Text color"),
                _("Background color"),
            ]):
                label = Gtk.Label()
                label.set_xalign(0)
                label.set_markup(f"<b>{col_name}</b>")
                size_groups[col].add_widget(label)
                filter_header_grid.attach(label, col, 0, 1, 1)
            grid.attach(filter_header_grid, 1, row, 8, 1)

            row += 1
            filter_grid = Gtk.Grid()
            fmt_grid(filter_grid)
            for i, filt in enumerate(filters):
                if filt is None:
                    filt_name = None
                    filt_label = _("Sidebar filter")
                    filter_badge_config = namespace_config["generic"]
                else:
                    filt_name = filt.get_name()
                    filt_label = filt_name
                    filter_badge_config = namespace_config["custom"][filt_name]
                col = -1

                col += 1
                label = Gtk.Label(filt_label)
                label.set_xalign(0)
                size_groups[col].add_widget(label)
                filter_grid.attach(label, col, i, 1, 1)

                col += 1
                box = Gtk.Box()
                check_button = Gtk.CheckButton()
                check_button.set_active(filter_badge_config["active"])
                def active_toggled(check_button, filter_badge_config):
                    filter_badge_config["active"] = check_button.get_active()
                    self.ftv._config.set("badges.familytreeview-badges-filter-match", filter_match_badges_config)
                    self.ftv.cb_update_config(None, None, None, None)
                check_button.connect("toggled", active_toggled, filter_badge_config)
                box.pack_start(check_button, True, False, 0)
                size_groups[col].add_widget(box)
                filter_grid.attach(box, col, i, 1, 1)

                # TODO maybe also support icons?
                col += 1
                entry = Gtk.Entry()
                entry.set_text(filter_badge_config["content_text"])
                def content_text_changed(entry, filter_badge_config):
                    filter_badge_config["content_text"] = entry.get_text()
                    self.ftv._config.set("badges.familytreeview-badges-filter-match", filter_match_badges_config)
                    self.ftv.cb_update_config(None, None, None, None)
                entry.connect("changed", content_text_changed, filter_badge_config)
                size_groups[col].add_widget(entry)
                filter_grid.attach(entry, col, i, 1, 1)

                def color_set(color_button, filter_badge_config, key):
                    rgba = color_button.get_rgba()
                    filter_badge_config[key] = rgb_to_hex((rgba.red, rgba.green, rgba.blue))
                    self.ftv._config.set("badges.familytreeview-badges-filter-match", filter_match_badges_config)
                    self.ftv.cb_update_config(None, None, None, None)

                col += 1
                box = Gtk.Box()
                color_button = Gtk.ColorButton()
                color_button.set_hexpand(False)
                rgba = Gdk.RGBA()
                rgba.parse(filter_badge_config["text_color"])
                color_button.set_rgba(rgba)
                color_button.set_title(_("{name}: text color").format(name=filt_name))
                color_button.connect("color-set", color_set, filter_badge_config, "text_color")
                box.pack_start(color_button, True, False, 0)
                size_groups[col].add_widget(box)
                filter_grid.attach(box, col, i, 1, 1)

                col += 1
                box = Gtk.Box()
                color_button = Gtk.ColorButton()
                color_button.set_hexpand(False)
                rgba = Gdk.RGBA()
                rgba.parse(filter_badge_config["background_color"])
                color_button.set_rgba(rgba)
                color_button.set_title(_("{name}: background color").format(name=filt_name))
                color_button.connect("color-set", color_set, filter_badge_config, "background_color")
                box.pack_start(color_button, True, False, 0)
                size_groups[col].add_widget(box)
                filter_grid.attach(box, col, i, 1, 1)

            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.set_hexpand(True)
            scrolled_window.set_vexpand(True)
            scrolled_window.add(filter_grid)
            grid.attach(scrolled_window, 1, row, 8, 1) # these are the default with of widgets created by configdialog's methods

        return grid

    def timeline_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

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
            _("Use short age representation in timeline (much shorter for uncertain dates)"),
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

        return grid

    def print_export_page(self, configdialog):
        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_column_spacing(6)
        grid.set_row_spacing(6)
        row = -1

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

        row += 1
        configdialog.add_checkbox(
            grid,
            _(
                "Hide expanders in prints and exports."
            ),
            row,
            "interaction.familytreeview-printing-export-hide-expanders",
            stop=3 # same width as spinners and combos
        )

        return grid

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
        configdialog.add_checkbox(
            grid,
            _("Prune people who do not match the sidebar filter"),
            row,
            "experimental.familytreeview-filter-person-prune",
            stop=3 # same width as spinners and combos
        )

        row += 1
        configdialog.add_checkbox(
            grid,
            _("Display progress dialog while building the tree"),
            row,
            "experimental.familytreeview-tree-builder-use-progress",
            stop=3 # same width as spinners and combos
        )

        return grid

    # boxes page wrappers

    def get_person_width(self):
        return self.boxes_page_manager._get_person_width()

    def get_person_content_item_defs(self):
        return self.boxes_page_manager._get_box_content_item_defs("person")

    def get_family_content_item_defs(self):
        return self.boxes_page_manager._get_box_content_item_defs("family")

    # utils

    def spin_button_float_changed(self, spin_button, key):
        self.ftv._config.set(key, spin_button.get_value())
