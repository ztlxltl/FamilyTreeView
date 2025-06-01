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


from family_tree_view_gramplet import FamilyTreeViewGramplet
from family_tree_view_utils import get_gettext


_ = get_gettext()

class FamilyTreeViewPanelGramplet(FamilyTreeViewGramplet):
    def init(self):
        self.build_widget()

        self.fallback()

        # Don't call self.try_to_get_ftv() here as self.uistate.viewmanager.active_page isn't correct yet.
        self.ftv = None

        self.gui.get_container_widget().show_all()

    def try_to_get_ftv(self):
        super().try_to_get_ftv()
        if self.ftv is not None and self.uistate.viewmanager.active_page.__class__.__name__ == "FamilyTreeView":
            self.panel_manager = self.ftv.widget_manager.panel_manager
            container = self.gui.get_container_widget()

            container.remove(self.main_scrolled)
            self.ftv.widget_manager.use_external_panel(container)
            if self.panel_manager.displayed_object is None:
                active_person_handle = self.ftv.get_active()
                if len(active_person_handle) > 0:
                    self.panel_manager.open_person_panel(active_person_handle, 0, 0)
                else:
                    self.show_replacement_text(_(
                        "Select a person and open their panel to see details here."
                    ))

            # unrealized is emitted when a Gramplet is removed, destroy is not emitted.
            container.connect("unrealize", lambda *args: self.ftv.widget_manager.use_internal_panel())
        else:
            self.panel_manager = None

    def main(self):
        if self.uistate.viewmanager.active_page.__class__.__name__ != "FamilyTreeView":
            self.show_replacement_text(_(
                "Panel of FamilyTreeView is only available next to FamilyTreeView."
            ))
            return

        if self.ftv is None:
            self.try_to_get_ftv()
            if self.ftv is None:
                self.show_replacement_text(_(
                    "Can't display panel without FamilyTreeView loaded."
                ))
                return

        # Nothing else to do here.
        # Panel is created and managed by self.panel_manager.

        self.gui.get_container_widget().show_all()
