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
from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.lib.childreftype import ChildRefType
from gramps.gen.simple import make_basic_stylesheet
from gramps.gui.plug.quick._textbufdoc import TextBufDoc

import children_quick_report
from family_tree_view_badge_registerer import FamilyTreeViewBadgeRegisterer


_ = GRAMPS_LOCALE.translation.gettext

class NumCitationsBadgeRegisterer(FamilyTreeViewBadgeRegisterer):
    def register_badges(self):
        if self.badge_manager is not None:
            self.badge_manager.register_badges_callbacks(
                "num_citations", "Number of citations",
                self.cb_create_person_badges, self.cb_create_family_badges
            )

    def cb_create_person_badges(self, person_handle):
        person = self.dbstate.db.get_person_from_handle(person_handle)
        citation_list = person.get_citation_list()
        return self._cb_create_badges(citation_list)

    def cb_create_family_badges(self, family_handle):
        family = self.dbstate.db.get_family_from_handle(family_handle)
        citation_list = family.get_citation_list()
        return self._cb_create_badges(citation_list)

    def _cb_create_badges(self, citation_list):
        num_citations = len(citation_list)
        if num_citations == 0:
            color = "DarkRed"
            text_color = "White"
        elif num_citations < 3:
            color = "LimeGreen"
            text_color = "Black"
        else:
            color = "DarkGreen"
            text_color = "White"
        return [
            {
                "background_color": color,
                "tooltip": _("Number of citations: ") + str(num_citations),
                "content": [
                    {
                        "content_type": "text",
                        "text": str(num_citations),
                        "text_color": text_color
                    }
                ]
            }
        ]


class NumEventsWithoutCitationsBadgeRegisterer(FamilyTreeViewBadgeRegisterer):
    def register_badges(self):
        if self.badge_manager is not None:
            self.badge_manager.register_badges_callbacks(
                "num_events_without_citations", "Number of events without citations",
                self.cb_create_person_badges, self.cb_create_family_badges
            )

    def cb_create_person_badges(self, person_handle):
        person = self.dbstate.db.get_person_from_handle(person_handle)
        event_ref_list = person.get_event_ref_list()
        return self._cb_create_badges(event_ref_list)

    def cb_create_family_badges(self, family_handle):
        family = self.dbstate.db.get_family_from_handle(family_handle)
        event_ref_list = family.get_event_ref_list()
        return self._cb_create_badges(event_ref_list)

    def _cb_create_badges(self, event_ref_list):
        event_handle_list = [r.ref for r in event_ref_list]
        events_without_citations = 0
        for event_handle in event_handle_list:
            event = self.dbstate.db.get_event_from_handle(event_handle)
            if len(event.get_citation_list()) == 0:
                events_without_citations += 1
        if events_without_citations == 0:
            return []
        return [
            {
                "background_color": "Red",
                "tooltip": _("Number of events without citations: ") + str(events_without_citations),
                "content": [
                    {
                        "content_type": "text",
                        "text": str(events_without_citations),
                    }
                ]
            }
        ]


class NumChildrenBadgeRegisterer(FamilyTreeViewBadgeRegisterer):
    def register_badges(self):
        if self.badge_manager is not None:
            self.badge_manager.register_badges_callbacks(
                "num_children", "Number of children",
                self.cb_create_person_badges, self.cb_create_family_badges
            )

    def cb_create_person_badges(self, person_handle):
        def cb_open_children_quick_report():
            person = self.dbstate.db.get_person_from_handle(person_handle)
            document = TextBufDoc(make_basic_stylesheet(), None)
            document.dbstate = self.dbstate
            document.uistate = self.uistate
            document.open("")
            children_quick_report.run(self.dbstate.db, document, person)

        num_children = 0
        num_birth_children = 0
        person = self.dbstate.db.get_person_from_handle(person_handle)
        family_handles = person.get_family_handle_list()
        for family_handle in family_handles:
            family = self.dbstate.db.get_family_from_handle(family_handle)
            child_refs = family.get_child_ref_list()
            for ref in child_refs:
                num_children += 1
                if (
                    person_handle == family.get_father_handle() and ref.get_father_relation() == ChildRefType.BIRTH
                    or person_handle == family.get_mother_handle() and ref.get_mother_relation() == ChildRefType.BIRTH
                ):
                    num_birth_children += 1

        if num_children == 0:
            # no badge(s)
            return []

        content = [
            {
                "content_type": "icon_svg_inline",
                "svg_inline": "descendants_simple",
                "icon_fill_color": "SaddleBrown"
            },
            {
                "content_type": "text",
                "tooltip": _("Number of children with birth relationship: ") + str(num_birth_children),
                "text": str(num_birth_children),
            }
        ]
        if num_children > num_birth_children:
            content.append({
                "content_type": "text",
                "tooltip": _("Number of all children: ") + str(num_children),
                "text": "(" + str(num_children) + ")",
                "text_color": "SaddleBrown"
            })
        return [
            {
                "background_color": "BurlyWood",
                "tooltip": _("Number of children"),
                "content": content,
                "click_callback": cb_open_children_quick_report,
                "priority": 1
            }
        ]

    def cb_create_family_badges(self, family_handle):
        family = self.dbstate.db.get_family_from_handle(family_handle)
        num_children = len(family.get_child_ref_list())

        if num_children == 0:
            # no badge
            return []

        return [
            {
                "background_color": "BurlyWood",
                "tooltip": _("Number of all children: ") + str(num_children),
                "content": [
                    {
                        "content_type": "text",
                        "text": str(num_children),
                        "text_color": "SaddleBrown"
                    }
                ]
            }
        ]


class NumOtherFamiliesBadgeRegisterer(FamilyTreeViewBadgeRegisterer):
    def register_badges(self):
        if self.badge_manager is not None:
            self.badge_manager.register_person_badges_callback(
                "num_other_families", "Number of other families",
                self.cb_create_person_badges
            )

    def cb_create_person_badges(self, person_handle):
        num_other_families = 0
        person = self.dbstate.db.get_person_from_handle(person_handle)
        family_handles = person.get_family_handle_list()
        num_other_families = len(family_handles) - 1

        if num_other_families < 1:
            # no badge(s)
            return []
        
        scheme = config.get("colors.scheme")
        background_color = config.get("colors.family")[scheme]
        stroke_color = config.get("colors.border-family")[scheme]

        return [
            {
                "background_color": background_color,
                "stroke_color": stroke_color,
                "tooltip": _("Number of other families: ") + str(num_other_families),
                "content": [
                    {
                        "content_type": "text",
                        "text": "+" + str(num_other_families),
                    }
                ],
                "priority": 1
            }
        ]


def load_on_reg(dbstate, uistate, addon):
    return (dbstate, uistate, addon)

def register_badges(args):
    dbstate, uistate, addon = args
    NumCitationsBadgeRegisterer(dbstate, uistate).register_badges()
    NumEventsWithoutCitationsBadgeRegisterer(dbstate, uistate).register_badges()
    NumChildrenBadgeRegisterer(dbstate, uistate).register_badges()
    NumOtherFamiliesBadgeRegisterer(dbstate, uistate).register_badges()
