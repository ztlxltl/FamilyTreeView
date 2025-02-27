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


def get_person_avatar_svg_data(max_width, max_height):
    # This is designed as 10 x 10.
    f = min(max_width/10, max_height/10)
    svg_data = (
        f"M {2.5*f} { 2.5*f} a {2.5*f} {2.5*f} 0 0 1 { 5*f} 0 a {2.5*f} {2.5*f} 0 0 1 {-5*f} 0"
        f"M  0      {10  *f} a {5  *f} {5  *f} 0 0 1 {10*f} 0"
    )
    return (svg_data, 10*f, 10*f)

def get_family_avatar_svg_data(max_width, max_height):
    # This is designed as 18 x 10.
    f = min(max_width/18, max_height/10)
    svg_data = (
        f"M { 2.5*f} {2.5*f} a {2.5*f} {2.5*f} 0 0 1 {5*f} 0 a {2.5*f} {2.5*f} 0 0 1 {-5*f} 0"
        f"M {10.5*f} {2.5*f} a {2.5*f} {2.5*f} 0 0 1 {5*f} 0 a {2.5*f} {2.5*f} 0 0 1 {-5*f} 0"
        f"M  0    {10*f} a {5*f} {5*f} 0 0 1 {10*f} 0"
        f"M {8*f} {10*f} a {5*f} {5*f} 0 0 1 {10*f} 0"
    )
    return (svg_data, 18*f, 10*f)
