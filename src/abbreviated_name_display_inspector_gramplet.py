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


from gi.repository import Gtk

from gramps.gen.display.name import displayer as name_displayer, _F_FMT
from gramps.gen.plug import Gramplet

from abbreviated_name_display import AbbreviatedNameDisplay


class AbbreviatedNameDisplayInspectorGramplet(Gramplet):

    def init(self):
        self.abbrev_name_display = AbbreviatedNameDisplay()

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

        self.uistate.connect("nameformat-changed", self.update)
        self.fallback()
        self.gui.get_container_widget().show_all()

    def db_changed(self):
        self.connect(self.dbstate.db, "person-update", self.update)

    def active_changed(self, handle):
        self.update()

    def main(self):
        active_person = self.get_active_object("Person")
        if active_person:
            self.clear_main_widget()

            name = active_person.get_primary_name()
            self.add_name("Primary name", name, first=True)

            for i, name in enumerate(active_person.get_alternate_names()):
                self.add_name(f"Alternative name {i+1}", name)
        else:
            self.fallback()
        self.gui.get_container_widget().show_all()

    def get_format_str(self, name):
        num = name.display_as
        if num == 0:
            num = name_displayer.get_default_format()
        format_str = name_displayer.name_formats[num][_F_FMT]
        return name,format_str

    def add_name(self, title, name, first=False):
        name_label = Gtk.Label()
        name_label.set_markup(f"<b>{title}</b>")
        name_label.set_halign(Gtk.Align.START)
        if not first:
            name_label.set_margin_top(30)
        self.main_box.add(name_label)

        format_str = self.abbrev_name_display._get_format_str(name)
        format_label = Gtk.Label("Format:\n" + format_str)
        format_label.set_halign(Gtk.Align.START)
        self.main_box.add(format_label)

        name_parts_expander = Gtk.Expander(label="Name parts")
        name_parts_expander.set_expanded(False)
        name_parts_scrolled = Gtk.ScrolledWindow()
        name_parts_scrolled.set_hexpand(True)
        name_parts_scrolled.set_policy(
            Gtk.PolicyType.AUTOMATIC, # horizontal
            Gtk.PolicyType.NEVER # vertical
        )
        name_parts_label = Gtk.Label(self.get_name_parts(name))
        name_parts_label.set_halign(Gtk.Align.START)
        name_parts_scrolled.add(name_parts_label)
        name_parts_expander.add(name_parts_scrolled)
        self.main_box.add(name_parts_expander)

        abbr_name_list, step_descriptions = self.abbrev_name_display.get_abbreviated_names(name, return_step_description=True)

        name_list_store = Gtk.ListStore(str, str)
        for name, step in zip(abbr_name_list,step_descriptions):
            name_list_store.append([
                name,
                step,
                # "" # empty column
            ])

        name_list_view = Gtk.TreeView(model=name_list_store)
        name_list_view.set_hexpand(True)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Abbreviated Name", renderer, text=0)
        column.set_resizable(True)
        name_list_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Abbreviation Step", renderer, text=1)
        column.set_resizable(True)
        name_list_view.append_column(column)

        # renderer = Gtk.CellRendererText()
        # column = Gtk.TreeViewColumn("", renderer, text=2)
        # name_list_view.append_column(column)

        name_list_scrolled = Gtk.ScrolledWindow()
        name_list_scrolled.set_hexpand(True)
        name_list_scrolled.set_policy(
            Gtk.PolicyType.AUTOMATIC, # horizontal
            Gtk.PolicyType.NEVER # vertical
        )
        name_list_scrolled.add(name_list_view)
        self.main_box.add(name_list_scrolled)

    def get_name_parts(self, name):
        name_parts = self.abbrev_name_display._get_name_parts(name)

        # remove extra info of given name
        for part in name_parts:
            if isinstance(part, str):
                continue
            for i in range(len(part[2])-1, -1, -1):
                if isinstance(part[2][i], tuple) and len(part[2][i]) == 4:
                    part[2][i] = part[2][i][:2]
        
        s = "[\n"
        for part in name_parts:
            s += f"  {repr(part)}\n"
        s += "]"

        return s

    def fallback(self):
        self.clear_main_widget()
        label = Gtk.Label("Noting to show.\nMaybe no database is loaded.")
        self.main_box.add(label)

    def clear_main_widget(self):
        for child in self.main_box.get_children():
            self.main_box.remove(child)
