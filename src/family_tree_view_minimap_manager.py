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

from gramps.gui.utils import rgb_to_hex

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
                background-color: mix(@theme_fg_color, @theme_bg_color, 0.8);
            }
            #minimap-canvas {
                background-color: @theme_bg_color
            }
        """)

        self.minimap_width = 150
        self.minimap_height = 150
        self.minimap_padding = 5
        self.mouse_pressed = False

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
        self.minimap_canvas.connect("button-press-event", self.minimap_pressed)
        self.minimap_canvas.connect("button-release-event", self.minimap_released)
        self.minimap_canvas.connect("motion-notify-event", self.minimap_move)
        self.minimap_inner_container.add(self.minimap_canvas)
        self.minimap_outer_container.add(self.minimap_inner_container)

        self.init_minimap()

        self.minimap_view_rect = None
        self.minimap_view_rect_line_width = 2
        self.widget_manager.canvas_manager.canvas_container.connect("size-allocate", self.set_view_rect)
        self.widget_manager.canvas_manager.hadjustment.connect("value-changed", self.set_view_rect)
        self.widget_manager.canvas_manager.vadjustment.connect("value-changed", self.set_view_rect)

    def reset_minimap(self):
        # Remove children of root item (instead of creating a new root
        # item) to keep signal connections when resetting.
        root_item = self.minimap_canvas.get_root_item()
        for i in range(root_item.get_n_children()-1, -1, -1):
            root_item.remove_child(i)
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

        fg_color_found, fg_color = self.minimap_outer_container.get_style_context().lookup_color('theme_fg_color')
        if fg_color_found:
            fg_color = tuple(fg_color)[:3]
        else:
            fg_color = (0, 0, 0)

        self.minimap_view_rect = GooCanvas.CanvasRect(
            parent=self.minimap_canvas.get_root_item(),
            x=hadj/scale + canvas_bounds[0],
            y=vadj/scale + canvas_bounds[1],
            height=canvas_allocation.height/scale,
            width=canvas_allocation.width/scale,
            fill_color_gdk_rgba=Gdk.RGBA(*fg_color, 0.15),
            stroke_color=rgb_to_hex(fg_color),
            line_width=self.minimap_view_rect_line_width
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

        self.minimap_view_rect_line_width = 2/scale
        self.minimap_view_rect.props.line_width = self.minimap_view_rect_line_width

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
        self.minimap_canvas.show_all()

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
        self.minimap_canvas.show_all()

    def minimap_button_clicked(self, *_):
        if self.minimap_inner_container.get_visible():
            self.minimap_inner_container.set_visible(False)
            arrow_type = Gtk.ArrowType.UP
        else:
            self.minimap_inner_container.set_visible(True)
            arrow_type = Gtk.ArrowType.DOWN
        self.arrow.set(arrow_type=arrow_type, shadow_type=Gtk.ShadowType.NONE)

    def minimap_pressed(self, _widget, event):
        self.mouse_pressed = True
        self.move_minimap(event.x, event.y)

    def move_minimap(self, mouse_x, mouse_y):
        canvas_bounds = self.canvas_manager.canvas.get_bounds()
        minimap_bounds = self.minimap_canvas.get_bounds()
        minimap_scale = self.minimap_canvas.get_scale()
        canvas_scale = self.canvas_manager.get_scale()
        canvas_allocation = self.canvas_manager.canvas_container.get_allocation()

        hadj = (mouse_x/minimap_scale) + minimap_bounds.left - canvas_bounds.left
        vadj = (mouse_y/minimap_scale) + minimap_bounds.top - canvas_bounds.top

        hadj *= canvas_scale
        vadj *= canvas_scale

        # Move to center
        hadj -= canvas_allocation.width/2
        vadj -= canvas_allocation.height/2

        self.canvas_manager.hadjustment.set_value(hadj)
        self.canvas_manager.vadjustment.set_value(vadj)

    def minimap_released(self, *_):
        self.mouse_pressed = False

    def minimap_move(self, _widget, event):
        if self.mouse_pressed:
            self.move_minimap(event.x, event.y)
