#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2025-      ztlxltl
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

from gi.repository import Gtk

from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.plug import Gramplet

if TYPE_CHECKING:
    from family_tree_view import FamilyTreeView


_ = GRAMPS_LOCALE.translation.gettext

class FamilyTreeViewGramplet(Gramplet):

    def build_widget(self):
        self.main_scrolled = Gtk.ScrolledWindow()
        self.main_scrolled.set_hexpand(True)
        self.main_scrolled.set_vexpand(True)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.main_box.set_hexpand(True)
        self.main_box.set_vexpand(True)
        self.main_box.set_spacing(5)
        self.main_scrolled.add(self.main_box)
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.main_scrolled)

    def try_to_get_ftv(self):
        try:
            self.ftv: "FamilyTreeView" = next(
                view for view in self.uistate.viewmanager.pages
                if view.__class__.__name__ == "FamilyTreeView"
            )
        except StopIteration:
            # FamilyTreeView not loaded yet.
            self.ftv = None

    def show_replacement_text(self, msg):
        self.clear_main_widget()
        label = Gtk.Label(msg)
        label.set_xalign(0)
        label.set_line_wrap(True)
        label.set_margin_top(10)
        label.set_margin_left(10)
        label.set_margin_right(10)
        self.main_box.add(label)
        self.gui.get_container_widget().show_all()

    def fallback(self):
        self.show_replacement_text(_(
            "Noting to show.\nMaybe no database is loaded."
        ))

    def clear_main_widget(self):
        for child in self.main_box.get_children():
            self.main_box.remove(child)
