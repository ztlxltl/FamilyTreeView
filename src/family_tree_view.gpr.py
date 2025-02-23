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


from gramps.gen.config import config


if locals().get('uistate'): # don't start GUI if in CLI mode, just ignore
    from gi.repository import Gtk
    import os
    from gramps.gen.const import USER_PLUGINS
    fname = os.path.join(USER_PLUGINS, 'FamilyTreeView', 'src', 'icons')
    icons = Gtk.IconTheme().get_default()
    icons.append_search_path(fname)

if not config.has_default("interface.familytreeview-order-start"):
    config.register("interface.familytreeview-order-start", False)
    config.save()
order_start = config.get("interface.familytreeview-order-start")

if order_start:
    order = START
else:
    order = END

register(VIEW,
    id = "family_tree_view",
    name = _("FamilyTreeView"),
    description = _("A navigable family tree."),
    category = ("Ancestry", _("Charts")),
    version = '0.1.82',
    gramps_target_version = "5.2",
    status = BETA,
    fname = "family_tree_view.py",
    authors = ["ztlxltl"],
    authors_email = ["ztlxltl@gmx.net"],
    requires_gi = [
        ("GooCanvas", "2.0,3.0"),
    ],
    viewclass = "FamilyTreeView",
    stock_icon = "gramps-family-tree-view",
    order = order,
)
