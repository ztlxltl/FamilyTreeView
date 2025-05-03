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


from math import atan, cos, pi, sin, sqrt
from typing import TYPE_CHECKING

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango

from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.lib import Person
from gramps.gui.utils import get_contrast_color, rgb_to_hex

from family_tree_view_canvas_manager_base import FamilyTreeViewCanvasManagerBase
from family_tree_view_utils import get_gettext, import_GooCanvas, make_hashable
if TYPE_CHECKING:
    from family_tree_view_widget_manager import FamilyTreeViewWidgetManager


GooCanvas = import_GooCanvas()

_ = get_gettext()

class FamilyTreeViewCanvasManager(FamilyTreeViewCanvasManagerBase):
    def __init__(
        self,
        widget_manager: "FamilyTreeViewWidgetManager",
        *args,
        cb_background=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.widget_manager = widget_manager
        self.ftv = self.widget_manager.ftv

        self.canvas.props.has_tooltip = True

        self.scale_factor_min = 1/100
        self.canvas_padding = 100_000

        # inside boxes
        self.padding = 10
        self.border_width = 2
        self.border_width_hover = 4

        self.max_name_line_count = 2

        self.expander_sep = 5 # distance between expander and nearby boxes/expanders

        # horizontal seps
        self.spouse_sep = 10 # horizontal space between spouses
        self.grandparent_families_sep = 80 # horizontal space between the parental and maternal ancestors of active person

        # vertical seps
        self.above_family_sep = 10 # vertical space between family box and spouses above it

        # box sizes
        self.corner_radius = 10
        self.highlight_spread_radius = 20
        self.person_info_box_width = 400
        self.person_info_box_height = 200
        self.family_info_box_width = 450
        self.family_info_box_height = 150
        self.expander_size = 20

        # badges
        self.badge_sep = 5
        self.badge_padding = 5
        self.badge_radius = 10
        self.badge_content_sep = 2

        # connections
        self.connection_radius = 10
        self.connection_sep = 10

        # combinations
        self.expander_space_needed = self.expander_sep + self.expander_size + self.expander_sep
        self.below_family_sep = self.expander_space_needed + 2*self.connection_radius + self.expander_space_needed + self.badge_radius
        sep_for_two_expanders = 2*self.expander_space_needed # with double self.expander_sep in the middle
        self.child_subtree_sep = sep_for_two_expanders
        self.sibling_sep = sep_for_two_expanders
        self.other_families_sep = sep_for_two_expanders # horizontal space between families with sharing a spouse
        self.ancestor_sep = sep_for_two_expanders
        self.other_parent_families_sep = sep_for_two_expanders

        # visibility threshold
        # Set the offset to positive a number for testing, or to a
        # negative number for very high PPI screens.
        # TODO Detect screen PPI/DPI and adjust this value.
        visibility_threshold_offset = 0
        self.visibility_threshold_expanders = 2**(-4+visibility_threshold_offset)
        self.visibility_threshold_text = 2**(-5+visibility_threshold_offset)
        self.visibility_threshold_badges = 2**(-5+visibility_threshold_offset)

        # defaults
        self.reset_zoom_values()
        self.reset_transform()

        self.reset_canvas()
        self.reset_boxes()
        self.svg_pixbuf_cache = {}

        # add relative overlay
        self.overlay_group = None
        self.overlay_background_group = None

        # clicks
        if cb_background is not None:
            self.canvas.get_root_item().connect("button-press-event", self.click_callback, cb_background)

        # config connect to callbacks
        for key in [
            "interaction.familytreeview-zoom-level-default",
            "interaction.familytreeview-zoom-level-step"
        ]:
            self.ftv._config.connect(key, self.reset_zoom_values)

        for config_name in self.ftv._config.get_section_settings("boxes"):
            key = "boxes."+config_name
            self.ftv._config.connect(key, self.reset_boxes)

        def _cb_scroll_mode_changed(configManager, zero, scroll_mode, none):
            self.scroll_mode = scroll_mode
        self.ftv._config.connect(
            "interaction.familytreeview-scroll-mode",
            _cb_scroll_mode_changed
        )

        self.ftv.uistate.connect("nameformat-changed", self.reset_abbrev_names)
        self.ftv.connect("abbrev-rules-changed", self.reset_abbrev_names)

    def reset_canvas(self):
        super().reset_canvas()
        # Connections are added to a group created as first canvas element so connections are below everything else.
        self.connection_group = GooCanvas.CanvasGroup(parent=self.canvas.get_root_item())
        self.canvas_bounds = [0, 0, 0, 0] # left, top, right, bottom
        self.expander_list = []

    def reset_zoom_values(self, *args): # *args needed when used as a callback
        self.default_zoom_level = self.ftv._config.get("interaction.familytreeview-zoom-level-default")
        self.zoom_level_step = self.ftv._config.get("interaction.familytreeview-zoom-level-step")

    def reset_zoom(self):
        self.reset_zoom_values()
        self.set_zoom_level(self.default_zoom_level)

    def reset_abbrev_names(self):
        self.fitting_abbrev_names = {}

    def reset_boxes(self, *args): # *args needed when used as a callback
        # different size of box or different number of lines
        self.reset_abbrev_names()
        self.calculate_dimensions()

    def calculate_dimensions(self):
        self.calculate_line_height()

        self.person_width = self.ftv.config_provider.get_person_width()
        self.person_height = self.get_height_of_box_content_px("person") + 2*self.padding
        self.family_height = self.get_height_of_box_content_px("family") + 2*self.padding

        self.family_width = 2 * self.person_width + self.spouse_sep

        # vertical offset between bottom of family and bottom of spouses
        # above it:
        self.bottom_family_offset = self.above_family_sep + self.family_height
        # vertical space between persons from consecutive generations
        # (only generation <= 2, above also considers multiple
        # connections):
        self.generation_sep = self.bottom_family_offset + self.below_family_sep
        self.generation_offset = self.generation_sep + self.person_height

        self.default_y = -self.person_height/2

    def calculate_line_height(self):
        style_context = self.canvas_container.get_style_context()
        font_desc = style_context.get_font(Gtk.StateFlags.NORMAL)
        text_item = GooCanvas.CanvasText(text=" ",font_desc=font_desc)
        ink_extent_rect, logical_extent_rect = text_item.get_natural_extents()
        # convert from Pango units to pixels
        self.line_height_px = logical_extent_rect.height/Pango.SCALE

    def get_height_of_box_content_px(self, box_type):
        # sum up gutter, image height and lines
        h = 0
        if box_type == "person":
            content_items = self.ftv.config_provider.get_person_content_item_defs()
        else:
            content_items = self.ftv.config_provider.get_family_content_item_defs()
        for item in content_items:
            if item[0] == "gutter":
                h += item[1]["size"]
            elif item[0] == "image":
                h += item[1]["max_height"]
            else:
                h += item[1].get("lines", 1) * self.line_height_px
        return h

    def close_add_relative_overlay(self):
        self.overlay_group.remove()
        self.widget_manager.hide_close_tree_overlay_button()

    def init_add_relative_overlay(self):
        if self.overlay_group is not None:
            self.close_add_relative_overlay()

        self.widget_manager.info_box_manager.close_info_box()

        self.overlay_group = GooCanvas.CanvasGroup(parent=self.canvas.get_root_item())
        parent = self.overlay_group
        self.overlay_background_group = GooCanvas.CanvasGroup(parent=parent)
        # callback to close info box etc.
        self.overlay_background_group.connect("button-press-event", self.click_callback)

        self.widget_manager.show_close_tree_overlay_button(
            lambda *args: self.close_add_relative_overlay(),
            _("Close the \"Add relatives\" overlay")
        )

        bounds = self.canvas.get_bounds() # left top right bottom

        GooCanvas.CanvasRect(
            parent=self.overlay_background_group,
            x=bounds[0],
            y=bounds[1],
            width=bounds[2]-bounds[0],
            height=bounds[3]-bounds[1],
            fill_color_gdk_rgba=Gdk.RGBA(red=0.5, green=0.5, blue=0.5, alpha=0.75),
        )

        self.overlay_margin_stroke_group = GooCanvas.CanvasGroup(parent=self.overlay_background_group)
        self.overlay_margin_group = GooCanvas.CanvasGroup(parent=self.overlay_background_group)
        self.overlay_connection_group = GooCanvas.CanvasGroup(parent=self.overlay_background_group)

        self.overlay_margin = 35 # should not be slightly smaller or exactly the same as a common distance between boxes/lines
        self.overlay_margin_stroke = self.overlay_margin + 2 # fake stroke

        bg_color_found, bg_color = self.canvas.get_style_context().lookup_color("theme_bg_color")
        if bg_color_found:
            bg_color = tuple(bg_color)[:3]
        else:
            bg_color = (1, 1, 1)

        # TODO Clean up color related code so we don't need each color
        # in Gdk.RGBA and hex string.
        self.overlay_margin_color_gdk_rgba = Gdk.RGBA(
            red=bg_color[0],
            green=bg_color[1],
            blue=bg_color[2],
            alpha=1
        )
        self.overlay_margin_color_hex = rgb_to_hex((
            self.overlay_margin_color_gdk_rgba.red,
            self.overlay_margin_color_gdk_rgba.green,
            self.overlay_margin_color_gdk_rgba.blue
        ))
        self.overlay_margin_stroke_color_gdk_rgba = Gdk.RGBA(
            red=0, green=0, blue=0, alpha=1
        )
        self.overlay_margin_stroke_color_hex = "#000"

        max_person_lines = (
            (self.person_height - 2*self.padding) / self.line_height_px
        )
        max_family_lines = (
            (self.family_height - 2*self.padding) / self.line_height_px
        )

        return parent, max_person_lines, max_family_lines

    def open_add_person_relative_overlay(self, person_handle, x_person, generation, action):
        offset = self.get_center_in_units()
        parent, max_person_lines, max_family_lines = self.init_add_relative_overlay()

        # max with 1: We need at least one line (even though it can
        # cause negative gutter where the text will protrude vertically
        # into the padding).
        person_lines = min(max(1, max_person_lines), 4)
        family_lines = min(max(1, max_family_lines), 1) # always 1

        show_add_other_family = action in ["overlay", "overlay_direct", "overlay_all"]
        show_add_other_parent_family = action in ["overlay", "overlay_direct", "overlay_all"]
        show_add_sibling_existing_parents = action in ["overlay", "overlay_main", "overlay_all"]
        show_add_sibling_new_parents = action in ["overlay_main", "overlay_all"]
        show_add_child_other_family = action == "overlay_all"

        # person

        person = self.ftv.get_person_from_handle(person_handle)

        background_color, border_color = self.widget_manager.get_colors_for_missing()

        person_gutter_size = (
            self.person_height
            - 2*self.padding
            - person_lines*self.line_height_px
        ) / 2
        family_gutter_size = (
            self.family_height
            - 2*self.padding
            - family_lines*self.line_height_px
        ) / 2

        # prominent family: The family the person is directly attached
        # to in the tree or the main family of that person. They can be
        # different e.g. if the person is the first spouse of a child of
        # the active person but that child/spouse is the second spouse
        # of the person.
        try:
            prominent_family_handle = self.widget_manager.tree_builder.tree_cache_persons[(x_person, generation)]["prominent_family"]
        except KeyError:
            prominent_family_handle = None
        if prominent_family_handle is None:
            # if no prominent family in tree, use main family
            family_handle_list = person.get_family_handle_list()
            if len(family_handle_list) > 0:
                prominent_family_handle = family_handle_list[0]
        has_family = prominent_family_handle is not None

        # prominent parents: The parents the person is directly attached
        # to in the tree or the main parents of that person. They can be
        # different e.g. if the person is an adopted child of the active
        # person but the active person is not in the person's main
        # parent family (which may not be visible).
        try:
            prominent_parents_handle = self.widget_manager.tree_builder.tree_cache_persons[(x_person, generation)]["prominent_parents"]
        except KeyError:
            prominent_parents_handle = None
        if prominent_parents_handle is None:
            # if no prominent family in tree, use main family
            parent_family_handle_list = person.get_parent_family_handle_list()
            if len(parent_family_handle_list) > 0:
                prominent_parents_handle = parent_family_handle_list[0]
        has_parents = prominent_parents_handle is not None

        alignment = "r" # fallback
        if prominent_family_handle is not None:
            prominent_family = self.ftv.get_family_from_handle(prominent_family_handle)
            if person_handle == prominent_family.get_father_handle():
                alignment = "r"
            elif person_handle == prominent_family.get_mother_handle():
                alignment = "l"
        else:
            if person.gender == Person.MALE:
                alignment = "r"
            elif person.gender == Person.FEMALE:
                alignment = "l"
        if alignment == "l":
            m1 = -1
        else:
            m1 = 1

        person_bounds = self.widget_manager.add_person(person_handle, x_person, generation, alignment, canvas_parent=parent)
        self.add_overlay_margin(x_person, generation, "person")

        # prominent family and spouse

        if has_family:
            prominent_family = self.ftv.get_family_from_handle(prominent_family_handle)
            if person_handle == prominent_family.get_father_handle():
                prominent_spouse_handle = prominent_family.get_mother_handle()
                x_family = x_person + self.person_width/2 + self.spouse_sep/2
                new_spouse_is_first = False
            elif person_handle == prominent_family.get_mother_handle():
                prominent_spouse_handle = prominent_family.get_father_handle()
                x_family = x_person - self.person_width/2 - self.spouse_sep/2
                new_spouse_is_first = True
            else: # TODO is this fallback relevant?
                prominent_spouse_handle = None
                x_family = x_person + self.person_width/2 + self.spouse_sep/2
                new_spouse_is_first = False

            family_bounds = self.widget_manager.add_family(prominent_family_handle, x_family, generation, canvas_parent=parent)
            self.add_overlay_margin(x_family, generation, "family")
            self.add_overlay_connection(x_person, person_bounds["bx_b"], x_person, family_bounds["bx_t"], spouse_connection=True)

            x_spouse = x_family + (x_family-x_person)
            if prominent_spouse_handle is not None and len(prominent_spouse_handle) > 0:
                spouse_bounds = self.widget_manager.add_person(prominent_spouse_handle, x_spouse, generation, alignment, canvas_parent=parent)
            else:
                spouse_content_items = [
                    ("gutter", {"size": person_gutter_size}, {}),
                    ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                        "Add a new spouse"
                        "¦Add new spouse"
                        "¦Add spouse"
                        "¦+ spouse"
                        "¦+"
                    ).split("¦")})
                ]
                spouse_bounds = self.add_person(x_spouse, generation, spouse_content_items, background_color, border_color, True, False, click_callback=lambda *args, alignment=alignment: self.ftv.add_new_spouse(prominent_family_handle, new_spouse_is_first), parent=parent)
            self.add_overlay_margin(x_spouse, generation, "person")
            self.add_overlay_connection(x_spouse, spouse_bounds["bx_b"], x_spouse, family_bounds["bx_t"], spouse_connection=True)

            x_new_child = x_family
            child_content_items = [
                ("gutter", {"size": person_gutter_size}, {}),
                ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                    "Add a new child"
                    "¦Add new child"
                    "¦Add child"
                    "¦+ child"
                    "¦+"
                ).split("¦")})
            ]
            child_bounds = self.add_person(x_new_child, generation-1, child_content_items, background_color, border_color, True, True, click_callback=lambda *args: self.ftv.add_new_child(prominent_family_handle), parent=parent)
            self.add_overlay_margin(x_new_child, generation-1, "person")
            self.add_overlay_connection(x_family, family_bounds["bx_b"], x_new_child, child_bounds["bx_t"])

        # new family and spouse

        if has_family:
            if show_add_other_family:
                # new family needs to be next to existing family
                x_new_family = x_family - m1*(
                    self.family_width/2
                    + self.other_families_sep
                    + self.family_width/2
                )
        else:
            x_new_family = x_person + m1*(
                self.person_width/2
                + self.spouse_sep/2
            )

        if not has_family or show_add_other_family:
            family_content_items = [
                ("gutter", {"size": family_gutter_size}, {}),
                ("text_abbr", {"lines": family_lines}, {"abbr_texts": _(
                    "Add a new family"
                    "¦Add new family"
                    "¦Add family"
                    "¦+ family"
                    "¦+"
                ).split("¦")})
            ]
            spouse_content_items = [
                ("gutter", {"size": person_gutter_size}, {}),
                ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                    "Add a new family and a new spouse"
                    "¦Add new family and new spouse"
                    "¦Add family and spouse"
                    "¦Add family, spouse"
                    "¦+ family, spouse"
                    "¦+"
                ).split("¦")})
            ]

            x_person2 = x_new_family - m1*(
                self.spouse_sep/2
                + self.person_width/2
            )
            x_new_spouse = x_new_family + m1*(
                self.spouse_sep/2
                + self.person_width/2
            )

            new_family_bounds = self.add_family(x_new_family, generation, family_content_items, background_color, border_color, click_callback=lambda *args: self.ftv.add_new_family(person_handle, alignment=="r"), parent=parent)
            new_spouse_bounds = self.add_person(x_new_spouse, generation, spouse_content_items, background_color, border_color, True, False, click_callback=lambda *args: self.ftv.add_new_family(person_handle, alignment=="r", add_spouse=True), parent=parent)
            self.add_overlay_margin(x_new_family, generation, "family")
            self.add_overlay_margin(x_new_spouse, generation, "person")

            self.add_overlay_connection(x_person, person_bounds["bx_b"], x_person2, new_family_bounds["bx_t"], spouse_connection=True)
            self.add_overlay_connection(x_new_spouse, new_spouse_bounds["bx_b"], x_new_spouse, new_family_bounds["bx_t"], spouse_connection=True)

            if show_add_child_other_family or not has_family:
                child_content_items = [
                    ("gutter", {"size": person_gutter_size}, {}),
                    ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                        "Add a new family and a new child"
                        "¦Add new family and new child"
                        "¦Add family and child"
                        "¦Add family, child"
                        "¦+ family, child"
                        "¦+"
                    ).split("¦")})
                ]
                x_new_child = x_new_family
                new_child_bounds = self.add_person(x_new_child, generation-1, child_content_items, background_color, border_color, True, True, click_callback=lambda *args: self.ftv.add_new_family(person_handle, alignment=="r", add_child=True), parent=parent)
                self.add_overlay_margin(x_new_child, generation-1, "person")
                self.add_overlay_connection(x_new_family, new_family_bounds["bx_b"], x_new_child, new_child_bounds["bx_t"])

        if has_family and show_add_other_family:
            # fill empty hole in overlay margin
            self.add_overlay_margin(x_person2, generation, "person")

        # prominent parents

        if prominent_parents_handle is not None:
            # TODO Maybe use actual parent position (if parents are in
            # the tree) with a threshold for x difference as parents can
            # be far away.
            x_parents = x_person
            parents_bounds = self.widget_manager.add_family(prominent_parents_handle, x_parents, generation+1, canvas_parent=parent)
            self.add_overlay_margin(x_parents, generation+1, "family")
            self.add_overlay_connection(x_person, parents_bounds["bx_b"], x_person, person_bounds["bx_t"])

            prominent_parents = self.ftv.get_family_from_handle(prominent_parents_handle)
            prominent_father_handle = prominent_parents.get_father_handle()
            prominent_mother_handle = prominent_parents.get_mother_handle()
            x_father = x_parents - self.spouse_sep/2 - self.person_width/2
            if prominent_father_handle is not None and len(prominent_father_handle) > 0:
                father_bounds = self.widget_manager.add_person(prominent_father_handle, x_father, generation+1, "l", canvas_parent=parent)
            else:
                father_content_items = [
                    ("gutter", {"size": person_gutter_size}, {}),
                    ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                        "Add a new father"
                        "¦Add new father"
                        "¦Add father"
                        "¦+ father"
                        "¦+"
                    ).split("¦")})
                ]
                father_bounds = self.add_person(x_father, generation+1, father_content_items, background_color, border_color, True, False, click_callback=lambda *args: self.ftv.add_new_spouse(prominent_parents_handle, True), parent=parent)
            self.add_overlay_margin(x_father, generation+1, "person")
            self.add_overlay_connection(x_father, father_bounds["bx_b"], x_father, parents_bounds["bx_t"], spouse_connection=True)

            x_mother = x_parents + self.spouse_sep/2 + self.person_width/2
            if prominent_mother_handle is not None and len(prominent_mother_handle) > 0:
                mother_bounds = self.widget_manager.add_person(prominent_mother_handle, x_mother, generation+1, "l", canvas_parent=parent)
            else:
                mother_content_items = [
                    ("gutter", {"size": person_gutter_size}, {}),
                    ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                        "Add a new mother"
                        "¦Add new mother"
                        "¦Add mother"
                        "¦+ mother"
                        "¦+"
                    ).split("¦")})
                ]
                mother_bounds = self.add_person(x_mother, generation+1, mother_content_items, background_color, border_color, True, False, click_callback=lambda *args: self.ftv.add_new_spouse(prominent_parents_handle, False), parent=parent)
            self.add_overlay_margin(x_mother, generation+1, "person")
            self.add_overlay_connection(x_mother, mother_bounds["bx_b"], x_mother, parents_bounds["bx_t"], spouse_connection=True)

            if show_add_sibling_existing_parents:
                sibling_content_items = [
                    ("gutter", {"size": person_gutter_size}, {}),
                    ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                        "Add a new sibling"
                        "¦Add new sibling"
                        "¦Add sibling"
                        "¦+ sibling"
                        "¦+"
                    ).split("¦")})
                ]
                x_new_sibling = x_person + m1*(
                    self.person_width/2
                    + self.spouse_sep
                    + self.person_width
                    + self.sibling_sep
                    + self.person_width/2
                )
                new_sibling_bounds = self.add_person(x_new_sibling, generation, sibling_content_items, background_color, border_color, True, True, click_callback=lambda *args: self.ftv.add_new_child(prominent_parents_handle), parent=parent)
                self.add_overlay_margin(x_new_sibling, generation, "person")
                self.add_overlay_connection(x_parents, parents_bounds["bx_b"], x_new_sibling, new_sibling_bounds["bx_t"])

        # new parents

        if has_parents:
            if show_add_other_parent_family:
                # new parents need to be next to existing parents
                x_new_parents = x_parents - m1*(
                    self.family_width/2
                    + self.other_parent_families_sep
                    + self.family_width/2
                )
        else:
            x_new_parents = x_person

        if not has_parents or show_add_other_parent_family:
            parents_content_items = [
                ("gutter", {"size": family_gutter_size}, {}),
                ("text_abbr", {"lines": family_lines}, {"abbr_texts": _(
                    "Add a new parent family"
                    "¦Add new parent family"
                    "¦Add parent family"
                    "¦Add parents"
                    "¦+ parents"
                    "¦+"
                ).split("¦")})
            ]
            father_content_items = [
                ("gutter", {"size": person_gutter_size}, {}),
                ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                    "Add a new parent family and a new father"
                    "¦Add new parent family and new father"
                    "¦Add parent family and father"
                    "¦Add parent family, father"
                    "¦Add parents, father"
                    "¦+ parents, father"
                    "¦+"
                ).split("¦")})
            ]
            mother_content_items = [
                ("gutter", {"size": person_gutter_size}, {}),
                ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                    "Add a new parent family and a new mother"
                    "¦Add new parent family and new mother"
                    "¦Add parent family and mother"
                    "¦Add parent family, mother"
                    "¦Add parents, mother"
                    "¦+ parents, mother"
                    "¦+"
                ).split("¦")})
            ]

            x_new_father = (
                x_new_parents
                - self.spouse_sep/2
                - self.person_width/2
            )
            x_new_mother = (
                x_new_parents
                + self.spouse_sep/2
                + self.person_width/2
            )

            new_parents_bounds = self.add_family(x_new_parents, generation+1, parents_content_items, background_color, border_color, click_callback=lambda *args: self.ignore_this_mouse_button_press() or self.ftv.add_new_parent_family(person_handle), parent=parent)
            new_father_bounds = self.add_person(x_new_father, generation+1, father_content_items, background_color, border_color, True, False, click_callback=lambda *args: self.ignore_this_mouse_button_press() or self.ftv.add_new_parent_family(person_handle, add_parent=1), parent=parent)
            new_mother_bounds = self.add_person(x_new_mother, generation+1, mother_content_items, background_color, border_color, True, False, click_callback=lambda *args: self.ignore_this_mouse_button_press() or self.ftv.add_new_parent_family(person_handle, add_parent=2), parent=parent)
            self.add_overlay_margin(x_new_parents, generation+1, "family")
            self.add_overlay_margin(x_new_father, generation+1, "person")
            self.add_overlay_margin(x_new_mother, generation+1, "person")

            self.add_overlay_connection(x_new_parents, new_parents_bounds["bx_b"], x_person, person_bounds["bx_t"])
            self.add_overlay_connection(x_new_father, new_father_bounds["bx_b"], x_new_father, new_parents_bounds["bx_t"], spouse_connection=True)
            self.add_overlay_connection(x_new_mother, new_mother_bounds["bx_b"], x_new_mother, new_parents_bounds["bx_t"], spouse_connection=True)

            if show_add_sibling_new_parents:
                sibling_content_items = [
                    ("gutter", {"size": person_gutter_size}, {}),
                    ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                        "Add a new parent family and a new sibling"
                        "¦Add new parent family and new sibling"
                        "¦Add parent family and sibling"
                        "¦Add parent family, sibling"
                        "¦Add parents, sibling"
                        "¦+ parents, sibling"
                        "¦+"
                    ).split("¦")})
                ]
                # New sibling needs to be placed next to the new or
                # existing family.
                if not has_family or show_add_other_family:
                    x_outer_family = x_new_family
                else:
                    x_outer_family = x_person + m1*(
                        self.person_width/2
                        + self.spouse_sep/2
                    )
                x_new_sibling = x_outer_family - m1*(
                    self.family_width/2
                    + self.sibling_sep
                    + self.person_width/2
                )
                new_sibling_bounds = self.add_person(x_new_sibling, generation, sibling_content_items, background_color, border_color, True, True, click_callback=lambda *args: self.ignore_this_mouse_button_press() or self.ftv.add_new_parent_family(person_handle, add_sibling=True), parent=parent)
                self.add_overlay_margin(x_new_sibling, generation, "person")
                self.add_overlay_connection(x_new_parents, new_parents_bounds["bx_b"], x_new_sibling, new_sibling_bounds["bx_t"])

        self.move_to_center(*offset)

    def open_add_family_relative_overlay(self, family_handle, x_family, generation):
        offset = self.get_center_in_units()
        parent, max_person_lines, max_family_lines = self.init_add_relative_overlay()

        person_lines = max(min(4, max_person_lines), 1)

        family = self.ftv.get_family_from_handle(family_handle)

        background_color, border_color = self.widget_manager.get_colors_for_missing()

        person_gutter_size = (
            self.person_height
            - 2*self.padding
            - person_lines*self.line_height_px
        ) / 2

        family_bounds = self.widget_manager.add_family(family_handle, x_family, generation, canvas_parent=parent)
        self.add_overlay_margin(x_family, generation, "family")

        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()
        spouse_content_items = [
            ("gutter", {"size": person_gutter_size}, {}),
            ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                "Add a new spouse"
                "¦Add new spouse"
                "¦Add spouse"
                "¦+ spouse"
                "¦+"
            ).split("¦")})
        ]
        for spouse_handle, alignment in [(father_handle, "l"), (mother_handle, "r")]:
            if alignment == "l":
                m1 = -1
            else:
                m1 = 1
            x_spouse = x_family + m1*(
                self.spouse_sep/2
                + self.person_width/2
            )
            if spouse_handle is None or len(spouse_handle) == 0:
                # alignment as kwarg to lambda since variable changes
                # due to loop.
                spouse_bounds = self.add_person(x_spouse, generation, spouse_content_items, background_color, border_color, True, False, click_callback=lambda *args, alignment=alignment: self.ftv.add_new_spouse(family_handle, alignment=="l"), parent=parent)
            else:
                spouse_bounds = self.widget_manager.add_person(spouse_handle, x_spouse, generation, alignment, canvas_parent=parent)
            self.add_overlay_margin(x_spouse, generation, "person")
            self.add_overlay_connection(x_spouse, spouse_bounds["bx_b"], x_spouse, family_bounds["bx_t"])

        x_new_child = x_family
        child_content_items = [
            ("gutter", {"size": person_gutter_size}, {}),
            ("text_abbr", {"lines": person_lines}, {"abbr_texts": _(
                "Add a new child"
                "¦Add new child"
                "¦Add child"
                "¦+ child"
                "¦+"
            ).split("¦")})
        ]
        child_bounds = self.add_person(x_new_child, generation-1, child_content_items, background_color, border_color, True, True, click_callback=lambda *args: self.ftv.add_new_child(family_handle), parent=parent)
        self.add_overlay_margin(x_new_child, generation-1, "person")
        self.add_overlay_connection(x_family, family_bounds["bx_b"], x_new_child, child_bounds["bx_t"])

        self.move_to_center(*offset)

    def add_overlay_margin(self, x, generation, box_type):
        y = self.widget_manager.tree_builder.get_y_of_generation(generation)
        if box_type == "person":
            width = self.person_width
            height = self.person_height
            y -= self.person_height
        else: # "family"
            width = self.family_width
            height = self.family_height
            y += self.above_family_sep

        bg_color_found, bg_color = self.canvas.get_style_context().lookup_color('theme_bg_color')
        if bg_color_found:
            bg_color = tuple(bg_color)[:3]
        else:
            bg_color = (1, 1, 1)

        GooCanvas.CanvasRect(
            parent=self.overlay_margin_group,
            x=x-width/2-self.overlay_margin,
            y=y-self.overlay_margin,
            width=width+2*self.overlay_margin,
            height=height+2*self.overlay_margin,
            fill_color_gdk_rgba=self.overlay_margin_color_gdk_rgba,
            stroke_color=None,
        )

        GooCanvas.CanvasRect(
            parent=self.overlay_margin_stroke_group,
            x=x-width/2-self.overlay_margin_stroke,
            y=y-self.overlay_margin_stroke,
            width=width+2*self.overlay_margin_stroke,
            height=height+2*self.overlay_margin_stroke,
            fill_color_gdk_rgba=self.overlay_margin_stroke_color_gdk_rgba,
            stroke_color=None,
        )

    def add_overlay_connection(self, x1, y1, x2, y2, ym=None, m=None, dashed=False, spouse_connection=False):
        if spouse_connection:
            line_width = 2*self.overlay_margin - self.above_family_sep
            line_width_stroke = 2*self.overlay_margin_stroke - self.above_family_sep
        else:
            line_width = 2*self.overlay_margin
            line_width_stroke = 2*self.overlay_margin_stroke
        self.add_connection(x1, y1, x2, y2, ym=ym, m=m, dashed=dashed, parent=self.overlay_connection_group)
        self.add_connection(x1, y1, x2, y2, ym=ym, m=m, dashed=dashed, parent=self.overlay_margin_group, line_width=line_width, fg_color=self.overlay_margin_color_hex)
        self.add_connection(x1, y1, x2, y2, ym=ym, m=m, dashed=dashed, parent=self.overlay_margin_stroke_group, line_width=line_width_stroke, fg_color=self.overlay_margin_stroke_color_hex)

    def add_person(self, x, generation, content_items, primary_color, secondary_color, alive, round_lower_corners, click_callback=None, badges=None, parent=None):

        # group
        use_default_parent = parent is None
        if use_default_parent:
            parent = self.canvas.get_root_item()
        group = GooCanvas.CanvasGroup(parent=parent)
        group.connect("button-press-event", self.click_callback, click_callback)
        parent = group

        # box
        y = self.widget_manager.tree_builder.get_y_of_generation(generation) # bottom center

        r = self.corner_radius
        if round_lower_corners:
            data = f"""
                M {x - self.person_width/2+r},{y}
                a {r} {r} 90 0 1 {-r} {-r}
                v {-self.person_height + 2*r}
                a {r} {r} 90 0 1 {r} {-r}
                h {self.person_width - 2*r}
                a {r} {r} 90 0 1 {r} {r}
                v {self.person_height - 2*r}
                a {r} {r} 90 0 1 {-r} {r}
                z
            """
        else:
            data = f"""
                M {x - self.person_width/2},{y}
                v {-self.person_height + r}
                a {r} {r} 90 0 1 {r} {-r}
                h {self.person_width - 2*r}
                a {r} {r} 90 0 1 {r} {r}
                v {self.person_height - r}
                z
            """

        line_width = self.ftv._config.get("appearance.familytreeview-box-line-width")
        if (
            x == 0 and generation == 0
            and use_default_parent # (0, 0) can be new child in overlay
            and self.ftv._config.get("appearance.familytreeview-highlight-root-person")
        ):
            # This is the root person.
            line_width = min(line_width + 2, line_width * 2)

        box = GooCanvas.CanvasPath(
            parent=parent,
            data=data,
            fill_color=primary_color,
            stroke_color=secondary_color,
            line_width=line_width,
        )

        contrast_color = rgb_to_hex(get_contrast_color(tuple(box.props.fill_color_gdk_rgba)[:3]))

        y_item = y - self.person_height + self.padding
        content_width = self.person_width-2*self.padding
        self.add_content_items(content_items, parent, x, y_item, secondary_color, contrast_color, content_width, alive)

        if not alive and self.ftv._config.get("appearance.familytreeview-show-deceased-ribbon"):
            s = 25
            r = 4
            svg_data = f"M {s-r*sqrt(2)} 0 h {r*sqrt(2)} l {-s} {s} v {-r*sqrt(2)} z"
            GooCanvas.CanvasPath(
                parent=parent,
                data=svg_data,
                fill_color=secondary_color,
                line_width=0,
                x=x-self.person_width/2,
                y=y-self.person_height,
            )

        if badges is not None:
            self.add_badges(badges, x+self.person_width/2-self.padding, y-self.person_height)

        self.adjust_bounds(x-self.person_width/2, y-self.person_height, x+self.person_width/2, y)

        return {
            # optical center x/y
            "oc_x": x,
            "oc_y": y - self.person_height/2,
            # box top/bottom
            "bx_t": y - self.person_height,
            "bx_b": y
        }

    def add_family(self, x, generation, content_items, primary_color, secondary_color, click_callback=None, badges=None, parent=None):

        # group
        if parent is None:
            parent = self.canvas.get_root_item()
        group = GooCanvas.CanvasGroup(parent=parent)
        group.connect("button-press-event", self.click_callback, click_callback)
        parent = group

        # box
        y = self.widget_manager.tree_builder.get_y_of_generation(generation) + self.above_family_sep # top center
        r = self.corner_radius
        data = f"""
            M {x - self.family_width/2},{y}
            h {self.family_width}
            v {self.family_height - r}
            a {r} {r} 90 0 1 {-r} {r}
            h {-self.family_width + 2*r}
            a {r} {r} 90 0 1 {-r} {-r}
            z
        """
        line_width = self.ftv._config.get("appearance.familytreeview-box-line-width")
        box = GooCanvas.CanvasPath(
            parent=parent,
            data=data,
            fill_color=primary_color,
            stroke_color=secondary_color,
            line_width=line_width,
        )

        contrast_color = rgb_to_hex(get_contrast_color(tuple(box.props.fill_color_gdk_rgba)[:3]))

        y_item = y + self.padding
        content_width = self.family_width-2*self.padding
        self.add_content_items(content_items, parent, x, y_item, "#000", contrast_color, content_width, True)
        if badges is not None:
            self.add_badges(badges, x+self.family_width/2-self.padding, y)

        self.adjust_bounds(x-self.family_width/2, y, x+self.family_width/2, y+self.family_height)

        return {
            # optical center x/y
            "oc_x": x,
            "oc_y": y + self.family_height - (self.family_height + self.above_family_sep + self.person_height)/2, # center of family and spouses
            # box top/bottom
            "bx_t": y,
            "bx_b": y + self.family_height,
            "x": x
        }

    def add_content_items(self, content_items, parent, x, y_item, avatar_color, contrast_color, content_width, alive):
        font_desc = self.canvas_container.get_style_context().get_font(Gtk.StateFlags.NORMAL)
        for item in content_items:
            if item[0] == "gutter":
                y_item += item[1]["size"]
            elif item[0] == "image":
                img_max_height = item[1]["max_height"]
                img_max_width = item[1]["max_width"]
                image_spec = item[2]["image_spec"]
                if image_spec is None:
                    pass # no image
                else:
                    image_filter = self.ftv._config.get("appearance.familytreeview-person-image-filter")
                    self.add_from_image_spec(
                        parent,
                        image_spec,
                        x-img_max_width/2,
                        y_item,
                        min(content_width, img_max_width), img_max_height,
                        grayscale=(image_filter == 1 and not alive) or image_filter == 2,
                        color=avatar_color,
                    )

                y_item += img_max_height

            elif item[0] in ["name", "names", "text", "text_abbr"]:
                max_height = self.line_height_px * item[1].get("lines", 1)
                if item[0] == "name":
                    if item[2]["name"] is None:
                        text = ""
                    else:
                        # first name in list is full name
                        text = item[2]["abbr_name_strs"][0]
                elif item[0] == "names":
                    if all(name is None for name in item[2]["names"]):
                        text = ""
                    else:
                        # first item in list is combination of full names
                        text = item[2]["abbr_name_strs"][0]
                elif item[0] == "text_abbr":
                    if len(item[2]["abbr_texts"]) == 0:
                        text = ""
                    else:
                        # first item in list is full sting
                        text = item[2]["abbr_texts"][0]
                else:
                    text = item[2]["text"]

                text_item = GooCanvas.CanvasText(
                    parent=parent,
                    x=x,
                    y=y_item,
                    text=text,
                    use_markup=True,
                    alignment=Pango.Alignment.CENTER,
                    anchor=GooCanvas.CanvasAnchorType.NORTH,
                    width=content_width,
                    height=max_height,
                    font_desc=font_desc,
                    fill_color=contrast_color,
                    # ellipsize needs to be applied after abbreviation selection
                    wrap=Pango.WrapMode.WORD,
                    visibility=GooCanvas.CanvasItemVisibility.VISIBLE_ABOVE_THRESHOLD,
                    visibility_threshold=self.visibility_threshold_text,
                )

                if (
                    (item[0] == "name" and item[2]["name"] is not None)
                    or (item[0] == "names" and any(name is not None for name in item[2]["names"]))
                    or (item[0] == "text_abbr" and len(item[2]["abbr_texts"]) > 0)
                ):
                    # The hashes are valid for the name format returned by
                    # self.ftv.abbrev_name_display.get_num_for_name_abbrev
                    # for the names.
                    if item[0] == "name":
                        hashable_name = make_hashable(item[2]["name"].serialize())
                    elif item[0] == "names":
                        hashable_name = make_hashable(tuple(
                            [item[2]["fmt_str"], item[1]["name_format"]] + [
                                name
                                if name is None else
                                name.serialize()
                                for name in item[2]["names"]
                            ]
                        ))
                    else: # text_abbr
                        hashable_name = None
                    if hashable_name is not None and hashable_name in self.fitting_abbrev_names:
                        text_item.text_data.text = self.fitting_abbrev_names[hashable_name]
                    else:
                        line_height_px = self.line_height_px
                        if item[0] == "text_abbr":
                            abbr_name_list = item[2]["abbr_texts"][1:] # skip full string used above
                        else: # name or names
                            abbr_name_list = item[2]["abbr_name_strs"][1:] # skip full name used above
                        for abbr_name in abbr_name_list:
                            ink_extent_rect, logical_extent_rect = text_item.get_natural_extents()

                            # Check the height since too many lines
                            # requires the use of abbreviations.
                            actual_height_px = logical_extent_rect.height/Pango.SCALE
                            expected_height_px = item[1].get("lines", 1)*line_height_px
                            # equivalent to rounding the number of lines
                            height_threshold_px = expected_height_px + line_height_px/2

                            # Also check the width, as long name parts
                            # can be too long for the content width.
                            # This is not ideal, because if the long
                            # name part is abbreviated last, other name
                            # parts are abbreviated which doesn't help.
                            actual_width_px = logical_extent_rect.width/Pango.SCALE

                            if (
                                actual_height_px > height_threshold_px
                                or actual_width_px > content_width
                            ):
                                text_item.text_data.text = abbr_name
                            else:
                                break
                        if hashable_name is not None:
                            self.fitting_abbrev_names[hashable_name] = text_item.text_data.text

                if item[1].get("lines", 1) == 1:
                    ellipsize = Pango.EllipsizeMode.END
                else:
                    # TODO somehow make ellipsize work for multiline
                    ellipsize = Pango.EllipsizeMode.NONE
                text_item.props.ellipsize = ellipsize

                y_item += max_height

    def add_connection(self, x1, y1, x2, y2, ym=None, m=None, dashed=False, click_callback=None, parent=None, line_width=None, fg_color=None):
        # assuming y1 < y2 (e.g. y1 is ancestor)
        if parent is None:
            parent = self.connection_group

        if ym is None:
            ym = (y1 + y2) / 2 # middle
        if x1 == x2:
            data = f"""
                M {x1} {y1}
                L {x2} {y2}
            """
        else:
            if m is not None:
                # m[0] which line, 0-based, counted from top to bottom
                # m[1] how many lines
                if m[1] > 1:
                    ym1 = ym - self.connection_sep * (m[1]-1)/2 # top
                    ym2 = ym + self.connection_sep * (m[1]-1)/2 # bottom
                    ym = ym1 + (ym2 - ym1) * m[0]/(m[1]-1) # horizontal part
            if (x1 < x2) != (y1 < y2): # xor
                sweepFlag1 = "1"
                sweepFlag2 = "0"
            else:
                sweepFlag1 = "0"
                sweepFlag2 = "1"
            if y1 < y2:
                yDirSign = -1
            else:
                yDirSign = 1
            if x1 < x2:
                xDirSign = 1
            else:
                xDirSign = -1

            r = self.connection_radius
            if abs(x1 - x2) < 2*r:
                # The line between the two arcs is not horizontal.
                Dx = abs(x1 - x2)/r
                # angle of the line (Dx=2 -> alpha=0, Dx=0° -> alpha=90°)
                alpha = pi/2 + 2*atan(Dx/(Dx-4))
                data = f"""
                    M {x1} {y1}
                    V {ym + yDirSign*r}
                    A {r} {r} 0 0 {sweepFlag1} {x1 + xDirSign*r*(1-sin(alpha))} {ym + yDirSign*r*(1-cos(alpha))}
                    L {x2 - xDirSign*r*(1-sin(alpha))} {ym - yDirSign*r*(1-cos(alpha))}
                    A {r} {r} 0 0 {sweepFlag2} {x2} {ym - yDirSign*r}
                    V {y2}
                """
            else:
                data = f"""
                    M {x1} {y1}
                    V {ym + yDirSign*r}
                    A {r} {r} 0 0 {sweepFlag1} {x1 + xDirSign*r} {ym}
                    H {x2 - xDirSign*r}
                    A {r} {r} 0 0 {sweepFlag2} {x2} {ym - yDirSign*r}
                    V {y2}
                """

        if fg_color is None:
            fg_color_found, fg_color = self.canvas.get_style_context().lookup_color('theme_fg_color')
            if fg_color_found:
                fg_color = rgb_to_hex(tuple(fg_color)[:3])
            else:
                fg_color = "black"

        if dashed:
            line_dash = GooCanvas.CanvasLineDash.newv([10, 5])
        else:
            line_dash = None

        if line_width is None:
            line_width = self.ftv._config.get("appearance.familytreeview-connections-line-width")
        path = GooCanvas.CanvasPath(
            parent=parent,
            data=data,
            stroke_color=fg_color,
            line_width=line_width,
            line_dash=line_dash
        )
        if line_width < 5:
            # add additional (invisible) path for larger clickable area
            path = GooCanvas.CanvasPath(
                parent=parent,
                data=data,
                line_width=5,
                stroke_color=None
            )
        # path is visible CanvasPath if no invisible was drawn.
        path.connect("button-press-event", self.click_callback, click_callback, ym)

    def add_badges(self, badges, x, y):
        # add badges right-aligned and right to left starting from (x, y), vertically centered

        font_desc = self.canvas_container.get_style_context().get_font(Gtk.StateFlags.NORMAL)

        x += self.badge_sep # will be subtracted in loop
        for badge_info in reversed(badges): # since they are added from right to left
            x -= self.badge_sep
            x_ = x
            group = GooCanvas.CanvasGroup(
                parent=self.canvas.get_root_item(),
                visibility=GooCanvas.CanvasItemVisibility.VISIBLE_ABOVE_THRESHOLD,
                visibility_threshold=self.visibility_threshold_badges,
            )
            if "click_callback" in badge_info:
                # We can't tell if the pointer moves away from the badge while the mouse button is held down.
                # item and target of button-release-event are the same whether the mouse stays on the badge or not.
                # Calling the callback on releasing the button when the mouse moved away would be counterintuitive.
                # Therefore, the callback is called on button-press-event.
                def cb_badge(item, target, event):
                    # This conditional is workaround since multiple users reported a KeyError.
                    # TODO Find the actual root cause of the KeyError.
                    if "click_callback" in badge_info:
                        badge_info["click_callback"]()
                        return True # Don't propagate further.
                    return False # Propagate as if there was no callback.
                group.connect("button-press-event", self.click_callback, cb_badge)
            badge_rect = GooCanvas.CanvasRect(
                parent=group,
                x=x-20, # initial x, will be set below
                y=y-self.padding, # half height
                height=2*self.padding,
                width=20, # initial width, will be set below
                radius_x=self.badge_radius,
                radius_y=self.badge_radius,
                fill_color=badge_info["background_color"],
                stroke_color=badge_info.get("stroke_color", "#000"),
                tooltip=badge_info.get("tooltip"),
            )

            x -= self.badge_padding
            x += self.badge_content_sep # padding will be subtracted in loop
            for badge_content_info in reversed(badge_info["content"]): # start with last as badges are right aligned
                x -= self.badge_content_sep
                tooltip = badge_content_info.get("tooltip", badge_info.get("tooltip"))
                if badge_content_info["content_type"] == "text":
                    badge_content_text = GooCanvas.CanvasText(
                        parent=group,
                        x=x,
                        y=y,
                        text=badge_content_info["text"],
                        fill_color=badge_content_info.get("text_color", "#000"),
                        alignment=Pango.Alignment.RIGHT,
                        anchor=GooCanvas.CanvasAnchorType.EAST,
                        font_desc=font_desc,
                        tooltip=tooltip,
                        visibility=GooCanvas.CanvasItemVisibility.VISIBLE_ABOVE_THRESHOLD,
                        visibility_threshold=self.visibility_threshold_text,
                    )
                    ink_extent_rect, logical_extent_rect = badge_content_text.get_natural_extents()
                    Pango.extents_to_pixels(logical_extent_rect)
                    x = x - logical_extent_rect.width
                elif badge_content_info["content_type"][:5] == "icon_":
                    icon_size = 10
                    if badge_content_info["content_type"] == "icon_file_svg":
                        self.add_from_image_spec(
                            group, ("svg_path", badge_content_info["file"]),
                            x-icon_size,
                            y-icon_size/2,
                            icon_size,
                            icon_size,
                            color=badge_content_info.get("current_color", "black"),
                            tooltip=tooltip,
                        )
                    elif badge_content_info["content_type"] == "icon_svg_data_callback":
                        svg_data = badge_content_info["callback"](icon_size, icon_size)
                        fill_color = badge_content_info.get("fill_color", "#000")
                        stroke_color = badge_content_info.get("line_width", None)
                        line_width = badge_content_info.get("line_width", 0)
                        GooCanvas.CanvasPath(
                            parent=group,
                            data=svg_data,
                            fill_color=fill_color,
                            stroke_color=stroke_color,
                            line_width=line_width,
                            tooltip=tooltip,
                            x=x-icon_size,
                            y=y-icon_size/2,
                        )
                    x = x - icon_size

            # TODO remove badge and break if too little space.

            x -= self.badge_padding
            w = x_ - x
            if w < 2*self.badge_radius:
                # circular corners
                badge_rect.props.radius_x = w/2
                badge_rect.props.radius_y = w/2
            badge_rect.props.x = x
            badge_rect.props.width = w

    def add_expander(self, x, y, ang, click_callback):
        group = GooCanvas.CanvasGroup(
            parent=self.canvas.get_root_item(),
            visibility=GooCanvas.CanvasItemVisibility.VISIBLE_ABOVE_THRESHOLD,
            visibility_threshold=self.visibility_threshold_expanders,
        )
        group.connect("button-press-event", self.click_callback, click_callback)
        self.expander_list.append(group)
        parent = group

        fg_color_found, fg_color = self.canvas.get_style_context().lookup_color('theme_fg_color')
        if fg_color_found:
            fg_color = tuple(fg_color)[:3]
        else:
            fg_color = (0, 0, 0)

        bg_color_found, bg_color = self.canvas.get_style_context().lookup_color('theme_bg_color')
        if bg_color_found:
            bg_color = tuple(bg_color)[:3]
        else:
            bg_color = (1, 1, 1)

        background_color = rgb_to_hex(tuple(fgc*0.2+bgc*0.8 for fgc, bgc in zip(fg_color, bg_color)))

        GooCanvas.CanvasEllipse(
            parent=parent,
            center_x=x,
            center_y=y,
            radius_x=self.expander_size/2,
            radius_y=self.expander_size/2,
            fill_color=background_color,
            stroke_color=None,
        )

        # Use path instead of pixbuf with icon as icon is pixelated.
        # (tried Gtk.IconLookupFlags.FORCE_SVG, doesn't work)
        l = 5
        data = f"""
            M {x-l/2} {y-l}
            L {x+l/2} {y}
            L {x-l/2} {y+l}
        """
        GooCanvas.CanvasPath(
            parent=parent,
            data=data,
            stroke_color=rgb_to_hex(fg_color),
        ).rotate(ang, x, y)

    def add_from_image_spec(self, parent, image_spec, x, y, max_width, max_height, color=None, grayscale=False, tooltip=None):
        if image_spec[0] in ["path", "svg_path", "pixbuf"]:
            if image_spec[0] == "path":
                path = image_spec[1]
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            elif image_spec[0] == "svg_path":
                svg_factor = 16 # if 1: too pixelated, if too large: slow
                path = image_spec[1]
                if color is None:
                    # When viewBox is specified, the scaling will
                    # increase resolution. If its not specified, the svg
                    # is scaled down.
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, max_width*svg_factor, max_height*svg_factor)
                else:
                    with open(path, 'r') as file:
                        svg_code = file.read()

                    # Insert the color to use for currentcolor.
                    # TODO Is this robust enough?
                    index = svg_code.lower().find("svg")
                    # 3 to insert after "svg"
                    svg_code = svg_code[:index+3] + f""" style="color: {color}" """ + svg_code[index+3:]

                    # Rendering SVGs at high resolution takes time.
                    # Caching the result speeds up building large trees.
                    if svg_code in self.svg_pixbuf_cache:
                        pixbuf = self.svg_pixbuf_cache[svg_code]
                    else:
                        pixbuf_loader = GdkPixbuf.PixbufLoader()
                        pixbuf_loader.set_size(
                            max_width*svg_factor,
                            max_height*svg_factor
                        )
                        pixbuf_loader.write(svg_code.encode())
                        try:
                            pixbuf_loader.close()
                        except GLib.Error:
                            # Error on MacOS, Gramps 6.0.0 for SVGs:
                            # gi.repository.GLib.GError: gdk-pixbuf-error-quark: Unrecognized image file format (3)
                            # Use white pixbuf of correct size as replacement
                            pixbuf = GdkPixbuf.Pixbuf.new(
                                GdkPixbuf.Colorspace.RGB, True, 8,
                                max_width, max_height
                            )
                            pixbuf.fill(0xFFFFFFFF)
                        else:
                            pixbuf = pixbuf_loader.get_pixbuf()
                        self.svg_pixbuf_cache[svg_code] = pixbuf
            else:
                pixbuf = image_spec[1]
            if grayscale:
                pixbuf.saturate_and_pixelate(pixbuf, 0, False)
            img = GooCanvas.CanvasImage(
                parent=parent,
                x=x,
                y=y,
                pixbuf=pixbuf,
                tooltip=tooltip,
            )
            # Setting image size with arguments doesn't work.
            scale = min(
                max_height/pixbuf.get_height(),
                max_width/pixbuf.get_width()
            )
            img.props.width=pixbuf.get_width()*scale
            img.props.height=pixbuf.get_height()*scale
            # Otherwise, the image is cropped instead of scaled:
            img.props.scale_to_fit=True

            # center image
            # needs to be done after setting size
            img.props.x += (max_width-img.props.width)/2
            img.props.y += (max_height-img.props.height)/2
        elif image_spec[0] == "svg_data_callback":
            svg_data, width, height = image_spec[1](
                max_width,
                max_height,
            )
            # Setting width and height (as a kwarg or the property),
            # causes distortion (the order of defining/setting those
            # matters). This happens when using absolute coordinates
            # (upper-case letters) as well as when using relative
            # coordinates (lower-case letters) in the path data.
            GooCanvas.CanvasPath(
                parent=parent,
                data=svg_data,
                fill_color=color,
                line_width=0,
                x=x+(max_width-width)/2,
                y=y+(max_height-height)/2,
                tooltip=tooltip,
            )

    def click_callback(self, root_item, target, event, other_callback=None, *other_args, **other_kwargs):
        if self.widget_manager.search_widget is not None:
            self.widget_manager.search_widget.hide_search_popover()
        if target is None:
            background_click = True
        else:
            background_click = False
            if self.overlay_background_group is not None:
                if self.overlay_background_group.find_child(target) != -1:
                    background_click = True
                else:
                    # Loop over sub-groups (margin, margin stroke,
                    # connections).
                    for i in range(self.overlay_background_group.get_n_children()):
                        child = self.overlay_background_group.get_child(i)
                        if child.find_child(target) != -1:
                            background_click = True
                            break
        if background_click:
            self.widget_manager.info_box_manager.close_info_box()
        if other_callback is not None:
            return other_callback(root_item, target, event, *other_args, **other_kwargs)
        return False

    def adjust_bounds(self, left, top, right, bottom):
        self.canvas_bounds[0] = min(self.canvas_bounds[0], left-self.canvas_padding)
        self.canvas_bounds[1] = min(self.canvas_bounds[1], top-self.canvas_padding)
        self.canvas_bounds[2] = max(self.canvas_bounds[2], right+self.canvas_padding)
        self.canvas_bounds[3] = max(self.canvas_bounds[3], bottom+self.canvas_padding)

        self.canvas.set_bounds(*self.canvas_bounds)

    def set_expander_visible(self, visible):
        if visible:
            visibility = GooCanvas.CanvasItemVisibility.VISIBLE
        else:
            visibility = GooCanvas.CanvasItemVisibility.INVISIBLE

        for expander in self.expander_list:
            expander.props.visibility = visibility
