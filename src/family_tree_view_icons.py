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


from math import sqrt


def get_svg_data(inline_svg_name, x, y, max_width, max_height, centered=False):
    # TODO All icons should be svg files, but for some reason they cannot be positioned in canvas in this case.

    if inline_svg_name == "avatar_simple":
        width = 10
        height = 10
        x, y, f = apply_scale(x, y, max_width, max_height, centered, width, height)
        svg_path_data = [
            f"M {2.5*f+x} { 2.5*f+y} a {2.5*f} {2.5*f} 0 0 1 {5*f} { 0*f} a {2.5*f} {2.5*f} 0 0 1 {-5*f} {0*f}"
            f"M {0  *f+x} {10  *f+y} a {5  *f} {5  *f} 0 0 1 {10*f} {0*f}"
        ]
    elif inline_svg_name == "descendants_simple":
        width = 10
        height = 10
        x, y, f = apply_scale(x, y, max_width, max_height, centered, width, height)
        svg_path_data = [
            f"M {3*f+x} {2*f+y} a {2*f} {2*f} 0 0 1 {4*f} {0*f} a {2*f} {2*f} 0 0 1 {-4*f} {0*f}"
            f"M {6*f+x} {8*f+y} a {2*f} {2*f} 0 0 1 {4*f} {0*f} a {2*f} {2*f} 0 0 1 {-4*f} {0*f}"
            f"M {0*f+x} {8*f+y} a {2*f} {2*f} 0 0 1 {4*f} {0*f} a {2*f} {2*f} 0 0 1 {-4*f} {0*f}"
            f"M {4.5*f+x} {3.5*f+y} h {1*f} v {1*f} h {3*f} v {2*f} h {-1*f} v {-1*f} h {-5*f} v {1*f} h {-1*f} v {-2*f} h {3*f} z"
        ]
    elif inline_svg_name == "deceased_ribbon":
        s = 25
        r = 4
        x, y, f = apply_scale(x, y, max_width, max_height, centered, s, s)
        svg_path_data = [
            f"M {(s-r*sqrt(2))*f+x} {0*f+y} h {r*sqrt(2)*f} l {-s*f} {s*f} v {-r*sqrt(2)*f} z"
        ]
    else:
        raise ValueError(f"Unknown inline SVG name '{inline_svg_name}'.")
    return svg_path_data

def apply_scale(x, y, max_width, max_height, centered, width, height):
    f = min(max_width/width, max_height/height)
    if centered:
        x += (max_width-width*f)/2
        y += (max_height-height*f)/2
    return (x, y, f)
