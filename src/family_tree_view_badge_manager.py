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

from family_tree_view_utils import get_gettext, get_reloaded_custom_filter_list
if TYPE_CHECKING:
    from family_tree_view import FamilyTreeView


_ = get_gettext()

class FamilyTreeViewBadgeManager:
    def __init__(self, ftv: "FamilyTreeView"):
        self.ftv = ftv
        self.reset_badges()

        self.prepared_filter_badges_data = {}

    def reset_badges(self):
        self.badges = []
        self.badge_click_callbacks = {}

    def register_badges_callbacks(self, badge_id, badge_name, 
        person_badge_callback, family_badge_callback, 
        default_active_person=True, default_active_family=True
    ):
        assert badge_id not in [b[0] for b in self.badges]
        self.badges.append((badge_id, badge_name, 
            person_badge_callback, family_badge_callback,
            default_active_person, default_active_family
        ))

    def register_person_badges_callback(self, badge_id, badge_name, person_badge_callback, default_active_person=True):
        self.register_badges_callbacks(badge_id, badge_name, person_badge_callback, None, default_active_person, False)

    def register_family_badges_callback(self, badge_id, badge_name, family_badge_callback, default_active_family=True):
        self.register_badges_callbacks(badge_id, badge_name, None, family_badge_callback, False, default_active_family)

    def get_person_badges(self, person_handle):
        return self._get_badges("person", person_handle)

    def get_family_badges(self, family_handle):
        return self._get_badges("family", family_handle)

    def prepare_badges(self):
        """call this method before rebuilding the tree"""

        self.prepared_filter_badges_data = {}

        custom_filter_list = get_reloaded_custom_filter_list()

        for key, namespace in [("person", "Person"), ("family", "Family")]:
            if key == "person":
                self.prepared_filter_badges_data[key] = {"generic": {}, "custom": {}}
            else:
                self.prepared_filter_badges_data[key] = {"custom": {}}
            filters = custom_filter_list.get_filters(namespace)
            if key == "person":
                filter_dict = {None: self.ftv.generic_filter}
            else:
                filter_dict = {}
            filter_dict = {
                **filter_dict,
                **{filt.get_name(): filt for filt in filters}
            }

            badges_filter_match_config = self.ftv._config.get("badges.familytreeview-badges-filter-match")
            for filter_name, filt in filter_dict.items():
                prepared_filter_data = {"matches": []}
                if filter_name is None:
                    self.prepared_filter_badges_data[key]["generic"] = prepared_filter_data
                    if filt is None:
                        # no generic filter
                        continue
                    if not badges_filter_match_config[key]["generic"]["active"]:
                        continue
                else:
                    self.prepared_filter_badges_data[key]["custom"][filter_name] = prepared_filter_data
                    if (
                        filter_name not in badges_filter_match_config[key]["custom"]
                        or not badges_filter_match_config[key]["custom"][filter_name]["active"]
                    ):
                        continue

                # TODO Couldn't find a way to reliably detect if a
                # filter was changed since the last run of apply(). Run
                # it every time to make sure the current filter is used
                # in the tree.

                try:
                    prepared_filter_data["matches"] = filt.apply(
                        self.ftv.dbstate.db,
                        user=self.ftv.uistate.viewmanager.user
                    )
                except:
                    # TODO maybe show a popup or an error icon in the
                    # filter badge's row in the config dialog.
                    pass


    BADGE_CONTENT_TYPES = [
        "text",
        "icon_file_svg",
        "icon_svg_data_callback",
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
        handle = callback_args[0]

        config_badge_active = self.ftv._config.get("badges.familytreeview-badges-active")
        if key == "person":
            i = 2
        elif key == "family":
            i = 3
        else:
            raise ValueError(f"key has to be 'person' or 'family' but it's '{key}'")

        badge_callbacks = []
        for badge in self.badges:
            if badge[0] in config_badge_active:
                if not config_badge_active[badge[0]][key]:
                    continue # not active
            else:
                if not badge[i+2]: # default
                    continue # default: not active
            if badge[i] is None:
                continue # no callback
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

        badges_filter_match_config = self.ftv._config.get("badges.familytreeview-badges-filter-match")

        if key == "person":
            badge_data = self._add_filter_badge(
                _("Sidebar filter"),
                badges_filter_match_config[key]["generic"],
                self.prepared_filter_badges_data[key]["generic"]["matches"],
                handle
            )
            if badge_data is not None:
                badges.append(badge_data)

        for filter_name, filter_badge_data in badges_filter_match_config[key]["custom"].items():
            if filter_name not in self.prepared_filter_badges_data[key]["custom"]:
                continue
            badge_data = self._add_filter_badge(
                filter_name,
                filter_badge_data,
                self.prepared_filter_badges_data[key]["custom"][filter_name]["matches"],
                handle
            )
            if badge_data is not None:
                badges.append(badge_data)

        return badges

    def _add_filter_badge(self, filter_name, filter_badge_data, prepared_matches, handle):
        if handle not in prepared_matches or not filter_badge_data["active"]:
            return None
        return {
            "background_color": filter_badge_data["background_color"],
            "tooltip": "Matches filter: " + filter_name,
            "content": [{
                "content_type": "text",
                "text": filter_badge_data["content_text"],
                "text_color": filter_badge_data["text_color"],
            }]
        }

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
                    "text_color",
                ]
            elif content_element_info["content_type"] == "icon_file_svg":
                content_element_type_keys = [
                    "file",
                    "current_color",
                ]
            elif content_element_info["content_type"] == "icon_svg_data_callback":
                content_element_type_keys = [
                    "callback",
                    "fill_color",
                    "stroke_color",
                    "line_width",
                ]
            # TODO image / pixel graphic
            assert all(key in self.CONTENT_ELEMENT_KEYS+content_element_type_keys for key in content_element_info) # all keys are known
        if "click_callback" in content_element_info:
            assert callable(content_element_info["click_callback"])
