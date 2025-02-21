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


import os
import sys
from typing import TYPE_CHECKING

from gi.repository import Gdk, GLib, Gtk

from gramps.gen.config import config
from gramps.gen.const import GRAMPS_LOCALE, USER_PLUGINS
from gramps.gen.datehandler import get_date
from gramps.gen.lib import Person
from gramps.gen.utils.alive import probably_alive
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback, get_marriage_or_fallback, get_divorce_or_fallback
from gramps.gen.utils.string import format_gender
from gramps.gui.utils import color_graph_box, color_graph_family, get_contrast_color, hex_to_rgb, hex_to_rgb_float, rgb_to_hex

from family_tree_view_canvas_manager import FamilyTreeViewCanvasManager
from family_tree_view_info_box_manager import FamilyTreeViewInfoBoxManager
from family_tree_view_minimap_manager import FamilyTreeViewMinimapManager
from family_tree_view_panel_manager import FamilyTreeViewPanelManager
from family_tree_view_tree_builder import FamilyTreeViewTreeBuilder
from family_tree_view_utils import get_event_from_family, get_event_from_person, import_GooCanvas
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

_ = GRAMPS_LOCALE.translation.gettext

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
        self.num_persons_not_matching_filter_added = 0
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

        self.main_container_paned = Gtk.Paned()
        self.main_container_paned_size_allocate_first_call = True
        self.main_container_paned.connect("size-allocate", self.main_container_paned_size_allocate)

        self.canvas_manager = FamilyTreeViewCanvasManager(self, resize_reference=self.main_container_paned)
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
        self.main_widget.pack_start(self.main_container_paned, True, True, 0)
        self.external_panel = False

        self.panel_hidden = True

        self.click_event_sources = [] # to wait for double clicks

        self.position_of_handle = {} # keep record of what is placed where

    def use_internal_handle(self):
        # TODO skip if Gramps is closed
        if self.panel_manager.panel_widget.get_parent() != self.main_container_paned:
            if self.panel_manager.panel_widget.get_parent() is not None:
                self.panel_manager.panel_widget.get_parent().remove(self.panel_manager.panel_widget)
            self.main_container_paned.pack2(self.panel_manager.panel_widget)
        if self.panel_manager.panel_scrolled.get_parent() != self.panel_manager.panel_widget:
            if self.panel_manager.panel_scrolled.get_parent() is not None:
                self.panel_manager.panel_scrolled.get_parent().remove(self.panel_manager.panel_scrolled)
            self.panel_manager.panel_widget.add(self.panel_manager.panel_scrolled)
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
        self.canvas_manager.reset_canvas()
        self.minimap_manager.reset_minimap()

        self.num_persons_added = 0
        self.num_persons_not_matching_filter_added = 0
        self.num_missing_persons_added = 0
        self.num_families_added = 0
        self.person_handle_list = []
        if self.search_widget is not None:
            self.search_widget.hide_search_popover()
            self.search_widget.set_items_list(self.person_handle_list)

    def add_person(self, person_handle, x, person_generation, alignment, ahnentafel=None):
        person = self.ftv.get_person_from_handle(person_handle)

        alive = probably_alive(person, self.ftv.dbstate.db)
        gender = person.get_gender()
        background_color, border_color = color_graph_box(alive, gender)
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
        if not matches_filter:
            self.num_persons_not_matching_filter_added += 1

        self.person_handle_list.append(person_handle)
        self.position_of_handle[person_handle] = [person_bounds["oc_x"], person_bounds["oc_y"]]

        return person_bounds

    def add_missing_person(self, x, person_generation, alignment):
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
            click_callback=None # TODO create new person
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
            click_callback = lambda item, target, event, ym: self._db_connection_clicked(handle1, handle2, event, ym)
        self.canvas_manager.add_connection(
            x1, y1, x2, y2, ym=ym, m=m, dashed=dashed,
            click_callback=click_callback
        )

    def add_expander(self, x, y, ang, click_callback):
        self.canvas_manager.add_expander(x, y, ang, click_callback)

    # box helpers

    def get_event_for_box(self, event, event_type_visualization_type, display_date, display_only_year, display_place, display_description, display_tags, tag_visualization, place_format):
        if event is None:
            return ""
        text = "" # required if no info is displayed
        if display_date:
            text = self.get_event_date_for_box(event, display_only_year).strip()
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
            params["place"],
            params["description"],
            params["tags"],
            params["tag_visualization"],
        ]

    def get_event_date_for_box(self, event, display_only_year):
        if event is None:
            return ""
        if display_only_year:
            date = event.get_date_object()
            if date.get_year_valid():
                return str(date.get_year())
            return ""
        return get_date(event)

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
        is_single_click = True
        if event.type == Gdk.EventType.BUTTON_PRESS:
            action = self.ftv._config.get("interaction.familytreeview-person-single-click-action")
        elif event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            action = self.ftv._config.get("interaction.familytreeview-person-double-click-action")
            is_single_click = False
        else:
            return False

        if action == 1: # info box
            function = self.info_box_manager.open_person_info_box
            data = [person_handle, x, person_generation, alignment]
        elif action == 2: # side panel
            function = self.panel_manager.open_person_panel
            data = [person_handle]
        elif action == 3: # edit
            function = self.ftv.edit_person
            data = [person_handle]
        elif action == 4: # set as active
            function = self.ftv.set_active_person
            data = [person_handle]
        elif action == 5: # set as home
            function = self.ftv.set_home_person()
            data = [person_handle, True] # also_set_active
        else:
            return False

        self._process_click(is_single_click, function, *data)

        return True

    def _cb_family_clicked(self, family_handle, event, x, family_generation):
        is_single_click = True
        if event.type == Gdk.EventType.BUTTON_PRESS:
            action = self.ftv._config.get("interaction.familytreeview-family-single-click-action")
        elif event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            action = self.ftv._config.get("interaction.familytreeview-family-double-click-action")
            is_single_click = False
        else:
            return False

        if action == 1: # info box
            function = self.info_box_manager.open_family_info_box
            data = [family_handle, x, family_generation]
        elif action == 2: # side panel
            function = self.panel_manager.open_family_panel
            data = [family_handle]
        elif action == 3: # edit
            function = self.ftv.edit_family
            data = [family_handle]
        else:
            return False

        self._process_click(is_single_click, function, *data)

        return True

    def _db_connection_clicked(self, handle1, handle2, event, ym):
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

    def add_to_provider(self, s):
        self.provider_str += s
        self.provider.load_from_data(self.provider_str.encode())
