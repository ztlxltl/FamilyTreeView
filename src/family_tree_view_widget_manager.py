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


import inspect
import os
import sys
from typing import TYPE_CHECKING

from gi.repository import Gdk, GLib, Gtk

from gramps.gen.config import config
from gramps.gen.const import USER_PLUGINS
from gramps.gen.datehandler import get_date
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.lib import Person
from gramps.gen.utils.alive import probably_alive
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback, get_marriage_or_fallback, get_divorce_or_fallback
from gramps.gen.utils.string import format_gender
from gramps.gui.utils import color_graph_box, color_graph_family, get_contrast_color, hex_to_rgb, hex_to_rgb_float, rgb_to_hex

from date_display_compact import get_date as get_date_compact
from family_tree_view_canvas_manager import FamilyTreeViewCanvasManager
from family_tree_view_info_box_manager import FamilyTreeViewInfoBoxManager
from family_tree_view_minimap_manager import FamilyTreeViewMinimapManager
from family_tree_view_panel_manager import FamilyTreeViewPanelManager
from family_tree_view_tree_builder import FamilyTreeViewTreeBuilder
from family_tree_view_utils import get_event_from_family, get_event_from_person, get_gettext, import_GooCanvas
if TYPE_CHECKING:
    from family_tree_view import FamilyTreeView


sys.path.append(os.path.join(USER_PLUGINS, 'GraphView'))
try:
    from search_widget import SearchWidget, Popover
except ModuleNotFoundError:
    search_widget_available = False
else:
    search_widget_available = True

GooCanvas = import_GooCanvas()

_ = get_gettext()

class FamilyTreeViewWidgetManager:
    def __init__(self, ftv: "FamilyTreeView"):

        self.ftv = ftv

        self.provider = Gtk.CssProvider()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(Gdk.Screen.get_default(), self.provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.provider_str = ""

        self.main_widget = Gtk.Box(spacing=4, orientation=Gtk.Orientation.VERTICAL)
        self.main_widget.set_border_width(4)

        self.num_persons_added = 0
        self.num_persons_matching_filter_added = 0
        self.num_missing_persons_added = 0
        self.num_families_added = 0
        self.person_handle_list = []

        self.toolbar = Gtk.Box(spacing=4, orientation=Gtk.Orientation.HORIZONTAL)
        if search_widget_available:
            self.search_widget = SearchWidget(
                self.ftv.dbstate,
                lambda *args, **kwargs: None, # no image for now
                bookmarks=self.ftv.bookmarks
            )

            # Use "view" instead of "graph" in result popover.
            self.search_widget.popover_widget = Popover(
                _('Persons from current view'),
                _('Other persons from database')
            )
            self.search_widget.popover_widget.set_relative_to(self.search_widget.search_entry)
            self.search_widget.popover_widget.connect('item-activated', self.search_widget.activate_item)
            self.search_widget.popover_widget.connect('closed', self.search_widget.stop_search)

            self.search_widget.set_options(show_images=False)
            def item_activated(_widget, person_handle):
                self.search_widget.hide_search_popover()
                self.ftv.goto_handle(person_handle)
            self.search_widget.connect('item-activated', item_activated)
            # Argument to set_items_list doesn't need to be a list of GooCanvas.CanvasGroup objects. Also works with handles.
            self.search_widget.set_items_list(self.person_handle_list)
            search_box = self.search_widget.get_widget()
            self.toolbar.add(search_box)
        else:
            self.search_widget = None

            info_bar = Gtk.InfoBar(
                parent=self.main_widget,
                message_type=Gtk.MessageType.INFO,
                show_close_button=True,
            )
            def close_info_bar(*args):
                info_bar.set_revealed(False)
            info_bar.connect("close", close_info_bar) # escape key
            info_bar.connect("response", close_info_bar) # close button

            content_area = info_bar.get_content_area()
            label = Gtk.Label(_(
                "Search is not available. "
                "Install the Graph View addon and restart Gramps to make the search available."
            ))
            label.set_line_wrap(True)
            label.set_xalign(0)
            content_area.add(label)

        self.main_widget.pack_start(self.toolbar, False, False, 0)

        # By preventing Gramps from freezing, the tree is redrawn often.
        # The stack is used to hide the tree while building it to avoid
        # flickering caused by the many tree updates. Use an image for
        # the old tree to prevent only briefly hiding the tree (small
        # tree build fast).
        # TODO This solution is not ideal: because of the static image,
        # the scrollbars don't disappear after a few seconds, and
        # resizing the window or the sidebar before the progress meter
        # pops up causes a wrong visualization (it looks different when
        # the canvas can adjust to the changed size).
        self.main_container_stack = Gtk.Stack()

        self.main_container_paned = Gtk.Paned()
        self.main_container_paned_size_allocate_first_call = True
        self.main_container_paned.connect("size-allocate", self.main_container_paned_size_allocate)

        self.canvas_manager = FamilyTreeViewCanvasManager(
            self,
            cb_background=self._cb_background_clicked,
            resize_reference=self.main_container_paned,
        )
        self.tree_builder = FamilyTreeViewTreeBuilder(self)

        self.minimap_overlay_container = Gtk.Overlay()
        self.minimap_overlay_container.add(self.canvas_manager.canvas_container)
        self.minimap_manager = FamilyTreeViewMinimapManager(self)
        self.minimap_overlay_container.add_overlay(self.minimap_manager.minimap_outer_container)

        # Overlay is required for info boxes.
        # This solution isn't perfect since the overlayed child is in front of the scroll bar of ScrolledWindow.
        # Overlay inside ScrollWindow doesn't work as GooCanvas doesn't seem to expand Overlay larger than ScrolledWindow.
        # Maybe I'm missing a property to fix this.
        self.info_box_overlay_container = Gtk.Overlay()
        self.info_box_overlay_container.add(self.minimap_overlay_container)
        self.main_container_paned.pack1(self.info_box_overlay_container)
        self.info_box_manager = FamilyTreeViewInfoBoxManager(self)

        self.panel_manager = FamilyTreeViewPanelManager(self)
        self.main_container_paned.pack2(self.panel_manager.panel_widget)
        self.main_container_stack.add_named(self.main_container_paned, "actual")

        # Without a ScrolledWindow parent, Image would request it's size
        # even when not visible in Stack. This would prevent the
        # Sidebar and the Bottombar from expanding after a tree rebuild.
        repl_image_scrolled = Gtk.ScrolledWindow()
        # No scroll bars. (Those from the screenshot might be visible.)
        repl_image_scrolled.set_policy(Gtk.PolicyType.EXTERNAL, Gtk.PolicyType.EXTERNAL)
        # Deactivate scrolling, do nothing, don't propagate.
        repl_image_scrolled.connect("scroll-event", lambda *args: True)
        self.replacement_image = Gtk.Image()
        repl_image_scrolled.add(self.replacement_image)
        self.main_container_stack.add_named(repl_image_scrolled, "image")

        self.main_widget.pack_start(self.main_container_stack, True, True, 0)
        self.external_panel = False

        self.panel_hidden = True

        self.click_event_sources = [] # to wait for double clicks

        self.position_of_handle = {} # keep record of what is placed where

    def use_internal_panel(self):
        stack = inspect.stack()
        frame = stack[2]
        if not (
            frame.function in ["remove_gramplet", "__delete_clicked"]
            and os.path.basename(frame.filename) == "grampletbar.py"
        ):
            # Gramps is closing. No need to move widgets around.
            return

        panel_widget = self.panel_manager.panel_widget
        panel_scrolled = self.panel_manager.panel_scrolled
        if panel_widget.get_parent() != self.main_container_paned:
            if panel_widget.get_parent() is not None:
                panel_widget.get_parent().remove(panel_widget)
            self.main_container_paned.pack2(panel_widget)
        if panel_scrolled.get_parent() != panel_widget:
            if panel_scrolled.get_parent() is not None:
                panel_scrolled.get_parent().remove(panel_scrolled)
            panel_widget.add(panel_scrolled)
        self.external_panel = False

    def use_external_panel(self, new_container, show_panel_header_in_external_panel=False):
        if show_panel_header_in_external_panel:
            self.main_container_paned.remove(self.panel_manager.panel_widget)
            new_container.add(self.panel_manager.panel_widget)
        else:
            self.panel_manager.panel_widget.remove(self.panel_manager.panel_scrolled)
            new_container.add(self.panel_manager.panel_scrolled)
            # remove empty panel (only header)
            self.main_container_paned.remove(self.panel_manager.panel_widget)
        self.external_panel = True

    def show_panel(self):
        if self.external_panel:
            self.panel_manager.panel_scrolled.show_all()
        else:
            paned_width = self.main_container_paned.get_allocation().width
            if self.panel_hidden:
                self.main_container_paned.set_position(round(paned_width*0.8)) # default value
                # if not hidden, keep position
            self.panel_manager.panel_widget.show_all()
            self.panel_hidden = False

    def close_panel(self):
        self.panel_manager.reset_panel()
        paned_width = self.main_container_paned.get_allocation().width
        self.main_container_paned.set_position(round(paned_width+0.5)) # ceil
        self.panel_hidden = True

    def main_container_paned_size_allocate(self, main_container, allocation):
        allocation_tuple = (allocation.x, allocation.y, allocation.width, allocation.height)
        if self.main_container_paned_size_allocate_first_call:
            # set initial value (hidden)
            main_container.set_position(round(allocation.width+0.5)) # ceil
            self.main_container_paned_size_allocate_first_call = False
            self.main_container_rel_pos = main_container.get_position() / allocation.width
        elif self.panel_hidden:
            # stay hidden
            # TODO this doesn't work
            main_container.set_position(round(allocation.width+0.5)) # ceil
        else:
            # either handle is moved or size is changed
            if allocation_tuple == self.container_size_last_allocation_tuple:
                # handle is moved (or something else)
                # store new relative position
                self.main_container_rel_pos = main_container.get_position() / allocation.width
            else:
                # keep relative position
                main_container.set_position(int(allocation.width * self.main_container_rel_pos))
                # don't update main_container_rel_pos here since this can cause drift in rel pos if size is changed fast
        self.container_size_last_allocation_tuple = allocation_tuple

    # content

    def reset_tree(self):
        if self.search_widget is not None:
            self.search_widget.hide_search_popover()
            self.search_widget.set_items_list(self.person_handle_list)
        self.close_panel()
        self.info_box_manager.close_info_box()

        self.canvas_manager.reset_canvas()
        self.minimap_manager.reset_minimap()

        self.num_persons_added = 0
        self.num_persons_matching_filter_added = 0
        self.num_missing_persons_added = 0
        self.num_families_added = 0
        self.person_handle_list = []

        self.position_of_handle = {}

    def add_person(self, person_handle, x, person_generation, alignment, ahnentafel=None):
        person = self.ftv.get_person_from_handle(person_handle)

        alive = probably_alive(person, self.ftv.dbstate.db)
        gender = person.get_gender()
        background_color, border_color = color_graph_box(alive, gender)

        if self.ftv._config.get("appearance.familytreeview-highlight-home-person"):
            home_person = self.ftv.dbstate.db.get_default_person()
            if home_person is not None:
                is_home_person = home_person.handle == person_handle
                if is_home_person:
                    background_color = config.get("colors.home-person")[config.get("colors.scheme")]

        matches_filter = self.tree_builder.filter_matches_person_handle(person_handle)
        if (
            self.ftv._config.get("appearance.familytreeview-filter-person-gray-out")
            and not matches_filter
        ):
            background_color = rgb_to_hex(
                # average of r, g, and b for all 3 values
                (sum(hex_to_rgb(background_color))//3,) * 3
            )

        round_lower_corners = alignment == "c"

        badges = self.ftv.badge_manager.get_person_badges(person_handle)

        content_items = self.ftv.config_provider.get_person_content_item_defs()

        # TODO Add an option to hide an item in an item is empty  for a
        # whole generation (especially images).

        for i_item, item in enumerate(content_items):
            item_type = item[0]
            item_data = {}
            if item[0] == "gutter":
                pass
            elif item[0] == "image":
                image_spec = self.ftv.get_image_spec(person, "person")
                item_data["image_spec"] = image_spec
            elif item[0] in ["name", "alt_name"]:
                if item[0] == "name":
                    name = person.get_primary_name()
                else:
                    alt_names = person.get_alternate_names()
                    if len(alt_names) > 0:
                        name = alt_names[0]
                    else:
                        name = None
                if name is not None:
                    num = self.ftv.abbrev_name_display.get_num_for_name_abbrev(name)
                    abbr_name_strs = self.ftv.abbrev_name_display.get_abbreviated_names(name, num=num)
                else:
                    abbr_name_strs = []
                item_type = "name" # for alt_name
                item_data["name"] = name
                item_data["abbr_name_strs"] = abbr_name_strs
            else:
                place_format = self.ftv._config.get("appearance.familytreeview-place-format")
                text = ""
                if item[0] in [
                    "birth_or_fallback",
                    "death_or_fallback",
                    "event",
                ]:
                    if item[0] == "birth_or_fallback":
                        event = get_birth_or_fallback(self.ftv.dbstate.db, person)
                    elif item[0] == "death_or_fallback":
                        event = get_death_or_fallback(self.ftv.dbstate.db, person)
                    elif item[0] == "event":
                        event = get_event_from_person(self.ftv.dbstate.db, person, item[1]["event_type"], item[1]["index"])
                    text = self.get_event_for_box(
                        event,
                        *self.get_args_for_event_for_box(item[1]),
                        place_format,
                    )
                elif item[0] == "birth_death_or_fallbacks":
                    birth_or_fallback = get_birth_or_fallback(self.ftv.dbstate.db, person)
                    text1 = self.get_event_for_box(
                        birth_or_fallback,
                        *self.get_args_for_event_for_box(item[1]),
                        place_format,
                    )
                    death_or_fallback = get_death_or_fallback(self.ftv.dbstate.db, person)
                    text2 = self.get_event_for_box(
                        death_or_fallback,
                        *self.get_args_for_event_for_box(item[1]),
                        place_format,
                    )
                    text = f"{text1} \u2013 {text2}" # en dash
                elif item[0] == "relationship":
                    if item[1]["rel_base"] == "active":
                        base_person_handle = self.ftv.get_active()
                        base_person = self.ftv.get_person_from_handle(base_person_handle)
                    elif item[1]["rel_base"] == "home":
                        base_person = self.ftv.dbstate.db.get_default_person()
                    if person is not None and base_person is not None:
                        text = self.ftv.uistate.relationship.get_one_relationship(
                            self.ftv.dbstate.db,
                            base_person,
                            person,
                        )
                elif item[0] == "attribute":
                    attribute_list = person.get_attribute_list()
                    for attr in attribute_list:
                        if attr.get_type() == item[1]["attribute_type"]:
                            text = attr.get_value()
                            break
                elif item[0] == "gender":
                    if item[1]["word_or_symbol"] == "Word":
                        text = format_gender([person.get_gender()]) # argument has to be an iterable
                    else:
                        if person.get_gender() == Person.FEMALE:
                            symbol = self.ftv.symbols.SYMBOL_FEMALE
                        elif person.get_gender() == Person.FEMALE:
                            symbol = self.ftv.symbols.SYMBOL_MALE
                        elif person.get_gender() == Person.UNKNOWN:
                            symbol = self.ftv.symbols.SYMBOL_ASEXUAL_SEXLESS
                        elif person.get_gender() == Person.OTHER:
                            symbol = self.ftv.symbols.SYMBOL_HERMAPHRODITE
                        else:
                            symbol = self.ftv.symbols.SYMBOL_ASEXUAL_SEXLESS # Unknown
                        if self.ftv.uistate and self.ftv.uistate.symbols:
                            text = self.ftv.symbols.get_symbol_for_string(symbol)
                        else:
                            text = self.ftv.symbols.get_symbol_fallback(symbol)
                elif item[0] == "gramps_id":
                    text = person.get_gramps_id()
                elif item[0] == "generation_num":
                    text = str(person_generation)
                elif item[0] == "genealogical_num":
                    if ahnentafel is None:
                        text = ""
                    else:
                        text = str(ahnentafel)
                elif item[0] == "tags":
                    tag_handle_list = person.get_tag_list()
                    text = self.get_tag_markup(tag_handle_list, item[1]["tag_visualization"])
                item_type = "text"
                item_data["text"] = text
            item = (item_type, item[1], item_data)
            content_items[i_item] = item

        person_bounds = self.canvas_manager.add_person(
            x, person_generation, content_items, background_color, border_color, alive, round_lower_corners,
            click_callback=lambda item, target, event: self._cb_person_clicked(person_handle, event, x, person_generation, alignment),
            badges=badges
        )
        self.minimap_manager.add_person(x, person_generation, background_color)

        self.num_persons_added += 1
        if matches_filter:
            self.num_persons_matching_filter_added += 1

        self.person_handle_list.append(person_handle)
        self.position_of_handle[person_handle] = [person_bounds["oc_x"], person_bounds["oc_y"]]

        return person_bounds

    def add_missing_person(self, x, person_generation, alignment, relationship, handle):
        fg_color_found, fg_color = self.main_widget.get_style_context().lookup_color('theme_fg_color')
        if fg_color_found:
            fg_color = tuple(fg_color)[:3]
        else:
            fg_color = (0, 0, 0)

        bg_color_found, bg_color = self.main_widget.get_style_context().lookup_color('theme_bg_color')
        if bg_color_found:
            bg_color = tuple(bg_color)[:3]
        else:
            bg_color = (1, 1, 1)

        background_color = rgb_to_hex(tuple(fgc*0.1+bgc*0.9 for fgc, bgc in zip(fg_color, bg_color)))
        border_color = "#000"

        round_lower_corners = alignment == "c"

        gutter_size = (
            self.canvas_manager.person_height
            - 2*self.canvas_manager.padding
            - 2*self.canvas_manager.line_height_px
        ) / 2
        content_items = [
            ("gutter", {"size": gutter_size}, {}),
            ("text", {"lines": 2}, {"text": "[missing]"})
        ]

        person_bounds = self.canvas_manager.add_person(
            x, person_generation, content_items, background_color, border_color,
            True, # no ribbon
            round_lower_corners,
            click_callback=lambda item, target, event: self._cb_missing_person_clicked(event, relationship, handle, alignment)
        )
        self.minimap_manager.add_person(x, person_generation, background_color)

        self.num_missing_persons_added += 1

        return person_bounds

    def add_family(self, family_handle, x, family_generation):
        family = self.ftv.dbstate.db.get_family_from_handle(family_handle)
        background_color, border_color = color_graph_family(family, self.ftv.dbstate)

        badges = self.ftv.badge_manager.get_family_badges(family_handle)

        content_items = self.ftv.config_provider.get_family_content_item_defs()

        for i_item, item in enumerate(content_items):
            item_type = item[0]
            item_data = {}
            if item[0] == "gutter":
                item_type = item[0]
            elif item[0] == "image":
                image_spec = self.ftv.get_image_spec(family, "family")
                item_data["image_spec"] = image_spec
            elif item[0] == "names":
                name1 = self.ftv.get_person_from_handle(family.get_father_handle()).get_primary_name()
                name2 = self.ftv.get_person_from_handle(family.get_mother_handle()).get_primary_name()

                if name1 is not None and name2 is not None:
                    if item[1]["name_format"] == 0:
                        num1 = self.ftv.abbrev_name_display.get_num_for_name_abbrev(name1)
                        num2 = self.ftv.abbrev_name_display.get_num_for_name_abbrev(name2)
                    else:
                        num1 = item[1]["name_format"]
                        num2 = item[1]["name_format"]
                    fmt_str = "%s \u2013 %s" # en dash
                    abbr_name_strs = self.ftv.abbrev_name_display.combine_abbreviated_names(
                        fmt_str, [name1, name2], [num1, num2]
                    )
                else:
                    abbr_name_strs = []
                item_data["names"] = [name1, name2]
                item_data["fmt_str"] = fmt_str
                item_data["abbr_name_strs"] = abbr_name_strs
            else:
                place_format = self.ftv._config.get("appearance.familytreeview-place-format")
                text = ""
                if item[0] == "rel_type":
                    text = str(family.get_relationship())
                elif item[0] in [
                    "marriage_or_fallback",
                    "divorce_or_fallback",
                    "event",
                ]:
                    if item[0] == "marriage_or_fallback":
                        event = get_marriage_or_fallback(self.ftv.dbstate.db, family)
                    elif item[0] == "divorce_or_fallback":
                        event = get_divorce_or_fallback(self.ftv.dbstate.db, family)
                    elif item[0] == "event":
                        event = get_event_from_family(self.ftv.dbstate.db, family, item[1]["event_type"], item[1]["index"])
                    text = self.get_event_for_box(
                        event,
                        *self.get_args_for_event_for_box(item[1]),
                        place_format,
                    )
                elif item[0] == "birth_death_or_fallbacks":
                    marriage_or_fallback = get_marriage_or_fallback(self.ftv.dbstate.db, family)
                    text1 = self.get_event_for_box(
                        marriage_or_fallback,
                        *self.get_args_for_event_for_box(item[1]),
                        place_format,
                    )
                    divorce_or_fallback = get_divorce_or_fallback(self.ftv.dbstate.db, family)
                    text2 = self.get_event_for_box(
                        divorce_or_fallback,
                        *self.get_args_for_event_for_box(item[1]),
                        place_format,
                    )
                    text = f"{text1} \u2013 {text2}" # en dash
                elif item[0] == "attribute":
                    attribute_list = family.get_attribute_list()
                    for attr in attribute_list:
                        if attr.get_type() == item[1]["attribute_type"]:
                            text = attr.get_value()
                            break
                elif item[0] == "gramps_id":
                    text = family.get_gramps_id()
                elif item[0] == "tags":
                    tag_handle_list = family.get_tag_list()
                    text = self.get_tag_markup(tag_handle_list, item[1]["tag_visualization"])
                item_type = "text"
                item_data["text"] = text 
            item = (item_type, item[1], item_data)
            content_items[i_item] = item

        family_bounds = self.canvas_manager.add_family(
            x, family_generation, content_items, background_color, border_color,
            click_callback=lambda item, target, event: self._cb_family_clicked(family_handle, event, x, family_generation),
            badges=badges
        )
        self.minimap_manager.add_family(x, family_generation, background_color)

        self.num_families_added += 1

        self.position_of_handle[family_handle] = [family_bounds["oc_x"], family_bounds["oc_y"]]

        return family_bounds

    def add_connection(self, x1, y1, x2, y2, ym=None, m=None, dashed=False, handle1=None, handle2=None):
        # assuming y1 < y2 (e.g. handle1 is ancestor)
        follow_on_click = self.ftv._config.get("experimental.familytreeview-connection-follow-on-click")
        if not follow_on_click or (handle1 is None and handle2 is None):
            click_callback = None
        else:
            click_callback = lambda item, target, event, ym: self._cb_connection_clicked(handle1, handle2, event, ym)
        self.canvas_manager.add_connection(
            x1, y1, x2, y2, ym=ym, m=m, dashed=dashed,
            click_callback=click_callback
        )

    def add_expander(self, x, y, ang, click_callback):
        self.canvas_manager.add_expander(x, y, ang, click_callback)

    # box helpers

    def get_event_for_box(self, event, event_type_visualization_type, display_date, display_only_year, date_compact, display_place, display_description, display_tags, tag_visualization, place_format):
        if event is None:
            return ""
        text = "" # required if no info is displayed
        if display_date:
            text = self.get_event_date_for_box(event, display_only_year, date_compact).strip()
        if display_place:
            text = (text + " " + self.get_event_place_for_box(event, place_format)).strip()
        if display_description:
            text = (text + " " + self.get_event_description_for_box(event)).strip()
        if display_tags:
            text = (text + " " + self.get_event_tags_for_box(event, tag_visualization)).strip()
        if "_only_if_empty" != event_type_visualization_type[-14:] or len(text) == 0:
            text = (self.get_event_type_visualization(event, event_type_visualization_type) + text).strip()
        return text

    def get_args_for_event_for_box(self, params):
        return [
            params["event_type_visualization"],
            params["date"],
            params["date_only_year"],
            params["date_compact"],
            params["place"],
            params["description"],
            params["tags"],
            params["tag_visualization"],
        ]

    def get_event_date_for_box(self, event, display_only_year, date_compact):
        if event is None:
            return ""
        if display_only_year:
            date = event.get_date_object()
            if date.get_year_valid():
                return str(date.get_year())
            return ""
        if date_compact:
            date_str = get_date_compact(event)
        else:
            date_str = get_date(event)
        date_bytes = date_str.encode("utf-8")
        date_escstr = GLib.markup_escape_text(date_bytes, len(date_bytes))
        return date_escstr

    def get_event_place_for_box(self, event, place_format):
        if event is None:
            return ""
        place_str = self.ftv.get_place_name_from_event(event, fmt=place_format)
        if place_str is not None and place_str != "":
            text = place_str
            return text.strip() # remove space after word/symbol as there is no place str
        return ""

    def get_event_description_for_box(self, event):
        if event is None:
            return ""
        return event.get_description()

    def get_event_tags_for_box(self, event, tag_visualization):
        if event is None:
            return ""
        return self.get_tag_markup(event.get_tag_list(), tag_visualization)

    def get_tag_markup(self, tag_handle_list, tag_visualization):
        tag_dicts = []
        for tag_handle in tag_handle_list:
            tag = self.ftv.dbstate.db.get_tag_from_handle(tag_handle)
            d = {}
            if tag_visualization != "text_names":
                d["color"] = tag.get_color()
            if tag_visualization[:11] != "tag_colors":
                d["name"] = tag.get_name()
            tag_dicts.append(d)
        if tag_visualization in ["text_colors_unique", "text_colors_counted"]:
            tag_colors = [
                d["color"]
                for d in tag_dicts
            ]
            tag_color_freq = {}
            for color in tag_colors:
                tag_color_freq.setdefault(color, 0)
                tag_color_freq[color] += 1
            tag_dicts = [
                {"color": k, "freq": v} # text_colors_unique: freq not used
                for k, v in tag_color_freq.items()
            ]

        text = ""
        for tag_dict in tag_dicts:
            if tag_visualization == "text_names":
                text += tag_dict["name"]
            else:
                if tag_visualization[:11] == "text_colors":
                    if tag_visualization == "text_colors_counted" and tag_dict["freq"] > 1:
                        text += str(tag_dict["freq"]) + "x" # e.g. "2x"
                    text += f"""<span fgcolor="{tag_dict["color"]}">⬤</span>"""
                elif tag_visualization == "text_names_colors":
                    bgcolor_hex = tag_dict["color"] # hex string
                    bgcolor_float_tuple = hex_to_rgb_float(bgcolor_hex)
                    fgcolor_float_tuple = get_contrast_color(bgcolor_float_tuple)
                    fgcolor_hex = rgb_to_hex(fgcolor_float_tuple)
                    tag_str = "\u00A0" + tag_dict["name"] + "\u00A0" # nb spaces for color padding
                    text += f"""<span fgcolor="{fgcolor_hex}" bgcolor="{bgcolor_hex}">{tag_str}</span>"""
            # Space at the end to separate tags.
            text += " "

        return text.strip() # remove last space

    def get_event_type_visualization(self, event, event_type_visualization_type):
        """Doesn't handle only_if_empty visualization types"""
        if event_type_visualization_type[:4] == "word":
            return str(event.type) + ": " # translated
        elif event_type_visualization_type[:6] == "symbol":
            return self.ftv.get_symbol(event.type) + " "
        # else event_type_visualization_type == "none"
        return ""

    # callbacks

    def _cb_person_clicked(self, person_handle, event, x, person_generation, alignment):
        action, is_single_click = self._get_click_config_action("person", event)

        if action == "open_info_box_person":
            fcn = self.info_box_manager.open_person_info_box
            data = [person_handle, x, person_generation, alignment]
        elif action == "open_panel_person":
            fcn = self.panel_manager.open_person_panel
            data = [person_handle]
        elif action == "edit_person":
            fcn = self.ftv.edit_person
            data = [person_handle]
        elif action == "set_active_person":
            fcn = self.ftv.set_active_person
            data = [person_handle]
        elif action == "set_home_person":
            fcn = self.ftv.set_home_person
            data = [person_handle, True] # also_set_active
        elif action == "open_context_menu_person":
            fcn = self.open_person_context_menu
            data = [person_handle, event, x, person_generation, alignment]
        else:
            return False

        self._process_click(is_single_click, fcn, *data)

        return True

    def _cb_missing_person_clicked(self, event, relationship, handle, alignment):
        if event.type != Gdk.EventType.DOUBLE_BUTTON_PRESS:
            return False

        if relationship is None:
            return False
        elif relationship == "root":
            return False # TODO
        elif relationship in ["spouse", "parent"]:
            fcn = self.ftv.add_new_parent_to_family
            family_handle = handle
            is_father = alignment == "r"
            args = [family_handle, is_father]
        else:
            return False
        self._process_click(False, fcn, *args)

        return True

    def _cb_family_clicked(self, family_handle, event, x, family_generation):
        action, is_single_click = self._get_click_config_action("family", event)

        if action == "open_info_box_family":
            fcn = self.info_box_manager.open_family_info_box
            data = [family_handle, x, family_generation]
        elif action == "open_panel_family":
            fcn = self.panel_manager.open_family_panel
            data = [family_handle]
        elif action == "edit_family":
            fcn = self.ftv.edit_family
            data = [family_handle]
        elif action == "set_active_family":
            fcn = self.ftv.set_active_family
            data = [family_handle]
        # no home family option
        elif action == "open_context_menu_family":
            fcn = self.open_family_context_menu
            data = [family_handle, event, x, family_generation]
        else:
            return False

        self._process_click(is_single_click, fcn, *data)

        return True

    def _cb_connection_clicked(self, handle1, handle2, event, ym):
        # assuming (y of handle 1) < (y of handle 2) (e.g. handle1 is ancestor)
        if event.type != Gdk.EventType.DOUBLE_BUTTON_PRESS:
            return False

        def move_to_target():
            # small distance to deactivate center
            # Has to be larger that half of the width of the additional (wider, invisible) connection.
            dy = 5
            
            # NOTE: event.y is in same units as ym
            if event.y < ym-dy: # smaller/negative y: up in view
                # clicked near the ancestor (1), go to descendant (2)
                target_handle = handle2
            elif event.y > ym+dy:
                # clicked near the descendant (2), go to ancestor (1)
                target_handle = handle1
            else:
                # center is ambiguous
                target_handle = None
            if target_handle is not None and target_handle in self.position_of_handle:
                self.canvas_manager.move_to_center(*self.position_of_handle[target_handle])

        self._process_click(False, move_to_target)

    def _cb_background_clicked(self, root_item, target, event):
        action, is_single_click = self._get_click_config_action("background", event)

        if action == "open_context_menu_background":
            fcn = self.open_background_context_menu
            data = [event]
        elif action == "zoom_in":
            fcn = self.canvas_manager.zoom_in
            data = []
        elif action == "zoom_out":
            fcn = self.canvas_manager.zoom_out
            data = []
        elif action == "zoom_reset":
            fcn = self.canvas_manager.reset_zoom
            data = []
        elif action == "scroll_to_active_person":
            fcn = self.scroll_to_active_person
            data = []
        elif action == "scroll_to_home_person":
            fcn = self.scroll_to_home_person
            data = []
        elif action == "scroll_to_active_family":
            fcn = self.scroll_to_active_family
            data = []
        else:
            return False

        self._process_click(is_single_click, fcn, *data)

    def _get_click_config_action(self, click_type, event):
        if event.type == Gdk.EventType.BUTTON_PRESS:
            if event.button == 1: # primary
                action = self.ftv._config.get(f"interaction.familytreeview-{click_type}-single-primary-click-action")
            elif event.button == 3: # secondary
                action = self.ftv._config.get(f"interaction.familytreeview-{click_type}-single-secondary-click-action")
            elif event.button == 2: # middle
                action = self.ftv._config.get(f"interaction.familytreeview-{click_type}-single-middle-click-action")
            else:
                action = None
            is_single_click = True
        elif event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            if event.button == 1: # primary
                action = self.ftv._config.get(f"interaction.familytreeview-{click_type}-double-primary-click-action")
            elif event.button == 3: # secondary
                action = self.ftv._config.get(f"interaction.familytreeview-{click_type}-double-secondary-click-action")
            elif event.button == 2: # middle
                action = self.ftv._config.get(f"interaction.familytreeview-{click_type}-double-middle-click-action")
            else:
                action = None
            is_single_click = False
        else:
            return (None, False)
        return (action, is_single_click)

    def _process_click(self, is_single_click, function, *data):
        if is_single_click:
            interval = self.ftv._config.get("interaction.familytreeview-double-click-timeout-milliseconds")
            def cb_call_function_once():
                # Make sure the callback returns False so that it's called repeatedly.
                function(*data)
                return False
            click_event_source_id = GLib.timeout_add(interval, cb_call_function_once)
            self.click_event_sources.append(GLib.main_context_default().find_source_by_id(click_event_source_id))
        else:
            for source in self.click_event_sources:
                if not source.is_destroyed():
                    GLib.source_remove(source.get_id())
            self.click_event_sources.clear()
            function(*data)

    def scroll_to_active_person(self):
        active_person_handle = self.ftv.get_active()
        if active_person_handle is None or len(active_person_handle) == 0:
            return
        try:
            active_pos = self.position_of_handle[active_person_handle]
        except KeyError:
            return
        self.canvas_manager.move_to_center(*active_pos)

    def scroll_to_home_person(self):
        home_person = self.ftv.dbstate.db.get_default_person()
        if home_person is None:
            return
        try:
            active_pos = self.position_of_handle[home_person.handle]
        except KeyError:
            return
        self.canvas_manager.move_to_center(*active_pos)

    def scroll_to_active_family(self):
        active_family_handle = self.ftv.get_active_family_handle()
        if active_family_handle is None or len(active_family_handle) == 0:
            return
        try:
            active_pos = self.position_of_handle[active_family_handle]
        except KeyError:
            return
        self.canvas_manager.move_to_center(*active_pos)

    def open_person_context_menu(self, person_handle, event, x, person_generation, alignment):
        self.menu = Gtk.Menu()

        menu_item = Gtk.MenuItem(label=_("Edit"))
        menu_item.connect("activate", lambda *_args:
            self.ftv.edit_person(person_handle)
        )
        self.menu.append(menu_item)

        person = self.ftv.get_person_from_handle(person_handle)
        associated_people_handles = []
        for person_ref in person.get_person_ref_list():
            associated_people_handles.append(person_ref.get_reference_handle())
        if len(associated_people_handles) > 0:
            submenu = Gtk.Menu()
            menu_item = Gtk.MenuItem(label=_("Set associated person as active"))
            menu_item.set_submenu(submenu)
            menu_item.show()
            self.menu.append(menu_item)

            for associated_person_handle in associated_people_handles:
                person = self.ftv.get_person_from_handle(associated_person_handle)
                name = person.get_primary_name()
                menu_item = Gtk.MenuItem(label=name_displayer.display_name(name))
                menu_item.connect("activate", lambda *_args:
                    self.ftv.set_active_person(associated_person_handle)
                )
                submenu.append(menu_item)

            ## TODO: Add witnesses at this person's main event
            ## TODO: Add main people at event this person witnessed

        menu_item = Gtk.MenuItem(label=_("Set as home person"))
        menu_item.connect("activate", lambda *_args:
            self.ftv.set_home_person(person_handle)
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Set as active person"))
        menu_item.connect("activate", lambda *_args:
            self.ftv.set_active_person(person_handle)
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Open info box"))
        menu_item.connect("activate", lambda *_args:
            self.info_box_manager.open_person_info_box(person_handle, x, person_generation, alignment)
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Open panel"))
        menu_item.connect("activate", lambda *_args:
            self.panel_manager.open_person_panel(person_handle)
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Add new parents family"))
        menu_item.connect("activate", lambda *_args:
            self.ftv.add_new_parent_family(person_handle)
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Add new family as husband"))
        menu_item.connect("activate", lambda *_args:
            self.ftv.add_new_spouse(person_handle, wife=True)
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Add new family as wife"))
        menu_item.connect("activate", lambda *_args:
            self.ftv.add_new_spouse(person_handle, wife=False)
        )
        self.menu.append(menu_item)

        self.show_menu(event)

    def open_family_context_menu(self, family_handle, event, x, family_generation):
        self.menu = Gtk.Menu()

        menu_item = Gtk.MenuItem(label=_("Edit"))
        menu_item.connect("activate", lambda *_args:
            self.ftv.edit_family(family_handle)
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Open info box"))
        menu_item.connect("activate", lambda *_args:
            self.info_box_manager.open_family_info_box(family_handle, x, family_generation)
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Open panel"))
        menu_item.connect("activate", lambda *_args:
            self.panel_manager.open_family_panel(family_handle)
        )
        self.menu.append(menu_item)

        self.show_menu(event)

    def open_background_context_menu(self, event):
        self.menu = Gtk.Menu()

        menu_item = Gtk.MenuItem(label=_("Zoom in"))
        menu_item.connect("activate", lambda *_args:
            self.canvas_manager.zoom_in()
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Zoom out"))
        menu_item.connect("activate", lambda *_args:
            self.canvas_manager.zoom_out()
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Reset zoom"))
        menu_item.connect("activate", lambda *_args:
            self.canvas_manager.reset_zoom()
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Scroll to active person"))
        menu_item.connect("activate", lambda *_args:
            self.scroll_to_active_person()
        )
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Scroll to home person"))
        menu_item.connect("activate", lambda *_args:
            self.scroll_to_home_person()
        )
        home_person = self.ftv.dbstate.db.get_default_person()
        if home_person is None:
            home_person_in_tree = False
        else:
            home_person_in_tree = home_person.handle in self.position_of_handle
        menu_item.set_sensitive(home_person_in_tree)
        self.menu.append(menu_item)

        menu_item = Gtk.MenuItem(label=_("Scroll to active family"))
        menu_item.connect("activate", lambda *_args:
            self.scroll_to_active_family()
        )
        active_family_handle = self.ftv.get_active_family_handle()
        active_family_set = (
            active_family_handle is not None
            and len(active_family_handle) > 0
        )
        menu_item.set_sensitive(active_family_set)
        self.menu.append(menu_item)

        self.show_menu(event)

    def show_menu(self, orig_event):
        self.menu.show_all()

        # We cannot use the original click event here because it is
        # garbage collected (at least as I understand it), which causes
        # event.window to be None, for example. The garbage collection
        # is triggered because we are delaying the call to this method
        # with timeout_add to detect double clicks. We need to create a
        # new event.
        new_event = Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
        new_event.window = self.main_widget.get_window()
        seat = self.main_widget.get_display().get_default_seat()
        new_event.device = seat.get_pointer() or seat.get_keyboard()
        new_event.x = orig_event.x
        new_event.y = orig_event.y
        new_event.button = orig_event.button
        new_event.time = orig_event.time
        self.menu.popup_at_pointer(new_event)

    def add_to_provider(self, s):
        self.provider_str += s
        self.provider.load_from_data(self.provider_str.encode())
