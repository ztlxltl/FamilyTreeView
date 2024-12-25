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

from gi.repository import Gdk, GLib, Gtk

from gramps.gen.config import config
from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.datehandler import get_date
from gramps.gen.utils.alive import probably_alive
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback, get_marriage_or_fallback
from gramps.gui.utils import color_graph_box, color_graph_family

from family_tree_view_canvas_manager import FamilyTreeViewCanvasManager
from family_tree_view_info_box_manager import FamilyTreeViewInfoBoxManager
from family_tree_view_minimap_manager import FamilyTreeViewMinimapManager
from family_tree_view_panel_manager import FamilyTreeViewPanelManager
from family_tree_view_tree_builder import FamilyTreeViewTreeBuilder
from family_tree_view_utils import import_GooCanvas
if TYPE_CHECKING:
    from family_tree_view import FamilyTreeView


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

        self.toolbar = Gtk.Box(spacing=4, orientation=Gtk.Orientation.HORIZONTAL)
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

        self.panel_hidden = True

        self.click_event_sources = [] # to wait for double clicks

    def show_panel(self):
        paned_width = self.main_container_paned.get_allocation().width
        if self.panel_hidden:
            self.main_container_paned.set_position(round(paned_width*0.8)) # default value
            # if not hidden, keep position
        self.main_container_paned.show_all()
        self.panel_hidden = False

    def close_panel(self):
        self.panel_manager.reset_panel()
        paned_width = self.main_container_paned.get_allocation().width
        self.main_container_paned.set_position(round(paned_width+0.5)) # ceil
        self.main_container_paned.show_all()
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

    def add_person(self, person_handle, x, person_generation, alignment):
        person = self.ftv.get_person_from_handle(person_handle)

        name_str = self.ftv.name_display.display_name(person.get_primary_name())
        abbr_name_strs = self.ftv.name_display.get_abbreviated_names(person.get_primary_name())
        birth_or_fallback = get_birth_or_fallback(self.ftv.dbstate.db, person)
        death_or_fallback = get_death_or_fallback(self.ftv.dbstate.db, person)
        if birth_or_fallback is not None:
            birth_date = f"{self.ftv.get_symbol(birth_or_fallback.type)} {get_date(birth_or_fallback)}"
        else:
            birth_date = ""
        if death_or_fallback is not None:
            death_date = f"{self.ftv.get_symbol(death_or_fallback.type)} {get_date(death_or_fallback)}"
        else:
            death_date = ""
        image_spec = self.ftv.get_image_spec(person)

        alive = probably_alive(person, self.ftv.dbstate.db)
        gender = person.get_gender()
        background_color, border_color = color_graph_box(alive, gender)
        home_person = self.ftv.dbstate.db.get_default_person()
        if home_person is not None:
            is_home_person = home_person.handle == person_handle
            if is_home_person:
                background_color = config.get("colors.home-person")[config.get("colors.scheme")]

        round_lower_corners = alignment == "c"

        badges = self.ftv.badge_manager.get_person_badges(person_handle)

        person_bounds = self.canvas_manager.add_person(
            x, person_generation, name_str, abbr_name_strs, birth_date, death_date, background_color, border_color, image_spec, alive, round_lower_corners,
            click_callback=lambda item, target, event: self._cb_person_clicked(person_handle, event, x, person_generation, alignment),
            badges=badges
        )
        self.minimap_manager.add_person(x, person_generation, background_color)

        return person_bounds

    def add_missing_person(self, x, person_generation, alignment):
        background_color = "#ddd"
        border_color = "#000"

        round_lower_corners = alignment == "c"

        person_bounds = self.canvas_manager.add_person(
            x, person_generation, "", [""], "", "", background_color, border_color,
            None, # no image
            True, # no ribbon
            round_lower_corners,
            click_callback=None # TODO create new person
        )
        self.minimap_manager.add_person(x, person_generation, background_color)

        return person_bounds

    def add_family(self, family_handle, x, family_generation):
        family = self.ftv.dbstate.db.get_family_from_handle(family_handle)
        background_color, border_color = color_graph_family(family, self.ftv.dbstate)

        marriage_or_fallback = get_marriage_or_fallback(self.ftv.dbstate.db, family)
        if marriage_or_fallback is not None:
            marriage_date = f"{self.ftv.get_symbol(marriage_or_fallback.type)} {get_date(marriage_or_fallback)}"
        else:
            marriage_date = ""

        badges = self.ftv.badge_manager.get_family_badges(family_handle)

        family_bounds = self.canvas_manager.add_family(
            x, family_generation, marriage_date, background_color, border_color,
            click_callback=lambda item, target, event: self._cb_family_clicked(family_handle, event, x, family_generation),
            badges=badges
        )
        self.minimap_manager.add_family(x, family_generation, background_color)

        return family_bounds

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
            function = self.panel_manager.open_person_panel
            data = [family_handle]
        elif action == 3: # edit
            function = self.ftv.edit_family
            data = [family_handle]
        else:
            return False

        self._process_click(is_single_click, function, *data)

        return True

    def _process_click(self, is_single_click, function, *data):
        if is_single_click:
            interval = self.ftv._config.get("interaction.familytreeview-double-click-timeout-milliseconds")
            click_event_source_id = GLib.timeout_add(interval, function, *data)
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
