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

from abbreviated_name_display import AbbreviatedNameDisplay
from family_tree_view_gramplet import FamilyTreeViewGramplet
from family_tree_view_utils import get_gettext


_ = get_gettext()

class AbbreviatedNameDisplayInspectorGramplet(FamilyTreeViewGramplet):

    def init(self):
        self.try_to_get_ftv()

        self.build_widget()

        self.uistate.connect("nameformat-changed", self.update)
        self.fallback()
        self.gui.get_container_widget().show_all()

    def try_to_get_ftv(self):
        super().try_to_get_ftv()
        if self.ftv is None:
            self.abbrev_name_display = None
        else:
            self.abbrev_name_display = AbbreviatedNameDisplay(self.ftv)
            self.ftv.connect("abbrev-rules-changed", self.update)

    def db_changed(self):
        self.connect(self.dbstate.db, "person-update", self.update)

    def active_changed(self, handle):
        self.update()

    def main(self):
        if self.ftv is None:
            self.try_to_get_ftv()
            if self.ftv is None:
                self.show_replacement_text(_(
                    "Abbreviated names are not available. "
                    "Open FamilyTreeView once to load it and make abbreviated names available."
                    "You may need to change the active person to reload this Gramplet."
                ))
                return
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

    def add_name(self, title, name, first=False):
        num = self.abbrev_name_display.get_num_for_name_abbrev(name)
        name_label = Gtk.Label()
        name_label.set_markup(f"<b>{title}</b>")
        name_label.set_halign(Gtk.Align.START)
        if not first:
            name_label.set_margin_top(30)
        self.main_box.add(name_label)

        format_str = self.abbrev_name_display._get_format_str(name, num=num)
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
        name_parts_label = Gtk.Label(self.get_name_parts(name, num=num))
        name_parts_label.set_halign(Gtk.Align.START)
        name_parts_scrolled.add(name_parts_label)
        name_parts_expander.add(name_parts_scrolled)
        self.main_box.add(name_parts_expander)

        abbr_name_list, step_descriptions = self.abbrev_name_display.get_abbreviated_names(name, num=num, return_step_description=True)

        name_list_store = Gtk.ListStore(str, str)
        for name, step_info in zip(abbr_name_list, step_descriptions):
            name_list_store.append([
                name,
                step_info[9] + "\n" + (
                    ""
                    if step_info[0] is None else
                    f"  (rule {step_info[0]}, rule step {step_info[1]}, name part {step_info[2]}: {repr(step_info[7])}, name sub-part {step_info[3]}: {repr(step_info[8])}, "
                    f"space-separated part {step_info[4]+1}, hyphen-separated part {step_info[5]+1}, uppercase-separated part {step_info[6]+1})"
                )
            ])

        name_list_view = Gtk.TreeView(model=name_list_store)
        name_list_view.set_hexpand(True)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Abbreviated Name", renderer, markup=0)
        column.set_resizable(True)
        name_list_view.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Abbreviation Step", renderer, text=1)
        column.set_resizable(True)
        name_list_view.append_column(column)

        name_list_scrolled = Gtk.ScrolledWindow()
        name_list_scrolled.set_hexpand(True)
        name_list_scrolled.set_policy(
            Gtk.PolicyType.AUTOMATIC, # horizontal
            Gtk.PolicyType.NEVER # vertical
        )
        name_list_scrolled.add(name_list_view)
        self.main_box.add(name_list_scrolled)

    def get_name_parts(self, name, num=None):
        name_parts = self.abbrev_name_display._get_name_parts(name, num=num)

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
