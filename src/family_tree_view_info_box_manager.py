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


from gi.repository import Gdk, GLib, Gtk

from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.utils.alive import probably_alive

from family_tree_view_info_widget_manager import FamilyTreeViewInfoWidgetManager


class FamilyTreeViewInfoBoxManager(FamilyTreeViewInfoWidgetManager):
    def __init__(self, widget_manager):
        super().__init__(widget_manager)
        self.overlay_container = self.widget_manager.info_box_overlay_container

        self.spacing = 10

        r = self.canvas_manager.corner_radius
        # TODO For some reason self.widget_manager.provider doesn't work.
        provider = Gtk.CssProvider()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        provider.load_from_data(f"""
            #ftv-info-box {{
                background-color: mix(@theme_fg_color, @theme_bg_color, 0.85);
                border-radius: {r}px;
                padding: {r}px;
                border: 2px solid black;
            }}
            #ftv-info-box #ftv-tag-circle{{ /* hole needs same color as background */
                background-color: mix(@theme_fg_color, @theme_bg_color, 0.85);
            }}
        """.encode())

        self.info_box_widget = None
        self.position_child_connection_handle = None

    def open_person_info_box(self, person_handle, x, person_generation, alignment):
        self.close_info_box()

        person = self.ftv.get_person_from_handle(person_handle)
        name_str = name_displayer.display_name(person.get_primary_name())

        self.info_box_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.info_box_widget.set_spacing(self.spacing)
        self.info_box_widget.set_name("ftv-info-box")

        base_info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        base_info.set_spacing(self.spacing)
        image_filter = self.ftv._config.get("appearance.familytreeview-person-image-filter")
        if image_filter == "grayscale_dead":
            grayscale = not probably_alive(person, self.ftv.dbstate.db)
        else:
            grayscale = image_filter == "grayscale_all"
        image = self.create_image_widget(person, grayscale=grayscale)
        if image is not None:
            base_info.add(image)
        base_data = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        base_data.set_spacing(self.spacing)
        name = Gtk.Label()
        name.set_markup(f"<big><b>{name_str}</b></big>")# TODO size
        name.set_line_wrap(True)
        name.set_xalign(0)
        base_data.add(name)
        main_events = self.create_person_base_events_widget(person)
        base_data.add(main_events)
        base_info.add(base_data)
        self.info_box_widget.add(base_info)

        buttons = self.create_person_buttons_widget(person_handle, x, person_generation)
        self.info_box_widget.add(buttons)

        tags = self.create_tags_widget(person)
        self.info_box_widget.add(tags)

        y = self.widget_manager.tree_builder.get_y_of_generation(person_generation)
        self.info_box_height = 50 # default, height is adjusted to fit content later
        self.finalize_info_box(
            x, y,
            350,
            self.canvas_manager.person_height, # bottom aligned at person
            alignment
        )

    def open_family_info_box(self, family_handle, x, family_generation):
        self.close_info_box()

        family = self.ftv.dbstate.db.get_family_from_handle(family_handle)

        self.info_box_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.info_box_widget.set_spacing(self.spacing)
        self.info_box_widget.set_name("ftv-info-box")

        base_info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        base_info.set_spacing(self.spacing)

        image_filter = self.ftv._config.get("appearance.familytreeview-person-image-filter")
        grayscale = image_filter == "grayscale_all"
        image = self.create_image_widget(family, obj_type="family", only_media=True, grayscale=grayscale)
        if image is not None:
            base_info.add(image)

        main_events = self.create_family_base_events_widget(family)
        base_info.add(main_events)

        self.info_box_widget.add(base_info)

        buttons = self.create_family_buttons_widget(family_handle, x, family_generation)
        self.info_box_widget.add(buttons)

        tags = self.create_tags_widget(family)
        self.info_box_widget.add(tags)

        y = self.widget_manager.tree_builder.get_y_of_generation(family_generation) + self.canvas_manager.above_family_sep
        self.info_box_height = 50 # default, height is adjusted to fit content later
        self.finalize_info_box(
            x, y,
            300,
            0 # top aligned
        )

    def finalize_info_box(self, x, y, info_box_width, base_height, alignment=None):
        offset = 1 # offset required to show full border of info_box

        canvas = self.canvas_manager.canvas

        def position_child(overlay, child_widget, allocation):
            canvas_scale = self.canvas_manager.get_scale()
            origin_px = canvas.convert_to_pixels(0, 0)
            if alignment == "l":
                # anchor bottom left
                x_pos = self.canvas_manager.person_width/2*canvas_scale
                y_pos = self.info_box_height
            elif alignment == "r":
                # anchor bottom right
                x_pos = -self.canvas_manager.person_width/2*canvas_scale + info_box_width
                y_pos = self.info_box_height
            else: # alignment == "c" or family
                # anchor top center
                # top since center-aligned persons are without family and only have a connection to ancestors
                x_pos = info_box_width/2
                y_pos = base_height*canvas_scale
            allocation.x = -self.canvas_manager.hadjustment.get_value() + origin_px.x + x*canvas_scale - x_pos
            allocation.y = -self.canvas_manager.vadjustment.get_value() + origin_px.y + y*canvas_scale - y_pos
            allocation.width = info_box_width+2*offset
            allocation.height = self.info_box_height+2*offset
            return True

        # TODO: Why does this not work?
        # self.info_box_widget.connect("scroll-event", lambda widget, event: Gtk.propagate_event(self.canvas_manager.zoom_at_pointer, event))

        # Make the info box invisible (without changing it's size,
        # set_visible(False) or hide() would change it)
        # to get the natural value for self.info_box_height later.
        # Leaving it visible would cause a flickering, immediate height change.
        self.info_box_widget.set_opacity(0)

        # self.info_box_widget is hidden for some reason:
        self.info_box_widget.show_all()

        # The info box uses an overlay as it's size should be independent on zoom,
        # i.e. you should be able to read info on persons when zoomed out.
        # Furthermore, buttons are in the info box and zoom cannot be applied to widgets.
        self.position_child_connection_handle = self.overlay_container.connect("get-child-position", position_child)
        self.overlay_container.add_overlay(self.info_box_widget)

        # adjust height to content
        # TODO: Why is sometimes the height too big?
        def set_height():
            self.info_box_height = self.info_box_widget.get_preferred_height().natural_height
            self.info_box_widget.queue_resize() # indirectly calls position_child
            self.info_box_widget.set_opacity(1) # make visible after setting correct height
        GLib.idle_add(set_height)

    def close_info_box(self):
        if self.info_box_widget is None:
            return False
        self.info_box_widget.destroy()
        self.info_box_widget = None
        if self.position_child_connection_handle is not None:
            self.overlay_container.disconnect(self.position_child_connection_handle)
            self.position_child_connection_handle = None
        return True
