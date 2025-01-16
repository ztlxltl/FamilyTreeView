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


from typing import TYPE_CHECKING

from gramps.gen.lib.childreftype import ChildRefType

if TYPE_CHECKING:
    from family_tree_view import FamilyTreeViewWidgetManager


class FamilyTreeViewTreeBuilder():
    """Collects all the information to build the tree and sends it to the canvas."""
    def __init__(self, widget_manager: "FamilyTreeViewWidgetManager"):
        self.widget_manager = widget_manager
        self.ftv = self.widget_manager.ftv
        self.dbstate = self.ftv.dbstate
        self.uistate = self.ftv.uistate
        self.canvas_manager = self.widget_manager.canvas_manager

        self.reset()

    def reset(self):
        """Should be called if the new tree is not closely related to the previous one, e.g. based on a different person."""
        # Reset what was expanded and what not.
        self.expanded = {}

        # In some cases this will be called again.
        self.prepare_redraw()

    def prepare_redraw(self):
        # NOTE: ancestors have positive generation number (descendants negative)
        self.generation_spread = {}

        # To only allocate the vertical space required for the connections between two ancestor generations,
        # we keep track of the number of connections in each generation (left and right side separately)
        self.num_connections_per_generation = {} # key i: number of connections between gen i and gen i+1
        # After dry run, keep track where we are using this property.
        self.i_connections_per_generation = {}

        self.expander_types_shown = self.ftv._config.get("expanders.familytreeview-expander-types-shown")
        self.expander_types_expanded = self.ftv._config.get("expanders.familytreeview-expander-types-expanded")

    def get_y_of_generation(self, generation):
        # negative y is up
        y = -generation*self.canvas_manager.generation_offset
        if generation > 3:
            if self.ftv._config.get("experimental.familytreeview-adaptive-ancestor-generation-dist"):
                s = sum(
                    max(v)
                    for g, v in self.num_connections_per_generation.items()
                    if g < generation
                )
            else:
                # To avoid overlapping lines, extra space has to be added if the lines could overlap.
                # Generation 3 (0 being active) needs to be the first which is shifted up (by 1 connection sep).
                # Generation 4 needs to be shifted up by 4 connection seps (1 from generation 3 and 3 own).
                # Generation 5 needs to be shifted up by 11 connection seps (4 from previous generations and 7 own).
                # etc.
                n = generation - 1
                s = (2**n - n - 1)
            y -= self.canvas_manager.connection_sep * s
        return y

    def process_person(
        self, person_handle, x_person, person_generation, dry_run=False, alignment=None,
        process_families=True, # needed for not processing families of ancestors again
        process_ancestors=True, # needed for not processing ancestors of descendants again
        process_descendants=True, # needed for not processing descendants of ancestors again
        ahnentafel=None, # needed for non-overlapping connection between ancestors
    ):
        person_width = self.canvas_manager.person_width

        # initialize subtree left and right bounds
        person_bounds = {"st_l": 0, "st_r": 0} # wrt x (left is usually negative, right is usually positive)

        person = self.ftv.get_person_from_handle(person_handle)

        if alignment is None:
            if person is None:
                alignment = "c"
            else:
                family_handles = person.get_family_handle_list()
                if len(family_handles) == 0:
                    alignment = "c"
                else:
                    family = self.dbstate.db.get_family_from_handle(family_handles[0]) # 0: main / primary
                    person_is_s1 = family.get_father_handle() == person_handle
                    if person_is_s1:
                        alignment = "r"
                    else:
                        alignment = "l"

        if not dry_run:
            if person is None:
                person_box_bounds = self.widget_manager.add_missing_person(x_person, person_generation, alignment)
            else:
                person_box_bounds = self.widget_manager.add_person(person_handle, x_person, person_generation, alignment)
            person_bounds.update(person_box_bounds)
        person_bounds["st_l"] = -person_width/2
        person_bounds["st_r"] = person_width/2

        if person is None:
            # Trying to process relatives doesn't make sense.
            return person_bounds

        if process_families:
            person_bounds = self.process_families(person_handle, person_bounds, x_person, person_generation, dry_run, process_descendants)

        if process_ancestors:
            # parents, siblings etc.
            if not dry_run and person_generation == 0 and self.ftv._config.get("experimental.familytreeview-adaptive-ancestor-generation-dist"):
                # fill self.num_connections_per_generation
                self.process_ancestors(person, person_bounds, x_person, person_generation, ahnentafel, dry_run=True)
                # reset generation spread after dry run to start over
                self.generation_spread = {}
            self.process_ancestors(person, person_bounds, x_person, person_generation, ahnentafel, dry_run=dry_run)

        return person_bounds

    def process_families(self, person_handle, person_bounds, x_person, person_generation, dry_run, process_descendants, skip_family_handle=None):
        family_width = self.canvas_manager.family_width
        person_width = self.canvas_manager.person_width
        spouse_sep = self.canvas_manager.spouse_sep

        person = self.ftv.get_person_from_handle(person_handle)
        family_handles = person.get_family_handle_list()
        if len(family_handles) > 1:
            if skip_family_handle is None or person_generation > 0:
                key = "other_families"
            else:
                key = "spouses_other_families"
            expand_other_families = self.get_expand(person_handle, key)
        else:
            expand_other_families = False
        is_primary_family = True
        for i_family, family_handle in enumerate(family_handles):
            if skip_family_handle is None:
                is_primary_family = i_family == 0
            elif skip_family_handle == family_handle:
                # This family has already been processed.
                continue
            else:
                is_primary_family = False
            if not is_primary_family and not expand_other_families:
                continue

            family = self.dbstate.db.get_family_from_handle(family_handle)
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            person_is_s1 = father_handle == person_handle
            if is_primary_family:
                x_family = x_person + (-1+2*person_is_s1)*(person_width/2+spouse_sep/2)
            else:
                children_bounds = {"st_l": 0, "st_r": 0}
                if process_descendants:
                    # Do a dry run to know how much space the children of the other families will need.
                    # continue
                    dummy_x = 0
                    dummy_dry_run = True
                    x_family = 0 # for dry-run
                    family_bounds = None # family_bounds is not needed for dry run of self.process_children
                    children_bounds = self.process_children(children_bounds, dummy_x, person_generation, dummy_dry_run, family, x_family, family_bounds)
                    # The primary family is processed before so the width their children is known, no dry-run required.
                if person_is_s1:
                    # Family will be on the left
                    x_family = x_person + person_bounds["st_l"] - max(family_width/2, children_bounds["st_r"]) - self.canvas_manager.other_families_sep
                else:
                    x_family = x_person + person_bounds["st_r"] + max(family_width/2, -children_bounds["st_l"]) + self.canvas_manager.other_families_sep

            if not dry_run:
                family_bounds = self.widget_manager.add_family(family_handle, x_family, person_generation)
            else:
                family_bounds = None
            person_bounds["st_l"] = min(person_bounds["st_l"], x_family-x_person-family_width/2)
            person_bounds["st_r"] = max(person_bounds["st_r"], x_family-x_person+family_width/2)

            # spouse
            if person_is_s1: # (father), spouse is mother
                spouse_handle = mother_handle
                x_spouse = x_family+spouse_sep/2+person_width/2
                spouse_alignment = "l"
            else: # person is s2 (mother), spouse is father
                spouse_handle = father_handle
                x_spouse = x_family-spouse_sep/2-person_width/2
                spouse_alignment = "r"

            if not dry_run:
                if spouse_handle is not None:
                    spouse_bounds = self.widget_manager.add_person(spouse_handle, x_spouse, person_generation, spouse_alignment)
                else:
                    # missing person
                    spouse_bounds = self.widget_manager.add_missing_person(x_spouse, person_generation, spouse_alignment)
            else:
                spouse_bounds = {}

            if not dry_run:
                # connections between family and spouses
                x_person_family = x_family - (-1+2*person_is_s1)*(person_width/2+spouse_sep/2)
                self.widget_manager.add_connection(x_person, person_bounds["bx_b"], x_person_family, family_bounds["bx_t"]) # very short, no handles
                self.widget_manager.add_connection(x_spouse, spouse_bounds["bx_b"], x_spouse, family_bounds["bx_t"])

                if len(family_handles) > 1 and self.expander_types_shown["other_families"]["default_hidden"]:
                    self.add_other_families_expander(person_handle, x_person, person_generation, person_is_s1, "other_families", expand_other_families)

            person_bounds["st_l"] = min(person_bounds["st_l"], (x_spouse - x_person) - person_width/2)
            person_bounds["st_r"] = max(person_bounds["st_r"], (x_spouse - x_person) + person_width/2)

            # children
            if process_descendants:
                person_bounds = self.process_children(person_bounds, x_person, person_generation, dry_run, family, x_family, family_bounds)

            # Spouse's other families after children, so there is enough space for all children.
            if spouse_handle is not None:
                # Since spouse is not processed (self.process_person()) and children's subtree size is in person_bounds:
                spouse_bounds["st_l"] = person_bounds["st_l"] - (x_spouse - x_person)
                spouse_bounds["st_r"] = person_bounds["st_r"] - (x_spouse - x_person)

                spouse = self.ftv.get_person_from_handle(spouse_handle)
                spouse_family_handles = spouse.get_family_handle_list()
                if len(spouse_family_handles) > 1 and (
                    i_family == 0 # i_family > 0: person's other families: They should not have an expander for other families of spouse.
                    and skip_family_handle is None # Since other families of the spouse can be the first (i_family == 0) of the spouse,
                    # also skip if the current call to process_families() is run on the spouse (skip_family_handle wouldn't be None).
                ):
                    spouse_bounds = self.process_families(spouse_handle, spouse_bounds, x_spouse, person_generation, dry_run, process_descendants, skip_family_handle=family_handle)
                    if not dry_run and self.expander_types_shown["spouses_other_families"]["default_hidden"]:
                        expand_spouses_other_families = self.get_expand(spouse_handle, "spouses_other_families")
                        self.add_other_families_expander(spouse_handle, x_spouse, person_generation, not person_is_s1, "spouses_other_families", expand_spouses_other_families)

                person_bounds["st_l"] = min(person_bounds["st_l"], (x_spouse - x_person) + spouse_bounds["st_l"])
                person_bounds["st_r"] = max(person_bounds["st_r"], (x_spouse - x_person) + spouse_bounds["st_r"])

        return person_bounds

    def process_children(self, person_bounds, x_person, person_generation, dry_run, family, x_family, family_bounds):
        child_sep = self.canvas_manager.child_subtree_sep

        min_generation = -self.ftv._config.get("appearance.familytreeview-num-descendant-generations-default")

        child_refs = family.get_child_ref_list()
        if len(child_refs) == 0:
            # Skip if there are no children.
            return person_bounds

        child_generation = person_generation - 1

        # children expander
        family_handle = family.get_handle()
        expand_children = self.get_expand(family_handle, "children", default=child_generation >= min_generation)
        if not dry_run and self.expander_types_shown["children"]["default_shown" if child_generation >= min_generation else "default_hidden"]:
            bottom_family_offset = self.canvas_manager.bottom_family_offset
            expander_sep = self.canvas_manager.expander_sep
            expander_size = self.canvas_manager.expander_size
            x_expander = x_family
            y_expander = self.get_y_of_generation(person_generation) + bottom_family_offset + expander_sep + expander_size/2
            ang = 90
            self.add_expander(x_expander, y_expander, expand_children, ang, family_handle, "children")

        if not expand_children:
            return person_bounds

        child_handles = [ref.ref for ref in child_refs]
        children_subtree_width = 0
        children_bounds = []
        for child_handle in child_handles:
            # Process child at x=0 to get relative subtree bounds.
            child_bounds = self.process_person(child_handle, 0, child_generation, dry_run=True, process_ancestors=False)
            children_bounds.append(child_bounds)
            child_subtree_width = child_bounds["st_r"] - child_bounds["st_l"]
            if child_subtree_width > 0 and children_subtree_width > 0:
                children_subtree_width += child_sep
            children_subtree_width += child_subtree_width
        x_child = x_family - children_subtree_width/2 # subtree should be centered

        if not dry_run:
            for i_child, child_handle in enumerate(child_handles):
                x_child -= children_bounds[i_child]["st_l"] # subtree left is negative
                child_bounds = self.process_person(child_handle, x_child, child_generation, dry_run=False, process_ancestors=False)
                dashed = self.get_dashed(family, child_handle)
                self.widget_manager.add_connection(
                    x_family, family_bounds["bx_b"], x_child, child_bounds["bx_t"],
                    ym=(family_bounds["bx_b"]+child_bounds["bx_t"]-self.canvas_manager.badge_radius)/2,
                    dashed=dashed,
                    # For multiple children, clicking near the parents is ambiguous.
                    handle1=family.handle, handle2=child_handle if len(child_handles) == 1 else None
                )
                x_child += children_bounds[i_child]["st_r"]
                x_child += child_sep
        person_bounds["st_l"] = min(person_bounds["st_l"], x_family-x_person-children_subtree_width/2) # /2: descendants are centered
        person_bounds["st_r"] = max(person_bounds["st_r"], x_family-x_person+children_subtree_width/2)
        return person_bounds

    def process_ancestors(self, person, person_bounds, x_person, person_generation, ahnentafel, dry_run=False):
        # family in which person is a child with parents and siblings
        parent_family_handle = person.get_main_parents_family_handle()
        if parent_family_handle is None:
            return

        parent_generation = person_generation + 1
        max_generation = self.ftv._config.get("appearance.familytreeview-num-ancestor-generations-default")

        # parents expander
        person_handle = person.get_handle()
        expand_parents = self.get_expand(person_handle, "parents", default=parent_generation <= max_generation)
        if not dry_run and self.expander_types_shown["parents"]["default_shown" if parent_generation <= max_generation else "default_hidden"]:
            person_height = self.canvas_manager.person_height
            badge_radius = self.canvas_manager.badge_radius # prevent overlap
            expander_sep = self.canvas_manager.expander_sep
            expander_size = self.canvas_manager.expander_size
            y_expander = self.get_y_of_generation(person_generation) - person_height - badge_radius - expander_sep - expander_size/2
            self.add_expander(x_person, y_expander, expand_parents, -90, person_handle, "parents")

        if not expand_parents:
            return

        if person_generation >= 1:
            if dry_run:
                self.num_connections_per_generation.setdefault(person_generation, [0, 0])
                self.num_connections_per_generation[person_generation][int(x_person > 0)] += 1
            else:
                self.i_connections_per_generation.setdefault(person_generation, [-1, -1]) # none, 1st will be 0
                self.i_connections_per_generation[person_generation][int(x_person > 0)] += 1

        person_width = self.canvas_manager.person_width
        family_width = self.canvas_manager.family_width
        spouse_sep = self.canvas_manager.spouse_sep
        grandparent_families_sep = self.canvas_manager.grandparent_families_sep
        ancestor_sep = self.canvas_manager.ancestor_sep

        family = self.dbstate.db.get_family_from_handle(parent_family_handle)

        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()

        # Ancestors of each generation need to be added from the middle, so inner parent need to be first.
        if x_person < 0:
            inner_parent_handle = mother_handle
            inner_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel + 1
            inner_parent_alignment = "l"
            outer_parent_handle = father_handle
            outer_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel
            outer_parent_alignment = "r"
        else: # x_person >= 0
            inner_parent_handle = father_handle
            inner_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel
            inner_parent_alignment = "r"
            outer_parent_handle = mother_handle
            outer_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel + 1
            outer_parent_alignment = "l"

        inner_parent_family_handles = None
        if x_person == 0 and parent_generation == 1:
            # parent family of active person is centered
            x_family = 0
        else:
            # Since the inner parent has their other parents towards the middle, room needs to be reserved for them.
            extra_left = 0
            extra_right = 0
            if inner_parent_handle is not None:
                inner_parent_family_handles = self.ftv.get_person_from_handle(inner_parent_handle).get_family_handle_list()
                if len(inner_parent_family_handles) > 1:
                    inner_parent_bounds = {"st_l": -person_width/2, "st_r": person_width/2}
                    inner_parent_bounds = self.process_families(inner_parent_handle, inner_parent_bounds, 0, parent_generation, True, parent_generation == 1, skip_family_handle=parent_family_handle)
                    # Extra space that has to be added between previous (inner) family (or middle) and this parent family make room for other families.
                    extra_left = inner_parent_bounds["st_l"] + person_width/2
                    extra_right = inner_parent_bounds["st_r"] - person_width/2

            if parent_generation not in self.generation_spread:
                self.generation_spread[parent_generation] = [-grandparent_families_sep/2+ancestor_sep, grandparent_families_sep/2-ancestor_sep]
            if x_person < 0:
                x_family = min(x_person, self.generation_spread[parent_generation][0] - (ancestor_sep + family_width/2) - extra_right)
                self.generation_spread[parent_generation][0] = x_family - family_width/2
            else:
                x_family = max(x_person, self.generation_spread[parent_generation][1] + (ancestor_sep + family_width/2) - extra_left)
                self.generation_spread[parent_generation][1] = x_family + family_width/2

        if not dry_run:
            family_bounds = self.widget_manager.add_family(parent_family_handle, x_family, parent_generation)

        x_father = x_family - spouse_sep/2 - person_width/2
        x_mother = x_family + spouse_sep/2 + person_width/2

        if x_person < 0:
            inner_parent_x = x_mother
            outer_parent_x = x_father
        else: # x_person >= 0
            inner_parent_x = x_father
            outer_parent_x = x_mother

        if inner_parent_handle is not None:
            inner_parent_bounds = self.process_person(inner_parent_handle, inner_parent_x, parent_generation, dry_run=dry_run, alignment=inner_parent_alignment, process_families=False, process_descendants=False, ahnentafel=inner_parent_ahnentafel)

            if inner_parent_family_handles is None: # only if not before
                inner_parent_family_handles = self.ftv.get_person_from_handle(inner_parent_handle).get_family_handle_list()
            if len(inner_parent_family_handles) > 1:
                # NOTE about process_descendants: In general, there is only room to show descendants for other families of outer ancestors.
                # There is no room for descendants of other families of inner ancestors without creating crossing lines.
                # To be fair (and to avoid questions and bug reports), we don't show descendants for other families of ancestors.
                # For the first ancestor generation, there is no risk of crossing lines, so allow descendants for their other families.

                if parent_generation == 1:
                    # TODO Something can be simplified here, since in gen == 1, x_person == 0 and father is always "inner", etc.
                    # To account for children of person (which is the active person if this is first ancestor generation), enlarge the st_l/r.
                    # Note that the inner_parent_bounds st_l/r are wrong but they are not used for first ancestor generation below.
                    inner_parent_bounds["st_l"] = min(inner_parent_bounds["st_l"], person_bounds["st_l"] - (inner_parent_x-x_person))
                    inner_parent_bounds["st_r"] = max(inner_parent_bounds["st_r"], person_bounds["st_r"] + (inner_parent_x-x_person))
                inner_parent_bounds = self.process_families(inner_parent_handle, inner_parent_bounds, inner_parent_x, parent_generation, dry_run, parent_generation == 1, skip_family_handle=parent_family_handle)
                if not dry_run and self.expander_types_shown["other_families"]["default_hidden"]:
                    expand_inner_parent_other_families = self.get_expand(inner_parent_handle, "other_families")
                    self.add_other_families_expander(inner_parent_handle, inner_parent_x, parent_generation, inner_parent_alignment == "r", "other_families", expand_inner_parent_other_families)
        else:
            # missing inner parent
            if not dry_run:
                inner_parent_bounds = self.add_missing_person(inner_parent_x, parent_generation, inner_parent_alignment)
            else:
                inner_parent_bounds = {"st_l": -person_width/2, "st_r": person_width/2}

        if outer_parent_handle is not None:
            outer_parent_bounds = self.process_person(outer_parent_handle, outer_parent_x, parent_generation, dry_run=dry_run, alignment=outer_parent_alignment, process_families=False, process_descendants=False, ahnentafel=outer_parent_ahnentafel)

            outer_parent_family_handles = self.ftv.get_person_from_handle(outer_parent_handle).get_family_handle_list()
            if len(outer_parent_family_handles) > 1:
                # NOTE about process_descendants: see above

                if parent_generation == 1:
                    outer_parent_bounds["st_l"] = min(outer_parent_bounds["st_l"], person_bounds["st_l"] + (outer_parent_x-x_person))
                    outer_parent_bounds["st_r"] = max(outer_parent_bounds["st_r"], person_bounds["st_r"] - (outer_parent_x-x_person))
                outer_parent_bounds = self.process_families(outer_parent_handle, outer_parent_bounds, outer_parent_x, parent_generation, dry_run, parent_generation == 1, skip_family_handle=parent_family_handle)
                if not dry_run and self.expander_types_shown["other_families"]["default_hidden"]:
                    expand_outer_parent_other_families = self.get_expand(outer_parent_handle, "other_families")
                    self.add_other_families_expander(outer_parent_handle, outer_parent_x, parent_generation, outer_parent_alignment == "r", "other_families", expand_outer_parent_other_families)
        else:
            # missing outer parent
            if not dry_run:
                outer_parent_bounds = self.add_missing_person(outer_parent_x, parent_generation, outer_parent_alignment)
            else:
                outer_parent_bounds = {"st_l": -person_width/2, "st_r": person_width/2}

        if parent_generation > 1:
            if x_family < 0:
                new_left = outer_parent_x + outer_parent_bounds[f"st_l"]
                new_right = inner_parent_x + inner_parent_bounds[f"st_r"]
            else:
                new_left = inner_parent_x + inner_parent_bounds[f"st_l"]
                new_right = outer_parent_x + outer_parent_bounds[f"st_r"]
            self.generation_spread[parent_generation][0] = min(self.generation_spread[parent_generation][0], new_left)
            self.generation_spread[parent_generation][1] = max(self.generation_spread[parent_generation][1], new_right)

        if not dry_run:
            # connections between family and spouses
            self.widget_manager.add_connection(inner_parent_x, inner_parent_bounds["bx_b"], inner_parent_x, family_bounds["bx_t"]) # very short, no handles
            self.widget_manager.add_connection(outer_parent_x, outer_parent_bounds["bx_b"], outer_parent_x, family_bounds["bx_t"])

            if ahnentafel is None:
                m = None
            else:
                if self.ftv._config.get("experimental.familytreeview-adaptive-ancestor-generation-dist"):
                    if person_generation > 1:
                        m0 = self.i_connections_per_generation[person_generation][int(x_person>0)]
                        m1 = self.num_connections_per_generation[person_generation][int(x_person>0)]
                        m = (m0, m1)
                    else:
                        m = None
                else: # use ahnentafel
                    # NOTE: floor(log2(ahnentafel)) == person_generation
                    first_maternal_ahnentafel_in_generation = 3*2**(person_generation-1)
                    if ahnentafel >= first_maternal_ahnentafel_in_generation:
                        # maternal side (right)
                        m0 = ahnentafel-first_maternal_ahnentafel_in_generation
                    else:
                        # paternal side (left)
                        m0 = (first_maternal_ahnentafel_in_generation-1)-ahnentafel
                    m = (
                        m0,
                        2**(person_generation-1) # -1 since only the lines on one side are counted since only those can overlap
                    )

            parent_family = self.dbstate.db.get_family_from_handle(parent_family_handle)
            dashed = self.get_dashed(parent_family, person.handle)

            self.widget_manager.add_connection(
                family_bounds["x"], family_bounds["bx_b"], x_person, person_bounds["bx_t"],
                ym=(family_bounds["bx_b"]+person_bounds["bx_t"]-self.canvas_manager.badge_radius)/2,
                m=m, dashed=dashed, handle1=parent_family_handle, handle2=person.handle
            )

    def add_missing_person(self, x_person, person_generation, alignment, dry_run=False):
        person_width = self.canvas_manager.person_width

        person_bounds = {"st_l": 0, "st_r": 0}

        if not dry_run:
            person_box_bounds = self.widget_manager.add_missing_person(x_person, person_generation, alignment)
            person_bounds.update(person_box_bounds)
        person_bounds["st_l"] = -person_width/2
        person_bounds["st_r"] = person_width/2

        return person_bounds

    def get_dashed(self, family, child_handle):
        child_ref = [ref for ref in family.get_child_ref_list() if ref.ref == child_handle][0]
        dashed = int(child_ref.get_father_relation()) != ChildRefType.BIRTH or int(child_ref.get_mother_relation()) != ChildRefType.BIRTH
        return dashed

    def get_expand(self, handle, key, default=None):
        expand = self.expanded.get(handle, {}).get(key, None)
        if expand is None:
            if default is None:
                expand = self.expander_types_expanded[key]
            else:
                expand = default
            self.expanded.setdefault(handle, {})[key] = expand
        return expand

    def add_expander(self, x_expander, y_expander, expanded, ang_collapsed, handle, key):
        def expander_clicked(root_item, target, event):
            # The fallback False should not be used, because self.expanded.setdefault()[key] = val is used before each call of self.add_expander().
            expand = not self.expanded.get(handle, {}).get(key, False)
            self.expanded.setdefault(handle, {})[key] = expand
            offset = self.canvas_manager.get_center_in_units()
            self.ftv.close_info_and_rebuild(self, offset=offset)
        if expanded:
            ang = ang_collapsed + 180
        else:
            ang = ang_collapsed
        self.widget_manager.add_expander(x_expander, y_expander, ang, expander_clicked)

    def add_other_families_expander(self, person_handle, x_person, person_generation, person_is_s1, key, expanded):
        person_width = self.canvas_manager.person_width

        # We can't use a button since canvas can be zoomed.
        expander_size = self.canvas_manager.expander_size
        expander_sep = self.canvas_manager.expander_sep
        # Expander for other families always on the outside of the main family:
        x_expander = x_person - (-1+2*person_is_s1)*(person_width/2 + expander_size/2 + expander_sep)
        y_expander = self.get_y_of_generation(person_generation) - expander_size/2
        ang = 0 + person_is_s1*180
        self.add_expander(x_expander, y_expander, expanded, ang, person_handle, key)
