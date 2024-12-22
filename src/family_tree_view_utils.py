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


from gi import require_version
from gi.repository import Pango


def import_GooCanvas():
    # GooCanvas is used since it allows zooming and is already available in Gramps AIO for Windows.

    gooCanvas_available = False
    for gooCanvas_version in ("3.0", "2.0"):
        try:
            require_version("GooCanvas", gooCanvas_version)
            from gi.repository import GooCanvas
            gooCanvas_available = True
            break
        except (ImportError, ValueError):
            pass
    if not gooCanvas_available:
        raise Exception("GooCanvas 2 or 3 (http://live.gnome.org/GooCanvas) is required for this view to work.")
    return GooCanvas

def get_contrast_color(color):
    """
    Choose contrast text color (white or black) for provided background.

    This function is similar to the one in gramps.gui.utils, but with Gtk.RGBA input and string output.
    """
    yiq = color.red*299 + color.green*587 + color.blue*114
    if yiq < 500:
        return "white"
    return "black"

def get_label_line_height(label):
    label_layout = label.get_layout()
    line = label_layout.get_line(0)
    ink_extend_rect, logical_extend_rect = line.get_extents()
    Pango.extents_to_pixels(logical_extend_rect)
    return logical_extend_rect.height

def get_start_stop_ymd(event, calendar):
    start_ymd = event.date.to_calendar(calendar).get_ymd()
    if start_ymd == (0, 0, 0):
        # no start date given -> no date specified at all
        start_ymd = None
    stop_ymd = event.date.to_calendar(calendar).get_stop_ymd()
    if stop_ymd == (0, 0, 0):
        # no stop date given -> no compound date -> no range or span
        stop_ymd = start_ymd
    return (start_ymd, stop_ymd)

def calculate_min_max_age_at_event(birth_event, event, calendar):
    birth_start_ymd, birth_stop_ymd = get_start_stop_ymd(birth_event, calendar)
    event_start_ymd, event_stop_ymd = get_start_stop_ymd(event, calendar)
    if birth_start_ymd is None or event_start_ymd is None:
        return None

    birth_start_ymd = list(birth_start_ymd)
    birth_stop_ymd = list(birth_stop_ymd)
    if birth_start_ymd[0] == 0:
        return None
    # round stop up and start down
    if birth_stop_ymd[0] == 0:
        birth_stop_ymd = birth_start_ymd
    if birth_start_ymd[1] == 0:
        birth_start_ymd[1] = 1
    if birth_stop_ymd[1] == 0:
        birth_stop_ymd[1] = 12
    if birth_start_ymd[2] == 0:
        birth_start_ymd[2] = 1
    if birth_stop_ymd[2] == 0:
        leap_year = (birth_start_ymd[0] % 400 == 0 or (birth_start_ymd[0] % 4 == 0 and birth_start_ymd[0] % 100 != 0))
        if leap_year:
            days_feb = 29
        else:
            days_feb = 28
        # index 0 for unknown month
        birth_stop_ymd[2] = [None, 31, days_feb, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][birth_stop_ymd[1]]

    if event_stop_ymd[0] == 0:
        event_stop_ymd = event_start_ymd

    def age_at_event(birth_ymd, event_ymd):
        age = event_ymd[0] - birth_ymd[0]
        if birth_ymd[1] > event_ymd[1]:
            # didn't reached birth month
            age -= 1
        elif (birth_ymd[1] == event_ymd[1]) and (birth_ymd[2] > event_ymd[2]):
            # didn't reached birth day in birth month
            age -= 1
        return age

    min_age = age_at_event(birth_stop_ymd, event_start_ymd)
    max_age = age_at_event(birth_start_ymd, event_stop_ymd)
    return (min_age, max_age)
