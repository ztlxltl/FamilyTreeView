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

from gi.repository import Gdk, Gtk

from family_tree_view_utils import import_GooCanvas
if TYPE_CHECKING:
    from family_tree_view_widget_manager import FamilyTreeViewWidgetManager


GooCanvas = import_GooCanvas()

class FamilyTreeViewMinimapManager:
    def __init__(self, widget_manager: "FamilyTreeViewWidgetManager"):
        self.widget_manager = widget_manager
        self.ftv = self.widget_manager.ftv
        self.canvas_manager = self.widget_manager.canvas_manager

        self.widget_manager.add_to_provider("""
            #minimap-outer-container {
                padding: 5px;
                border-radius: 5px;
            }
            #minimap-inner-container {
                padding: 8px;
                border-radius: 8px;
                background-color: #aaa
            }
            #minimap-canvas {
                background-color: #fff
            }
        """)

        self.minimap_width = 150
        self.minimap_height = 150
        self.minimap_padding = 5

        self.minimap_outer_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.minimap_outer_container.set_name("minimap-outer-container")
        self.minimap_outer_container.set_halign(Gtk.Align.START)
        self.minimap_outer_container.set_valign(Gtk.Align.END)

        self.minimap_button_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.minimap_button = Gtk.Button()
        self.minimap_button.connect("clicked", self.minimap_button_clicked)
        self.arrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.DOWN, shadow_type=Gtk.ShadowType.NONE)
        self.minimap_button.add(self.arrow)
        self.minimap_button_container.add(self.minimap_button)
        self.minimap_outer_container.add(self.minimap_button_container)

        self.minimap_inner_container = Gtk.Box()
        self.minimap_inner_container.set_name("minimap-inner-container")
        self.minimap_canvas = GooCanvas.Canvas()
        self.minimap_canvas.set_name("minimap-canvas")
        self.minimap_canvas.set_scale(1/10)
        self.minimap_canvas.set_size_request(self.minimap_width, self.minimap_height)
        self.minimap_inner_container.add(self.minimap_canvas)
        self.minimap_outer_container.add(self.minimap_inner_container)

        self.init_minimap()

        self.minimap_view_rect = None
        self.widget_manager.canvas_manager.canvas_container.connect("size-allocate", self.set_view_rect)
        self.widget_manager.canvas_manager.hadjustment.connect("value-changed", self.set_view_rect)
        self.widget_manager.canvas_manager.vadjustment.connect("value-changed", self.set_view_rect)

    def reset_minimap(self):
        self.minimap_canvas.get_root_item().remove()
        new_default_root_item = GooCanvas.CanvasGroup()
        self.minimap_canvas.set_root_item(new_default_root_item)
        self.init_minimap()

    def init_minimap(self):
        self.minimap_bounds = [0, 0, 0, 0] # left, top, right, bottom
        self.content_group = GooCanvas.CanvasGroup(
            parent=self.minimap_canvas.get_root_item()
        )

    def set_view_rect(self, *_):
        canvas_allocation = self.canvas_manager.canvas_container.get_allocation()
        scale = self.canvas_manager.get_scale()
        canvas_bounds = self.canvas_manager.canvas.get_bounds()
        hadj = self.canvas_manager.hadjustment.get_value()
        vadj = self.canvas_manager.vadjustment.get_value()

        if self.minimap_view_rect is not None:
            self.minimap_view_rect.remove()

        self.minimap_view_rect = GooCanvas.CanvasRect(
            parent=self.minimap_canvas.get_root_item(),
            x=hadj/scale + canvas_bounds[0],
            y=vadj/scale + canvas_bounds[1],
            height=canvas_allocation.height/scale,
            width=canvas_allocation.width/scale,
            fill_color_gdk_rgba=Gdk.RGBA(0, 0, 0, 0.25),
            stroke_color="#000",
            line_width=20
        )

    def adjust_bounds(self, left, top, right, bottom):
        self.minimap_bounds[0] = min(self.minimap_bounds[0], left)
        self.minimap_bounds[1] = min(self.minimap_bounds[1], top)
        self.minimap_bounds[2] = max(self.minimap_bounds[2], right)
        self.minimap_bounds[3] = max(self.minimap_bounds[3], bottom)
        scale = min(
            (self.minimap_width - 2*self.minimap_padding)/(self.minimap_bounds[2] - self.minimap_bounds[0]),
            (self.minimap_height - 2*self.minimap_padding)/(self.minimap_bounds[3] - self.minimap_bounds[1])
        )
        self.minimap_canvas.set_scale(scale)

        # center tree in minimap
        h_extra = self.minimap_width - scale*(self.minimap_bounds[2] - self.minimap_bounds[0])
        v_extra = self.minimap_height - scale*(self.minimap_bounds[3] - self.minimap_bounds[1])
        self.minimap_canvas.set_bounds(
            self.minimap_bounds[0] - h_extra/scale/2,
            self.minimap_bounds[1] - v_extra/scale/2,
            self.minimap_bounds[2] + h_extra/scale/2,
            self.minimap_bounds[3] + v_extra/scale/2
        )

    def add_person(self, x, person_generation, background_color):
        y = self.widget_manager.tree_builder.get_y_of_generation(person_generation)-self.canvas_manager.person_height
        GooCanvas.CanvasRect(
            parent=self.content_group,
            x=x-self.canvas_manager.person_width/2,
            y=y,
            height=self.canvas_manager.person_height,
            width=self.canvas_manager.person_width,
            fill_color=background_color,
            line_width=0
        )
        self.adjust_bounds(x-self.canvas_manager.person_width/2, y, x+self.canvas_manager.person_width/2, y+self.canvas_manager.person_height)
        self.minimap_outer_container.show_all()

    def add_family(self, x, family_generation, background_color):
        y = self.widget_manager.tree_builder.get_y_of_generation(family_generation)+self.canvas_manager.above_family_sep
        GooCanvas.CanvasRect(
            parent=self.content_group,
            x=x-self.canvas_manager.family_width/2,
            y=y,
            height=self.canvas_manager.family_height,
            width=self.canvas_manager.family_width,
            fill_color=background_color,
            line_width=0
        )
        self.adjust_bounds(x-self.canvas_manager.family_width/2, y, x+self.canvas_manager.family_width/2, y+self.canvas_manager.family_height)
        self.minimap_outer_container.show_all()

    def minimap_button_clicked(self, *_):
        if self.minimap_inner_container.get_visible():
            self.minimap_inner_container.set_visible(False)
            arrow_type = Gtk.ArrowType.UP
        else:
            self.minimap_inner_container.set_visible(True)
            arrow_type = Gtk.ArrowType.DOWN
        self.arrow.set(arrow_type=arrow_type, shadow_type=Gtk.ShadowType.NONE)