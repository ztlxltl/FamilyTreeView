#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2025-      Julien Lepiller <julien@lepiller.eu>
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


from gi.repository import Gtk

from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.display.name import displayer as name_displayer
from gramps.gui.widgets.menuitem import add_menuitem

_ = GRAMPS_LOCALE.translation.gettext

class FamilyTreeViewMenu(Gtk.Menu):
    def __init__(self, handle, ftv: "FamilyTreeView", typ):
        super().__init__()
        self.set_reserve_toggle_size(False)
        self.ftv = ftv
        self.handle = handle
        self.typ = typ

        if typ == 1: # person
            add_menuitem(self, _("Edit"), self.handle, lambda obj: self.ftv.edit_person(obj.get_data()))
            person = self.ftv.dbstate.db.get_person_from_handle(handle)
            other = []
            for associated in person.get_person_ref_list():
                other.append(associated.get_reference_handle())
            if other != []:
                # build associated submenu
                item = Gtk.MenuItem(label=_("Set associated person as active"))
                submenu = Gtk.Menu()
                submenu.set_reserve_toggle_size(False)
                item.set_submenu(submenu)
                item.show()
                self.append(item)

                for associated in other:
                    person = self.ftv.dbstate.db.get_person_from_handle(associated)
                    name = person.get_primary_name()
                    add_menuitem(submenu, name_displayer.display_name(name), associated, lambda obj: self.ftv.set_active_person(obj.get_data()))
        elif typ == 2: # family
            add_menuitem(self, _("Edit"), self.handle, lambda obj: self.ftv.edit_family(obj.get_data()))

    def popup(self, event):
        if event:
            super().popup(None, None, None, None, event.get_button()[1], event.time)
