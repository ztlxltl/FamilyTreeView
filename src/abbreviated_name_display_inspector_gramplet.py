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


from gramps.gen.plug import Gramplet

from abbreviated_name_display import AbbreviatedNameDisplay


class AbbreviatedNameDisplayInspectorGramplet(Gramplet):

    def init(self):
        self.abbrev_name_display = AbbreviatedNameDisplay()
        self.uistate.connect("nameformat-changed", self.update)
        self.fallback()

    def db_changed(self):
        self.connect(self.dbstate.db, "person-update", self.update)

    def active_changed(self, handle):
        self.update()

    def main(self):
        active_person = self.get_active_object("Person")
        if active_person:
            text = "Primary name:\n"
            abbr_name_list = self.abbrev_name_display.get_abbreviated_names(active_person.get_primary_name())
            text += "\n".join(abbr_name_list)
            for i, name in enumerate(active_person.get_alternate_names()):
                text += f"\n\nAlternative name {i+1}:\n"
                abbr_name_list = self.abbrev_name_display.get_abbreviated_names(name)
                text += "\n".join(abbr_name_list)
            self.gui.set_text(text)
        else:
            self.fallback()

    def fallback(self):
        self.gui.set_text("Noting to show.\nMaybe no database is loaded.")
