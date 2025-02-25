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


register(GENERAL,
    id = "family_tree_view_example_badges",
    name = _("FamilyTreeView Example Badges"),
    description = _("Example badges for FamilyTreeView."),
    category = "family_tree_view_badge_addon",
    version = '0.1.85',
    gramps_target_version = "5.2",
    status = BETA,
    fname = "family_tree_view_example_badges.py",
    authors = ["ztlxltl"],
    authors_email = ["ztlxltl@gmx.net"],
    # depends_on = ["familytreeview"],
    load_on_reg = True,
)
