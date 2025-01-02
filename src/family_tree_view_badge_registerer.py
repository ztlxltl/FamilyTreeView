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


from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from family_tree_view_badge_manager import FamilyTreeViewBadgeManager


class FamilyTreeViewBadgeRegisterer(metaclass=ABCMeta):
    """
    Hierarchy:
    - Multiple badge factories can be registered.
    - Each badge registerer registers one or more badge groups.
      Each group has an id, a name and can be (de)activated as a whole.
    - Each badge group consists of multiple badges.
      In most cases each badge group should consist of only one badge.
    - Each badge contains one or more content elements.
    """
    def __init__(self, dbstate, uistate, badge_manager: "FamilyTreeViewBadgeManager"):
        self.dbstate = dbstate
        self.uistate = uistate
        self.badge_manager = badge_manager
        self.ftv = self.badge_manager.ftv

    @abstractmethod
    def register_badges(self):
        """This method needs to call
        self.badge_manager.register_badges_callbacks() or
        self.badge_manager.register_person_badges_callback() or
        self.badge_manager.register_family_badges_callback()
        The registered callbacks are called for each person / family.
        They need to return a list of dicts, for each badge one dict.
        See family_tree_view_example_badges for examples.
        """
        pass
