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


from math import log2

from gi.repository import Gdk, Gtk

from family_tree_view_utils import import_GooCanvas


GooCanvas = import_GooCanvas()

class FamilyTreeViewCanvasManagerBase:
    def __init__(self, resize_reference=None):

        self.zoom_level_step = 0.1
        self.zoom_level_max = 4
        self.zoom_level_min = -6

        self.default_zoom_level = 0
        self.default_x = 0
        self.default_y = 0
        self.clicking_canvas = False
        self.dragging_canvas = False
        self.drag_canvas_last_x = 0
        self.drag_canvas_last_y = 0

        self.canvas_container = Gtk.ScrolledWindow()
        self.hadjustment = self.canvas_container.get_hadjustment()
        self.vadjustment = self.canvas_container.get_vadjustment()
        self.scroll_mode = "map"
        self.canvas_container_size_allocate_first_call = True
        if resize_reference is None:
            self.resize_reference = self.canvas_container
        else:
            self.resize_reference = resize_reference
        # If resize_reference is a parent widget which has a widget to the right,
        # resizing the widget to the right doesn't affect the callback and they appear more like an overlay.
        self.resize_reference.connect("size-allocate", self.canvas_container_size_allocate)

        self.canvas = GooCanvas.Canvas()
        self.canvas.connect("scroll-event", self.mouse_scroll)
        self.connect_root_item()
        self.set_zoom_level(self.default_zoom_level)
        self.canvas.set_bounds(-10000, -10000, 10000, 10000) # TODO

        self.canvas_container.add(self.canvas)

        self.ignore_this_mouse_button_press_ = False

    def reset_canvas(self):
        # Remove children of root item (instead of creating a new root
        # item) to keep signal connections when resetting.
        root_item = self.canvas.get_root_item()
        for i in range(root_item.get_n_children()-1, -1, -1):
            root_item.remove_child(i)

    def connect_root_item(self):
        self.canvas.get_root_item().connect("button-press-event", self.mouse_button_press)
        self.canvas.get_root_item().connect("button-release-event", self.mouse_button_release)
        self.canvas.get_root_item().connect("motion-notify-event", self.mouse_move)

    ################################
    # navigation: zoom
    ################################

    def canvas_container_size_allocate(self, canvas_container, allocation):
        if self.canvas_container_size_allocate_first_call:
            # move origin to center
            self.reset_transform()
            # only do this once
            self.canvas_container_size_allocate_first_call = False
        else:
            self.hadjustment.set_value(self.hadjustment.get_value() - (allocation.width - self.canvas_container_allocation.width)/2)
            self.vadjustment.set_value(self.vadjustment.get_value() - (allocation.height - self.canvas_container_allocation.height)/2)
        self.canvas_container_allocation = allocation

    def mouse_scroll(self, widget, event):
        """
        Zoom by mouse wheel.
        """
        if self.scroll_mode == "map":
            if event.direction == Gdk.ScrollDirection.UP:
                self.zoom_in()
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.zoom_out()
            return True # no propagation
        elif self.scroll_mode == "doc":
            if event.state & Gdk.ModifierType.SHIFT_MASK:
                old_value = self.hadjustment.get_value()
                # Same step as vertical scrolling:
                step = self.vadjustment.get_step_increment()
                if event.direction == Gdk.ScrollDirection.UP:
                    new_value = old_value - step
                elif event.direction == Gdk.ScrollDirection.DOWN:
                    new_value = old_value + step
                self.hadjustment.set_value(new_value)
                return True
            elif event.state & Gdk.ModifierType.CONTROL_MASK:
                if event.direction == Gdk.ScrollDirection.UP:
                    self.zoom_in()
                elif event.direction == Gdk.ScrollDirection.DOWN:
                    self.zoom_out()
                return True
            return False # Let ScrolledWindow do the scrolling.

    def zoom_in(self):
        """
        Increase zoom scale.
        """
        zoom_level = self.get_zoom_level() + self.zoom_level_step
        if zoom_level > self.zoom_level_max:
            zoom_level = self.zoom_level_max
        scale = 2**zoom_level
        scale_factor = self.get_scale() / scale
        self.zoom_at_pointer(scale_factor)

    def zoom_out(self):
        """
        Decrease zoom scale.
        """
        zoom_level = self.get_zoom_level() - self.zoom_level_step
        if zoom_level < self.zoom_level_min:
            zoom_level = self.zoom_level_min
        scale = 2**zoom_level
        scale_factor = self.get_scale() / scale
        self.zoom_at_pointer(scale_factor)

    def zoom_at_pointer(self, scale_factor):
        """
        Set value for zoom of the canvas widget and apply it.
        """

        scale = self.get_scale() / scale_factor

        pointer = self.canvas.get_pointer()
        canvas_allocation = self.canvas.get_allocation()
        adj = [self.hadjustment.get_value(), self.vadjustment.get_value()]

        adj[0] = adj[0] + (pointer.x - canvas_allocation.width/2) * (1 - scale_factor)
        adj[1] = adj[1] + (pointer.y - canvas_allocation.height/2) * (1 - scale_factor)

        self.hadjustment.set_value(adj[0])
        self.vadjustment.set_value(adj[1])

        self.set_scale(scale)

    def set_zoom_level(self, zoom_level):
        self.set_scale(2**zoom_level)

    def set_scale(self, scale):
        self.canvas.set_scale(scale)

    def get_zoom_level(self):
        return log2(self.get_scale())

    def get_scale(self):
        return self.canvas.get_scale()

    ################################
    # navigation: pan
    ################################

    def ignore_this_mouse_button_press(self):
        """
        Call this method if the currently processed mouse button press
        event is processed in another callback and doesn't needs to be
        processed here. This can help to prevent the canvas from
        sticking to the mouse when the other callback causes the mouse
        button release to not be caught. Only call if you are sure that
        mouse button press callback will be called as there is no
        timeout.
        """
        self.ignore_this_mouse_button_press_ = True

    def mouse_button_press(self, _, __, event):
        if self.ignore_this_mouse_button_press_:
            self.ignore_this_mouse_button_press_ = False
            return
        button = event.get_button()[1]
        if button == 1 or button == 2:
            self.drag_canvas_last_x = event.x_root
            self.drag_canvas_last_y = event.y_root
            self.clicking_canvas = True
        return False

    def mouse_button_release(self, root_item, target, event):
        if self.clicking_canvas:
            self.clicking_canvas = False
            self.dragging_canvas = False
            return True
        if self.dragging_canvas:
            self.mouse_move(root_item, target, event)
            self.canvas.get_parent().get_window().set_cursor(None)
            self.clicking_canvas = False
            self.dragging_canvas = False
            return True
        return False

    def mouse_move(self, _, __, event):
        # only move canvas if dragging it
        if self.clicking_canvas and event.type == Gdk.EventType.MOTION_NOTIFY:
            self.clicking_canvas = False
            self.dragging_canvas = True
            self.canvas.get_parent().get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.FLEUR))

        if self.dragging_canvas and event.type in [Gdk.EventType.MOTION_NOTIFY, Gdk.EventType.BUTTON_RELEASE]:
            self.move_by_pixels(
                event.x_root - self.drag_canvas_last_x,
                event.y_root - self.drag_canvas_last_y
            )
            return True
        return False

    def move_by_pixels(self, dx, dy):
        scale = self.canvas.get_scale()
        self.move_by_units(dx*scale, dy*scale)

    def move_by_units(self, dx, dy):
        h_adj = self.hadjustment.get_value()
        h_adj -= dx
        self.hadjustment.set_value(h_adj)

        v_adj = self.vadjustment.get_value()
        v_adj -= dy
        self.vadjustment.set_value(v_adj)

    def reset_transform(self):
        self.set_zoom_level(self.default_zoom_level)
        self.move_to_center()

    def move_to_center(self, x=None, y=None):
        if x is None or y is None:
            x = self.default_x
            y = self.default_y
        canvas_allocation = self.resize_reference.get_allocation()
        self.hadjustment.set_value((x - self.canvas.get_bounds()[0])*self.get_scale() - canvas_allocation.width/2)
        self.vadjustment.set_value((y - self.canvas.get_bounds()[1])*self.get_scale() - canvas_allocation.height/2)

    def get_center_in_units(self):
        canvas_allocation = self.resize_reference.get_allocation()
        x = (self.hadjustment.get_value() + canvas_allocation.width/2)/self.get_scale() + self.canvas.get_bounds()[0]
        y = (self.vadjustment.get_value() + canvas_allocation.height/2)/self.get_scale() + self.canvas.get_bounds()[1]
        return (x, y)
