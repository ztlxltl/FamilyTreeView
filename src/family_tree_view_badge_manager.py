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


import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from family_tree_view import FamilyTreeView


class FamilyTreeViewBadgeManager:
    def __init__(self, ftv: "FamilyTreeView"):
        self.ftv = ftv
        self.reset_badges()

    def reset_badges(self):
        self.badges = []
        self.badge_click_callbacks = {}

    def register_badges_callbacks(self, badge_id, badge_name, person_badge_callback, family_badge_callback):
        assert badge_id not in [b[0] for b in self.badges]
        self.badges.append((badge_id, badge_name, person_badge_callback, family_badge_callback))

    def register_person_badges_callback(self, badge_id, badge_name, person_badge_callback):
        self.register_badges_callbacks(badge_id, badge_name, person_badge_callback, None)

    def register_family_badges_callback(self, badge_id, badge_name, family_badge_callback):
        self.register_badges_callbacks(badge_id, badge_name, None, family_badge_callback)

    def get_person_badges(self, person_handle):
        return self._get_badges("person", person_handle)

    def get_family_badges(self, family_handle):
        return self._get_badges("family", family_handle)


    BADGE_CONTENT_TYPES = [
        "text",
        "icon_svg_inline",
        "icon_svg_default",
    ]

    BADGE_KEYS = [
        "background_color",
        "stroke_color",
        "content",
        "click_callback",
        "priority", # TODO
        "tooltip",
    ]

    CONTENT_ELEMENT_KEYS = [
        "content_type",
        "tooltip",
    ]

    def _get_badges(self, key, *callback_args):
        # callback_args currently is one arg: person or family handle

        config_badge_active = self.ftv._config.get("badges.familytreeview-badges-active")
        if key == "person":
            i = 2
        elif key == "family":
            i = 3
        else:
            raise ValueError(f"key has to be 'person' or 'family' but it's '{key}'")

        badge_callbacks = []
        for badge in self.badges:
            if badge[0] in config_badge_active: # default to active
                if not config_badge_active[badge[0]][key]:
                    continue
            if badge[i] is None:
                continue
            badge_callbacks.append(badge[i])

        badges = []
        for callback in badge_callbacks:
            try:
                callback_badges = callback(self.ftv.dbstate, self.ftv.uistate, *callback_args)
            except TypeError as e:
                # TODO drop support for this in a future update
                if len(traceback.extract_tb(e.__traceback__)) == 1:
                    # Wrong signature for callback.
                    callback_badges = callback(*callback_args)
                else:
                    raise
            for badge_info in callback_badges:
                self._validate_badge_info(badge_info)
                badges.append(badge_info)
        return badges

    def _validate_badge_info(self, badge_info):
        # required keys:
        assert "background_color" in badge_info
        assert "content" in badge_info
        # assert all keys are known (incl. optional)
        assert all(key in self.BADGE_KEYS for key in badge_info)
        for content_element_info in badge_info["content"]:
            assert "content_type" in content_element_info
            assert content_element_info["content_type"] in self.BADGE_CONTENT_TYPES
            if content_element_info["content_type"] == "text":
                content_element_type_keys = [
                    "text",
                    "text_color"
                ]
            elif content_element_info["content_type"] == "icon_svg_inline":
                content_element_type_keys = [
                    "svg_inline",
                    "icon_fill_color"
                ]
            elif content_element_info["content_type"] == "icon_svg_default":
                content_element_type_keys = [
                    "svg_default",
                    "icon_fill_color"
                ]
            # TODO image / pixel graphic
            assert all(key in self.CONTENT_ELEMENT_KEYS+content_element_type_keys for key in content_element_info) # all keys are known
        if "click_callback" in content_element_info:
            assert callable(content_element_info["click_callback"])
