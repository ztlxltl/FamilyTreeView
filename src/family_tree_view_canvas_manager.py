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


from math import atan, cos, pi, sin, sqrt
from typing import TYPE_CHECKING

from gi.repository import Gtk, GdkPixbuf, Pango

from gramps.gui.utils import get_contrast_color, rgb_to_hex

from family_tree_view_canvas_manager_base import FamilyTreeViewCanvasManagerBase
from family_tree_view_utils import import_GooCanvas, make_hashable
if TYPE_CHECKING:
    from family_tree_view_widget_manager import FamilyTreeViewWidgetManager


GooCanvas = import_GooCanvas()

class FamilyTreeViewCanvasManager(FamilyTreeViewCanvasManagerBase):
    def __init__(self, widget_manager: "FamilyTreeViewWidgetManager", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget_manager = widget_manager
        self.ftv = self.widget_manager.ftv

        self.canvas.props.has_tooltip = True

        self.scale_factor_min = 1/100
        self.canvas_padding = 100_000

        # inside boxes
        self.padding = 10
        self.border_width = 2
        self.border_width_hover = 4

        self.max_name_line_count = 2

        self.expander_sep = 5 # distance between expander and nearby boxes/expanders 

        # horizontal seps
        self.spouse_sep = 10 # horizontal space between spouses
        self.grandparent_families_sep = 80 # horizontal space between the parental and maternal ancestors of active person

        # vertical seps
        self.above_family_sep = 10 # vertical space between family box and spouses above it

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
        self.expander_size = 20

        # badges
        self.badge_sep = 5
        self.badge_padding = 5
        self.badge_radius = 10
        self.badge_content_sep = 2

        # connections
        self.connection_radius = 10
        self.connection_sep = 10

        # combinations
        self.bottom_family_offset = self.above_family_sep + self.family_height # vertical offset between bottom of family and bottom of spouses above it
        self.expander_space_needed = self.expander_sep + self.expander_size + self.expander_sep
        self.below_family_sep = self.expander_space_needed + 2*self.connection_radius + self.expander_space_needed + self.badge_radius
        self.generation_sep = self.bottom_family_offset + self.below_family_sep # vertical space between persons from consecutive generations (generation < 3)
        self.generation_offset = self.generation_sep + self.person_height
        sep_for_two_expanders = 2*self.expander_space_needed # with double self.expander_sep in the middle
        self.child_subtree_sep = sep_for_two_expanders
        self.sibling_sep = sep_for_two_expanders
        self.other_families_sep = sep_for_two_expanders # horizontal space between families with sharing a spouse
        self.ancestor_sep = sep_for_two_expanders
        self.other_parent_families_sep = sep_for_two_expanders

        # defaults
        self.default_scale = 1
        self.default_y = -self.person_height/2
        self.reset_transform()

        self.reset_canvas()
        self.reset_abbrev_names()
        self.svg_pixbuf_cache = {}

        self.ftv.uistate.connect("nameformat-changed", self.reset_abbrev_names)
        self.ftv.connect("abbrev-rules-changed", self.reset_abbrev_names)

    def reset_canvas(self):
        super().reset_canvas()
        # Connections are added to a group created as first canvas element so connections are below everything else.
        self.connection_group = GooCanvas.CanvasGroup(parent=self.canvas.get_root_item())
        self.canvas_bounds = [0, 0, 0, 0] # left, top, right, bottom
        self.ppi = self.ftv._config.get("experimental.familytreeview-canvas-font-size-ppi")

    def reset_abbrev_names(self):
        self.fitting_abbrev_names = {}

    def add_person(self, x, generation, name, abbr_names, birth_date, death_date, primary_color, secondary_color, image_spec, alive, round_lower_corners, click_callback=None, badges=None):

        # group
        group = GooCanvas.CanvasGroup(parent=self.canvas.get_root_item())
        group.connect("button-press-event", self.click_callback, click_callback)
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

        if x == 0 and generation == 0 and self.ftv._config.get("appearance.familytreeview-highlight-root-person"):
            # This is the root person.
            line_width = 4
        else:
            line_width = 2

        box = GooCanvas.CanvasPath(
            parent=parent,
            data=data,
            fill_color=primary_color,
            stroke_color=secondary_color,
            line_width=line_width,
        )

        contrast_color = rgb_to_hex(get_contrast_color(tuple(box.props.fill_color_gdk_rgba)[:3]))

        font_desc = self.canvas_container.get_style_context().get_font(Gtk.StateFlags.NORMAL)

        # image
        img_max_width = self.person_width - 2*self.padding
        img_max_height = 80
        if image_spec is None:
            pass # no image
        elif image_spec[0] == "text":
            GooCanvas.CanvasText(
                parent=parent,
                x=x,
                y=y-self.person_height+self.padding+img_max_height/2,
                text=image_spec[1],
                alignment=Pango.Alignment.CENTER,
                anchor=GooCanvas.CanvasAnchorType.CENTER,
                width=self.person_width-2*self.padding,
                font_desc=font_desc,
                fill_color=contrast_color,
                # TODO somehow make ellipsize work for multiline (most likely has to kick in after using abbreviated names)
            )
        else:
            image_filter = self.ftv._config.get("appearance.familytreeview-person-image-filter")
            if image_spec[0] == "svg_data_callback":
                img_max_width_ = img_max_width - self.padding*2
                img_max_height_ = img_max_height - self.padding
                extra_padding = self.padding
            else:
                img_max_width_ = img_max_width
                img_max_height_ = img_max_height
                extra_padding = 0
            self.add_from_image_spec(
                parent,
                image_spec,
                x-img_max_width_/2,
                y-self.person_height+self.padding+extra_padding,
                img_max_width_, img_max_height_,
                grayscale=(image_filter == 1 and not alive) or image_filter == 2,
                color=secondary_color,
            )

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
            text=abbr_names[0],
            use_markup=True,
            alignment=Pango.Alignment.CENTER,
            anchor=GooCanvas.CanvasAnchorType.NORTH,
            width=self.person_width-2*self.padding,
            height=max_name_height,
            font_desc=font_desc,
            fill_color=contrast_color,
            # TODO somehow make ellipsize work for multiline (most likely has to kick in after using abbreviated names)
        )

        if name is not None:
            hashable_name = make_hashable(name.serialize())
            if hashable_name in self.fitting_abbrev_names:
                name_label.text_data.text = self.fitting_abbrev_names[hashable_name]
            else:
                size_pt = font_desc.get_size() / Pango.SCALE
                ppi = self.ppi # TODO assumption: 96
                size_px = size_pt * ppi/72
                line_height_px = size_px * 1.2 # TODO how to compute this ? (current value seems to work)
                for abbr_name in abbr_names[1:]: # skip full name used above
                    ink_extend_rect, logical_extend_rect = name_label.get_natural_extents()
                    Pango.extents_to_pixels(logical_extend_rect)
                    # NOTE: logical_extend_rect is independent of the canvas scale
                    if logical_extend_rect.height > 2*line_height_px:
                        name_label.text_data.text = abbr_name
                    else:
                        break
                self.fitting_abbrev_names[hashable_name] = name_label.text_data.text

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
            fill_color=contrast_color,
            # ellipsization required for long dates (e.g. non-regular, non-default calendar)
            ellipsize=Pango.EllipsizeMode.END
        )

        if not alive and self.ftv._config.get("appearance.familytreeview-show-deceased-ribbon"):
            s = 25
            r = 4
            svg_data = f"M {s-r*sqrt(2)} 0 h {r*sqrt(2)} l {-s} {s} v {-r*sqrt(2)} z"
            GooCanvas.CanvasPath(
                parent=parent,
                data=svg_data,
                fill_color=secondary_color,
                line_width=0,
                x=x-self.person_width/2,
                y=y-self.person_height,
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
        group.connect("button-press-event", self.click_callback, click_callback)
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
        box = GooCanvas.CanvasPath(
            parent=parent,
            data=data,
            fill_color=primary_color,
            stroke_color=secondary_color
        )

        contrast_color = rgb_to_hex(get_contrast_color(tuple(box.props.fill_color_gdk_rgba)[:3]))

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
            fill_color=contrast_color,
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

    def add_connection(self, x1, y1, x2, y2, ym=None, m=None, dashed=False, click_callback=None):
        if ym is None:
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

        fg_color_found, fg_color = self.canvas.get_style_context().lookup_color('theme_fg_color')
        if fg_color_found:
            fg_color = rgb_to_hex(tuple(fg_color)[:3])
        else:
            fg_color = "black"

        if dashed:
            line_dash = GooCanvas.CanvasLineDash.newv([10, 5])
        else:
            line_dash = None

        GooCanvas.CanvasPath(
            parent=self.connection_group,
            data=data,
            stroke_color=fg_color,
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
        path.connect("button-press-event", self.click_callback, click_callback, ym)

    def add_badges(self, badges, x, y):
        # add badges right-aligned and right to left starting from (x, y), vertically centered

        font_desc = self.canvas_container.get_style_context().get_font(Gtk.StateFlags.NORMAL)

        x += self.badge_sep # will be subtracted in loop
        for badge_info in reversed(badges): # since they are added from right to left
            x -= self.badge_sep
            x_ = x
            group = GooCanvas.CanvasGroup(parent=self.canvas.get_root_item())
            if "click_callback" in badge_info:
                # We can't tell if the pointer moves away from the badge while the mouse button is held down.
                # item and target of button-release-event are the same whether the mouse stays on the badge or not.
                # Calling the callback on releasing the button when the mouse moved away would be counterintuitive.
                # Therefore, the callback is called on button-press-event.
                def cb_badge(item, target, event):
                    # This conditional is workaround since multiple users reported a KeyError.
                    # TODO Find the actual root cause of the KeyError.
                    if "click_callback" in badge_info:
                        badge_info["click_callback"]()
                        return True # Don't propagate further.
                    return False # Propagate as if there was no callback.
                group.connect("button-press-event", self.click_callback, cb_badge)
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
                tooltip = badge_content_info.get("tooltip", badge_info.get("tooltip"))
                if badge_content_info["content_type"] == "text":
                    badge_content_text = GooCanvas.CanvasText(
                        parent=group,
                        x=x,
                        y=y,
                        text=badge_content_info["text"],
                        fill_color=badge_content_info.get("text_color", "#000"),
                        alignment=Pango.Alignment.RIGHT,
                        anchor=GooCanvas.CanvasAnchorType.EAST,
                        font_desc=font_desc,
                        tooltip=tooltip,
                    )
                    ink_extend_rect, logical_extend_rect = badge_content_text.get_natural_extents()
                    Pango.extents_to_pixels(logical_extend_rect)
                    x = x - logical_extend_rect.width
                elif badge_content_info["content_type"][:5] == "icon_":
                    icon_size = 10
                    if badge_content_info["content_type"] == "icon_file_svg":
                        self.add_from_image_spec(
                            group, ("svg_path", badge_content_info["file"]),
                            x-icon_size,
                            y-icon_size/2,
                            icon_size,
                            icon_size,
                            color=badge_content_info.get("current_color", "black"),
                            tooltip=tooltip,
                        )
                    elif badge_content_info["content_type"] == "icon_svg_data_callback":
                        svg_data = badge_content_info["callback"](icon_size, icon_size)
                        fill_color = badge_content_info.get("fill_color", "#000")
                        stroke_color = badge_content_info.get("line_width", None)
                        line_width = badge_content_info.get("line_width", 0)
                        GooCanvas.CanvasPath(
                            parent=group,
                            data=svg_data,
                            fill_color=fill_color,
                            stroke_color=stroke_color,
                            line_width=line_width,
                            tooltip=tooltip,
                            x=x-icon_size,
                            y=y-icon_size/2,
                        )
                    x = x - icon_size

            # TODO remove badge and break if too little space.

            x -= self.badge_padding
            w = x_ - x
            if w < 2*self.badge_radius:
                # circular corners
                badge_rect.props.radius_x = w/2
                badge_rect.props.radius_y = w/2
            badge_rect.props.x = x
            badge_rect.props.width = w

    def add_expander(self, x, y, ang, click_callback):
        group = GooCanvas.CanvasGroup(parent=self.canvas.get_root_item())
        group.connect("button-press-event", self.click_callback, click_callback)
        parent = group

        fg_color_found, fg_color = self.canvas.get_style_context().lookup_color('theme_fg_color')
        if fg_color_found:
            fg_color = tuple(fg_color)[:3]
        else:
            fg_color = (0, 0, 0)

        bg_color_found, bg_color = self.canvas.get_style_context().lookup_color('theme_bg_color')
        if bg_color_found:
            bg_color = tuple(bg_color)[:3]
        else:
            bg_color = (1, 1, 1)

        background_color = rgb_to_hex(tuple(fgc*0.2+bgc*0.8 for fgc, bgc in zip(fg_color, bg_color)))

        GooCanvas.CanvasEllipse(
            parent=parent,
            center_x=x,
            center_y=y,
            radius_x=self.expander_size/2,
            radius_y=self.expander_size/2,
            fill_color=background_color,
            stroke_color=None,
        )

        # Use path instead of pixbuf with icon as icon is pixelated.
        # (tried Gtk.IconLookupFlags.FORCE_SVG, doesn't work)
        l = 5
        data = f"""
            M {x-l/2} {y-l}
            L {x+l/2} {y}
            L {x-l/2} {y+l}
        """
        GooCanvas.CanvasPath(
            parent=parent,
            data=data,
            stroke_color=rgb_to_hex(fg_color),
        ).rotate(ang, x, y)

    def add_from_image_spec(self, parent, image_spec, x, y, max_width, max_height, color=None, grayscale=False, tooltip=None):
        if image_spec[0] in ["path", "svg_path", "pixbuf"]:
            if image_spec[0] == "path":
                path = image_spec[1]
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            elif image_spec[0] == "svg_path":
                svg_factor = 16 # if 1: too pixelated, if too large: slow
                path = image_spec[1]
                if color is None:
                    # When viewBox is specified, the scaling will
                    # increase resolution. If its not specified, the svg
                    # is scaled down.
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, max_width*svg_factor, max_height*svg_factor)
                else:
                    with open(path, 'r') as file:
                        svg_code = file.read()

                    # Insert the color to use for currentcolor.
                    # TODO Is this robust enough?
                    index = svg_code.lower().find("svg")
                    # 3 to insert after "svg"
                    svg_code = svg_code[:index+3] + f""" style="color: {color}" """ + svg_code[index+3:]

                    # Rendering SVGs at high resolution takes time.
                    # Caching the result speeds up building large trees.
                    if svg_code in self.svg_pixbuf_cache:
                        pixbuf = self.svg_pixbuf_cache[svg_code]
                    else:
                        pixbuf_loader = GdkPixbuf.PixbufLoader()
                        pixbuf_loader.set_size(
                            max_width*svg_factor,
                            max_height*svg_factor
                        )
                        pixbuf_loader.write(svg_code.encode())
                        pixbuf_loader.close()
                        pixbuf = pixbuf_loader.get_pixbuf()
                        self.svg_pixbuf_cache[svg_code] = pixbuf
            else:
                pixbuf = image_spec[1]
            if grayscale:
                pixbuf.saturate_and_pixelate(pixbuf, 0, False)
            img = GooCanvas.CanvasImage(
                parent=parent,
                x=x,
                y=y,
                pixbuf=pixbuf,
                tooltip=tooltip,
            )
            # Setting image size with arguments doesn't work.
            scale = min(
                max_height/pixbuf.get_height(),
                max_width/pixbuf.get_width()
            )
            img.props.width=pixbuf.get_width()*scale
            img.props.height=pixbuf.get_height()*scale
            # Otherwise, the image is cropped instead of scaled:
            img.props.scale_to_fit=True

            # center image
            # needs to be done after setting size
            img.props.x += (max_width-img.props.width)/2
            img.props.y += (max_height-img.props.height)/2
        elif image_spec[0] == "svg_data_callback":
            svg_data, width, height = image_spec[1](
                max_width,
                max_height,
            )
            # Setting width and height (as a kwarg or the property),
            # causes distortion (the order of defining/setting those
            # matters). This happens when using absolute coordinates
            # (lowercase letters) as well as when using relative
            # coordinates (uppercase letters) in the path data.
            GooCanvas.CanvasPath(
                parent=parent,
                data=svg_data,
                fill_color=color,
                line_width=0,
                x=x+(max_width-width)/2,
                y=y+(max_height-height)/2,
                tooltip=tooltip,
            )

    def click_callback(self, root_item, target, event, other_callback=None, *other_args, **other_kwargs):
        if self.widget_manager.search_widget is not None:
            self.widget_manager.search_widget.hide_search_popover()
        if target is None:
            # background click
            return self.widget_manager.info_box_manager.close_info_box()
        if other_callback is not None:
            return other_callback(root_item, target, event, *other_args, **other_kwargs)
        return False

    def adjust_bounds(self, left, top, right, bottom):
        self.canvas_bounds[0] = min(self.canvas_bounds[0], left-self.canvas_padding)
        self.canvas_bounds[1] = min(self.canvas_bounds[1], top-self.canvas_padding)
        self.canvas_bounds[2] = max(self.canvas_bounds[2], right+self.canvas_padding)
        self.canvas_bounds[3] = max(self.canvas_bounds[3], bottom+self.canvas_padding)

        self.canvas.set_bounds(*self.canvas_bounds)
