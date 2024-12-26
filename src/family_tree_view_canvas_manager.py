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


from math import atan, cos, pi, sin
from typing import TYPE_CHECKING

from gi.repository import Gtk, GdkPixbuf, Pango

from family_tree_view_canvas_manager_base import FamilyTreeViewCanvasManagerBase
from family_tree_view_icons import get_svg_data
from family_tree_view_utils import import_GooCanvas
if TYPE_CHECKING:
    from family_tree_view_widget_manager import FamilyTreeViewWidgetManager


GooCanvas = import_GooCanvas()

class FamilyTreeViewCanvasManager(FamilyTreeViewCanvasManagerBase):
    def __init__(self, widget_manager: "FamilyTreeViewWidgetManager", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget_manager = widget_manager
        self.ftv = self.widget_manager.ftv

        self.canvas.props.has_tooltip = True

        # inside boxes
        self.padding = 10
        self.border_width = 2
        self.border_width_hover = 4

        self.max_name_line_count = 2

        self.toggler_sep = 8

        # horizontal seps
        self.spouse_sep = 10 # horizontal space between spouses
        self.child_sep = 50 # horizontal space between children
        self.grandparent_families_sep = 80 # horizontal space between the parental and maternal ancestors of active person
        self.ancestor_sep = 50 # horizontal space between the ancestor families

        # vertical seps
        self.above_family_sep = 10 # vertical space between family box and spouses above it
        self.line_sep = 10

        # box sizes
        self.corner_radius = 10
        self.person_width = 130 # width of person boxes
        self.person_height = 185 # height of person boxes
        self.family_width = 2 * self.person_width + self.spouse_sep # width of family boxes
        self.family_height = 25 # height of family boxes
        self.image_width = 80
        self.image_height = 80
        self.highlight_spread_radius = 20
        self.person_info_box_width = 3 * self.person_width
        self.person_info_box_height = 1.0 * self.person_height
        self.family_info_box_width = 1.5 * self.family_width
        self.family_info_box_height = 0.75 * self.person_info_box_height
        self.toggler_size = 20

        # connections
        self.connection_radius = 10
        self.connection_sep = 10

        # combinations
        self.bottom_family_offset = self.above_family_sep + self.family_height # vertical offset between bottom of family and bottom of spouses above it
        self.toggler_space_needed = self.toggler_sep + self.toggler_size + self.toggler_sep
        self.below_family_sep = self.toggler_space_needed + 2*self.connection_radius + self.toggler_space_needed
        self.generation_sep = self.bottom_family_offset + self.below_family_sep # vertical space between persons from consecutive generations (generation < 3)
        self.generation_offset = self.generation_sep + self.person_height
        self.child_subtree_sep = 3*self.toggler_sep + 2*self.toggler_size + 5
        self.sibling_sep = 3*self.toggler_sep + 2*self.toggler_size + 5
        self.multiple_families_sep = self.sibling_sep # horizontal space between families with sharing a spouse
        self.multiple_parent_families_sep = self.sibling_sep

        # badges
        self.badge_sep = 5
        self.badge_padding = 5
        self.badge_radius = 10
        self.badge_content_sep = 2

        # defaults
        self.default_scale = 1
        self.default_y = -self.person_height/2
        self.reset_transform()

        self.click_callback = self.click_handler

        self.reset_canvas()

    def reset_canvas(self):
        super().reset_canvas()
        # Connections are added to a group created as first canvas element so connections are below everything else.
        self.connection_group = GooCanvas.CanvasGroup(parent=self.canvas.get_root_item())
        self.canvas_bounds = [0, 0, 0, 0] # left, top, right, bottom

    def add_person(self, x, generation, name, abbr_names, birth_date, death_date, primary_color, secondary_color, image_spec, alive, round_lower_corners, click_callback=None, badges=None):

        # group
        group = GooCanvas.CanvasGroup(parent=self.canvas.get_root_item())
        if click_callback is not None:
            group.connect("button-press-event", click_callback)
        parent = group

        # box
        y = self.widget_manager.tree_builder.get_y_of_generation(generation) # bottom center

        r = self.corner_radius
        if round_lower_corners:
            data = f"""
                M {x - self.person_width/2+r},{y}
                a {r} {r} 90 0 1 {-r} {-r}
                v {-self.person_height + 2*r}
                a {r} {r} 90 0 1 {r} {-r}
                h {self.person_width - 2*r}
                a {r} {r} 90 0 1 {r} {r}
                v {self.person_height - 2*r}
                a {r} {r} 90 0 1 {-r} {r}
                z
            """
        else:
            data = f"""
                M {x - self.person_width/2},{y}
                v {-self.person_height + r}
                a {r} {r} 90 0 1 {r} {-r}
                h {self.person_width - 2*r}
                a {r} {r} 90 0 1 {r} {r}
                v {self.person_height - r}
                z
            """

        GooCanvas.CanvasPath(
            parent=parent,
            data=data,
            fill_color=primary_color,
            stroke_color=secondary_color
        )

        font_desc = self.canvas_container.get_style_context().get_font(Gtk.StateFlags.NORMAL)

        # image
        img_max_width = self.person_width - 2*self.padding
        img_max_height = 80
        if image_spec is None:
            pass # no image
        elif image_spec[0] == "path":
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(image_spec[1], img_max_width, img_max_height)
            image_filter = self.ftv._config.get("appearance.familytreeview-person-image-filter")
            if (image_filter == 1 and not alive) or image_filter == 2:
                # grayscale
                pixbuf.saturate_and_pixelate(pixbuf, 0, False)
            img = GooCanvas.CanvasImage(
                parent=parent,
                x=x-img_max_width/2,
                y=y-self.person_height+self.padding,
                width=img_max_width,
                height=img_max_height,
                pixbuf=pixbuf
            )
            # center image
            img.props.x += (img_max_width-img.props.width)/2
            img.props.y += (img_max_height-img.props.height)/2
        elif image_spec[0] == "svg_default":
            img_max_width_red = img_max_width - self.padding*2
            img_max_height_red = img_max_height - self.padding
            svg_ds = get_svg_data(
                image_spec[1],
                x-img_max_width_red/2,
                y-self.person_height+self.padding+self.padding, # extra padding
                img_max_width_red,
                img_max_height_red,
                centered=True
            )
            for svg_d in svg_ds:
                GooCanvas.CanvasPath(
                    parent=parent,
                    data=svg_d,
                    fill_color=secondary_color,
                    line_width=0
                )
        elif image_spec[0] == "text":
            image_text_label = GooCanvas.CanvasText(
                parent=parent,
                x=x,
                y=y-self.person_height+self.padding+img_max_height/2,
                text=image_spec[1],
                alignment=Pango.Alignment.CENTER,
                anchor=GooCanvas.CanvasAnchorType.CENTER,
                width=self.person_width-2*self.padding,
                font_desc=font_desc
                # TODO somehow make ellipsize work for multiline (most likely has to kick in after using abbreviated names)
            )
            image_text_label

        sep_below_image = 5 # between image and name
        sep_below_name = 5 # between name and dates

        max_text_height = self.person_height - 2*self.padding - img_max_height - sep_below_image
        num_lines_dates = 2
        num_max_name_text = 2
        max_name_height = (max_text_height - sep_below_name) / (num_lines_dates+num_max_name_text) * num_max_name_text

        # name
        name_label = GooCanvas.CanvasText(
            parent=parent,
            x=x,
            y=y-self.person_height+self.padding+img_max_height+sep_below_image,
            text=name,
            alignment=Pango.Alignment.CENTER,
            anchor=GooCanvas.CanvasAnchorType.NORTH,
            width=self.person_width-2*self.padding,
            height=max_name_height,
            font_desc=font_desc
            # TODO somehow make ellipsize work for multiline (most likely has to kick in after using abbreviated names)
        )

        size_pt = font_desc.get_size() / Pango.SCALE
        dpi = 96 # TODO assumption
        size_px = size_pt * dpi/72
        line_height_px = size_px * 1.2 # TODO how to compute this ? (current value seems to work)
        for abbr_name in abbr_names:
            ink_extend_rect, logical_extend_rect = name_label.get_natural_extents()
            Pango.extents_to_pixels(logical_extend_rect)
            # NOTE: logical_extend_rect is independent of the canvas scale
            if logical_extend_rect.height > 2*line_height_px:
                name_label.text_data.text = abbr_name
            else:
                break

        # dates
        if birth_date == "":
            # Line hight doesn't change when zooming,
            # if the line of birth date is empty.
            birth_date = " "
        GooCanvas.CanvasText(
            parent=parent,
            x=x,
            y=y-self.person_height+self.padding+img_max_height+sep_below_image+max_name_height+sep_below_name,
            text=f"{birth_date}\n{death_date}",
            alignment=Pango.Alignment.CENTER,
            anchor=GooCanvas.CanvasAnchorType.NORTH,
            width=self.person_width-2*self.padding,
            height=max_name_height,
            font_desc=font_desc,
            # ellipsization required for long dates (e.g. non-regular, non-default calendar)
            ellipsize=Pango.EllipsizeMode.END
        )

        if not alive and self.ftv._config.get("appearance.familytreeview-show-deceased-ribbon"):
            svg_ds = get_svg_data("deceased_ribbon", x-self.person_width/2, y-self.person_height, 25, 25)
            for svg_d in svg_ds:
                GooCanvas.CanvasPath(
                    parent=parent,
                    data=svg_d,
                    fill_color=secondary_color,
                    line_width=0
                )

        if badges is not None:
            self.add_badges(badges, x+self.person_width/2-self.padding, y-self.person_height)

        self.adjust_bounds(x-self.person_width/2, y-self.person_height, x+self.person_width/2, y)

        return {
            # optical center x/y
            "oc_x": x,
            "oc_y": y - self.person_height/2,
            # box top/bottom
            "bx_t": y - self.person_height,
            "bx_b": y
        }

    def add_family(self, x, generation, marriage_date, primary_color, secondary_color, click_callback=None, badges=None):

        # group
        group = GooCanvas.CanvasGroup(parent=self.canvas.get_root_item())
        if click_callback is not None:
            group.connect("button-press-event", click_callback)
        parent = group

        # box
        y = self.widget_manager.tree_builder.get_y_of_generation(generation) + self.above_family_sep # top center
        r = self.corner_radius
        data = f"""
            M {x - self.family_width/2},{y}
            h {self.family_width}
            v {self.family_height - r}
            a {r} {r} 90 0 1 {-r} {r}
            h {-self.family_width + 2*r}
            a {r} {r} 90 0 1 {-r} {-r}
            z
        """
        GooCanvas.CanvasPath(
            parent=parent,
            data=data,
            fill_color=primary_color,
            stroke_color=secondary_color
        )

        # date
        font_desc = self.canvas_container.get_style_context().get_font(Gtk.StateFlags.NORMAL)
        GooCanvas.CanvasText(
            parent=parent,
            x=x,
            y=y+self.padding/2,
            text=marriage_date,
            alignment=Pango.Alignment.CENTER,
            anchor=GooCanvas.CanvasAnchorType.NORTH,
            width=self.family_width-2*self.padding,
            height=self.family_height+2*self.padding,
            font_desc=font_desc,
            ellipsize=Pango.EllipsizeMode.END
        )

        if badges is not None:
            self.add_badges(badges, x+self.family_width/2-self.padding, y)

        self.adjust_bounds(x-self.family_width/2, y, x+self.family_width/2, y+self.family_height)

        return {
            # optical center x/y
            "oc_x": x,
            "oc_y": y + self.family_height - (self.family_height + self.above_family_sep + self.person_height)/2, # center of family and spouses
            # box top/bottom
            "bx_t": y,
            "bx_b": y + self.family_height,
            "x": x
        }

    def add_connection(self, x1, y1, x2, y2, m=None, dashed=False, click_callback=None):
        ym = (y1 + y2) / 2 # middle
        if x1 == x2:
            data = f"""
                M {x1} {y1}
                L {x2} {y2}
            """
        else:
            if m is not None:
                # m[0] which line, 0-based, counted from top to bottom
                # m[1] how many lines
                if m[1] > 1:
                    ym1 = ym - self.connection_sep * (m[1]-1)/2 # top
                    ym2 = ym + self.connection_sep * (m[1]-1)/2 # bottom
                    ym = ym1 + (ym2 - ym1) * m[0]/(m[1]-1) # horizontal part
            if (x1 < x2) != (y1 < y2): # xor
                sweepFlag1 = "1"
                sweepFlag2 = "0"
            else:
                sweepFlag1 = "0"
                sweepFlag2 = "1"
            if y1 < y2:
                yDirSign = -1
            else:
                yDirSign = 1
            if x1 < x2:
                xDirSign = 1
            else:
                xDirSign = -1

            r = self.connection_radius
            if abs(x1 - x2) < 2*r:
                # The line between the two arcs is not horizontal.
                Dx = abs(x1 - x2)/r
                # angle of the line (Dx=2 -> alpha=0, Dx=0° -> alpha=90°)
                alpha = pi/2 + 2*atan(Dx/(Dx-4))
                data = f"""
                    M {x1} {y1}
                    V {ym + yDirSign*r}
                    A {r} {r} 0 0 {sweepFlag1} {x1 + xDirSign*r*(1-sin(alpha))} {ym + yDirSign*r*(1-cos(alpha))}
                    L {x2 - xDirSign*r*(1-sin(alpha))} {ym - yDirSign*r*(1-cos(alpha))}
                    A {r} {r} 0 0 {sweepFlag2} {x2} {ym - yDirSign*r}
                    V {y2}
                """
            else:
                data = f"""
                    M {x1} {y1}
                    V {ym + yDirSign*r}
                    A {r} {r} 0 0 {sweepFlag1} {x1 + xDirSign*r} {ym}
                    H {x2 - xDirSign*r}
                    A {r} {r} 0 0 {sweepFlag2} {x2} {ym - yDirSign*r}
                    V {y2}
                """
        if dashed:
            line_dash = GooCanvas.CanvasLineDash.newv([10, 5])
        else:
            line_dash = None
        GooCanvas.CanvasPath(
            parent=self.connection_group,
            data=data,
            line_width=2,
            line_dash=line_dash
        )
        # add additional (invisible) path for larger clickable area
        path = GooCanvas.CanvasPath(
            parent=self.connection_group,
            data=data,
            line_width=5,
            stroke_color=None
        )
        if click_callback:
            path.connect("button-press-event", click_callback, ym)

    def add_badges(self, badges, x, y):
        # add badges right-aligned and right to left starting from (x, y), vertically centered

        font_desc = self.canvas_container.get_style_context().get_font(Gtk.StateFlags.NORMAL)

        x += self.badge_sep # will be subtracted in loop
        for badge_info in reversed(badges): # since they are added from right to left
            x -= self.badge_sep
            x_ = x
            group = GooCanvas.CanvasGroup(parent=self.canvas.get_root_item())
            if "click_callback" in badge_info:
                group.connect(
                    "button-press-event",
                    lambda *_: badge_info.get(
                        "click_callback",
                        # This is workaround since multiple users reported a KeyError.
                        # TODO Find the actual root cause of the KeyError.
                        lambda *_: None
                    )()
                )
            badge_rect = GooCanvas.CanvasRect(
                parent=group,
                x=x-20, # initial x, will be set below
                y=y-self.padding, # half height
                height=2*self.padding,
                width=20, # initial width, will be set below
                radius_x=self.badge_radius,
                radius_y=self.badge_radius,
                fill_color=badge_info["background_color"],
                stroke_color=badge_info.get("stroke_color", "#000"),
                tooltip=badge_info.get("tooltip"),
            )

            x -= self.badge_padding
            x += self.badge_content_sep # padding will be subtracted in loop
            for badge_content_info in reversed(badge_info["content"]): # start with last as badges are right aligned
                x -= self.badge_content_sep
                if badge_content_info["content_type"] == "icon_svg_inline":
                    icon_size = 10
                    svg_data = get_svg_data(badge_content_info["svg_inline"], x-icon_size, y-icon_size/2, icon_size, icon_size)
                    for svg_d in svg_data:
                        badge_content_text = GooCanvas.CanvasPath(
                            parent=group,
                            data=svg_d,
                            fill_color="#000",
                            line_width=0,
                            tooltip=badge_content_info.get("tooltip", badge_info.get("tooltip")),
                        )
                    x = x - icon_size
                elif badge_content_info["content_type"] == "text":
                    badge_content_text = GooCanvas.CanvasText(
                        parent=group,
                        x=x,
                        y=y,
                        text=badge_content_info["text"],
                        fill_color=badge_content_info.get("text_color", "#000"),
                        alignment=Pango.Alignment.RIGHT,
                        anchor=GooCanvas.CanvasAnchorType.EAST,
                        font_desc=font_desc,
                        tooltip=badge_content_info.get("tooltip", badge_info.get("tooltip")),
                    )
                    ink_extend_rect, logical_extend_rect = badge_content_text.get_natural_extents()
                    Pango.extents_to_pixels(logical_extend_rect)
                    x = x - logical_extend_rect.width

            # TODO remove badge and break if too little space.

            x -= self.badge_padding
            w = x_ - x
            if w < 2*self.badge_radius:
                # circular corners
                badge_rect.props.radius_x = w/2
                badge_rect.props.radius_y = w/2
            badge_rect.props.x = x
            badge_rect.props.width = w

    def click_handler(self, root_item, target, event):
        if target is None:
            # background click
            return self.widget_manager.info_box_manager.close_info_box()
        return False

    def adjust_bounds(self, left, top, right, bottom):
        padding = 10_000
        self.canvas_bounds[0] = min(self.canvas_bounds[0], left-padding)
        self.canvas_bounds[1] = min(self.canvas_bounds[1], top-padding)
        self.canvas_bounds[2] = max(self.canvas_bounds[2], right+padding)
        self.canvas_bounds[3] = max(self.canvas_bounds[3], bottom+padding)

        self.canvas.set_bounds(*self.canvas_bounds)
