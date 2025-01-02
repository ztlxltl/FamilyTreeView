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


register(GRAMPLET,
    id = "abbreviated_name_display_inspector_gramplet",
    name = _("AbbreviatedNameDisplay Inspector Gramplet"),
    description = _("A Gramplet to inspect the names of the active person, abbreviated by AbbreviationNameDisplay."),
    version = '0.1.26',
    gramps_target_version = "5.2",
    status = STABLE,
    fname = "abbreviated_name_display_inspector_gramplet.py",
    authors = ["ztlxltl"],
    authors_email = ["ztlxltl@gmx.net"],
    gramplet = "AbbreviatedNameDisplayInspectorGramplet",
    gramplet_title = "Abbreviated Names",
    navtypes=["Person"],
    audience=DEVELOPER
)
