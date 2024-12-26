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

    def reset(self):
        # NOTE: ancestors have positive generation number (descendants negative)
        self.generation_spread = {}
        
        # To only allocate the vertical space required for the connections between two ancestor generations,
        # we keep track of the number of connections in each generation (left and right side separately)
        self.num_connections_per_generation = {} # key i: number of connections between gen i and gen i+1
        # After dry run, keep track where we are using this property.
        self.i_connections_per_generation = {}

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

        if x_person == 0 and person_generation == 0:
            # this is a new active person
            self.reset()

        # initialize subtree left and right bounds
        person_bounds = {"st_l": 0, "st_r": 0} # wrt x (left is usually negative, right is usually positive)

        person = self.ftv.get_person_from_handle(person_handle)

        if alignment is None:
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
            person_box_bounds = self.widget_manager.add_person(person_handle, x_person, person_generation, alignment)
            person_bounds.update(person_box_bounds)
        person_bounds["st_l"] = -person_width/2
        person_bounds["st_r"] = person_width/2

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

    def process_families(self, person_handle, person_bounds, x_person, person_generation, dry_run, process_descendants):
        family_width = self.canvas_manager.family_width
        person_width = self.canvas_manager.person_width
        spouse_sep = self.canvas_manager.spouse_sep

        person = self.ftv.get_person_from_handle(person_handle)
        family_handles = person.get_family_handle_list()
        is_primary_family = True
        for i_family, family_handle in enumerate(family_handles):
            is_primary_family = i_family == 0
            if not is_primary_family: # TODO for now
                continue

            family = self.dbstate.db.get_family_from_handle(family_handle)
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            person_is_s1 = father_handle == person_handle
            x_family = x_person + (-1+2*person_is_s1)*(person_width/2+spouse_sep/2)

            if not dry_run:
                family_bounds = self.widget_manager.add_family(family_handle, x_family, person_generation)
            else:
                family_bounds = None
            person_bounds["st_l"] = min(person_bounds["st_l"], x_family-x_person-family_width/2)
            person_bounds["st_r"] = max(person_bounds["st_r"], x_family-x_person+family_width/2)

            # spouse
            if person_is_s1: # (father), spouse is mother
                spouse_handle = mother_handle
                x_spouse = x_person+person_width+spouse_sep
                spouse_alignment = "l"
            else: # person is s2 (mother), spouse is father
                spouse_handle = father_handle
                x_spouse = x_person-person_width-spouse_sep
                spouse_alignment = "r"

            if not dry_run:
                if spouse_handle is not None:
                    self.widget_manager.add_person(spouse_handle, x_spouse, person_generation, spouse_alignment)
                else:
                    # missing person
                    self.widget_manager.add_missing_person(x_spouse, person_generation, spouse_alignment)

                # connections between family and spouses
                self.widget_manager.add_connection(x_person, person_bounds["bx_b"], x_person, family_bounds["bx_t"]) # very short, no handles
                self.widget_manager.add_connection(x_spouse, person_bounds["bx_b"], x_spouse, family_bounds["bx_t"])

            # This is not required if family edges aligns with spouse edges.
            # (They do in the current / default configuration.)
            person_bounds["st_l"] = min(person_bounds["st_l"], x_spouse-x_person-person_width/2)
            person_bounds["st_r"] = max(person_bounds["st_r"], x_spouse-x_person+person_width/2)

            # children
            if process_descendants:
                person_bounds = self.process_children(person_bounds, x_person, person_generation, dry_run, family, x_family, family_bounds)
        return person_bounds

    def process_children(self, person_bounds, x_person, person_generation, dry_run, family, x_family, family_bounds):
        child_sep = self.canvas_manager.child_sep

        min_generation = -self.ftv._config.get("appearance.familytreeview-num-descendant-generations-default")

        child_refs = family.get_child_ref_list()
        if len(child_refs) == 0:
            # Skip if there are no children.
            return person_bounds

        child_generation = person_generation - 1
        if child_generation < min_generation:
            # Only add children if person's children not exceeding min. generation limit.
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
                    x_family, family_bounds["bx_b"], x_child, child_bounds["bx_t"], dashed=dashed,
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
        if parent_generation > max_generation:
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

        if x_person == 0 and parent_generation == 1:
            # parent family of active person is centered
            x_family = 0
        else:
            if parent_generation not in self.generation_spread:
                self.generation_spread[parent_generation] = [-grandparent_families_sep/2+ancestor_sep, grandparent_families_sep/2-ancestor_sep]
            if x_person < 0:
                x_family = min(x_person, self.generation_spread[parent_generation][0] - (ancestor_sep + family_width/2))
                self.generation_spread[parent_generation][0] = x_family - family_width/2
            else:
                x_family = max(x_person, self.generation_spread[parent_generation][1] + (ancestor_sep + family_width/2))
                self.generation_spread[parent_generation][1] = x_family + family_width/2

        if not dry_run:
            family_bounds = self.widget_manager.add_family(parent_family_handle, x_family, parent_generation)

        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()
        x_father = x_family - spouse_sep/2 - person_width/2
        x_mother = x_family + spouse_sep/2 + person_width/2

        # Ancestors of each generation need to be added from the middle, so inner parent need to be first.
        if x_family < 0:
            inner_parent_handle = mother_handle
            inner_parent_x = x_mother
            inner_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel + 1
            inner_parent_alignment = "l"
            outer_parent_handle = father_handle
            outer_parent_x = x_father
            outer_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel
            outer_parent_alignment = "r"
        else: # x_family >= 0
            inner_parent_handle = father_handle
            inner_parent_x = x_father
            inner_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel
            inner_parent_alignment = "r"
            outer_parent_handle = mother_handle
            outer_parent_x = x_mother
            outer_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel + 1
            outer_parent_alignment = "l"

        if inner_parent_handle is not None:
            inner_parent_bounds = self.process_person(inner_parent_handle, inner_parent_x, parent_generation, dry_run=dry_run, alignment=inner_parent_alignment, process_families=False, process_descendants=False, ahnentafel=inner_parent_ahnentafel)
        else:
            # missing inner parent
            if not dry_run:
                inner_parent_bounds = self.add_missing_person(inner_parent_x, parent_generation, inner_parent_alignment)
        if outer_parent_handle is not None:
            outer_parent_bounds = self.process_person(outer_parent_handle, outer_parent_x, parent_generation, dry_run=dry_run, alignment=outer_parent_alignment, process_families=False, process_descendants=False, ahnentafel=outer_parent_ahnentafel)
        else:
            # missing outer parent
            if not dry_run:
                outer_parent_bounds = self.add_missing_person(outer_parent_x, parent_generation, outer_parent_alignment)

        # TODO include parents' bounds (?)

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

            self.widget_manager.add_connection(family_bounds["x"], family_bounds["bx_b"], x_person, person_bounds["bx_t"], m=m, dashed=dashed, handle1=parent_family_handle, handle2=person.handle)

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
