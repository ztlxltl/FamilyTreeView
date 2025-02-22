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


from copy import deepcopy
from typing import TYPE_CHECKING

from gi.repository import Gdk, GLib, Gtk

from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.lib.childreftype import ChildRefType
from gramps.gui.utils import ProgressMeter

if TYPE_CHECKING:
    from family_tree_view import FamilyTreeViewWidgetManager


_ = GRAMPS_LOCALE.translation.gettext

class FamilyTreeViewTreeBuilder():
    """Collects all the information to build the tree and sends it to the canvas."""
    def __init__(self, widget_manager: "FamilyTreeViewWidgetManager"):
        self.widget_manager = widget_manager
        self.ftv = self.widget_manager.ftv
        self.dbstate = self.ftv.dbstate
        self.uistate = self.ftv.uistate
        self.canvas_manager = self.widget_manager.canvas_manager

        self.use_progress = False
        self.progress_meter = None
        self.check_to_show_progress_meter_event_sources = []
        # The progress meter should show up ass soon as we know that
        # it's needed. It's needed if the building of the tree takes
        # longer than:
        self.show_progress_meter_time_threshold = 1000 # in ms
        # The measured dry runs take about 1/10 of the time of the
        # actual runs (in the relevant range of tree complexity) of
        # descendants and ancestors. 
        self.check_to_show_progress_meter_activity_delay = (
            self.show_progress_meter_time_threshold/10
        )
        # The fraction delay should not be too large to show the
        # progress meter early, but if it is too early, the estimate of
        # total build time is bad.
        self.check_to_show_progress_meter_fraction_delay = 200 # in ms
        self.progress_pass_person_handles = []

        self.reset_filtered()
        self.reset()

    def reset_filtered(self):
        if self.ftv.generic_filter is None:
            self.filtered_person_handles = None
            return

        try:
            self.filtered_person_handles = self.ftv.generic_filter.apply(
                self.dbstate.db,
                user=self.uistate.viewmanager.user
            )
        except:
            dialog = Gtk.MessageDialog(
                transient_for=self.uistate.window,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="FamilyTreeView",
            )
            dialog.format_secondary_markup(_(
                "<b>Failed to apply filter.</b>\n"
                "An error occurred while applying the filter. "
                "This is most likely a bug in the filter rules. "
                "No filter is applied."
            ))
            dialog.run()
            dialog.destroy()

            self.filtered_person_handles = None

    def reset(self):
        """Should be called if the new tree is not closely related to the previous one, e.g. based on a different person."""
        # Reset what was expanded and what not.
        self.expanded = {}

    def build_tree(self, root_person_handle):
        # NOTE: ancestors have positive generation number (descendants negative)
        self.generation_spread = {}

        # To only allocate the vertical space required for the connections between two ancestor generations,
        # we keep track of the number of connections in each generation (left and right side separately)
        self.num_connections_per_generation = {} # key i: number of connections between gen i and gen i+1
        # After dry run, keep track where we are using this property.
        self.i_connections_per_generation = {}

        self.expander_types_shown = self.ftv._config.get("expanders.familytreeview-expander-types-shown")
        self.expander_types_expanded = self.ftv._config.get("expanders.familytreeview-expander-types-expanded")

        # By preventing Gramps from freezing, the tree is redrawn often.
        # Hide the tree while building it to avoid flickering caused by
        # the many tree updates. Use an image for the old tree to
        # prevent only briefly hiding the tree (small tree build fast).
        # If the widget is not in a window, it's not visible yet and we
        # don't need to hide it.
        widget = self.widget_manager.main_container_paned
        window = widget.get_window()
        if window is not None:
            # TODO This solution is not ideal: because of the static
            # image, the scrollbars don't disappear after a few seconds,
            # and resizing the window or the sidebar before the progress
            # meter pops up causes a wrong visualization (it looks
            # different when the canvas can adjust to the changed size).
            alloc = widget.get_allocation()
            pixbuf = Gdk.pixbuf_get_from_window(window, alloc.x, alloc.y, alloc.width, alloc.height)
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            self.widget_manager.main_widget.remove(widget)
            self.widget_manager.main_widget.pack_start(image, True, True, 0)
            self.widget_manager.main_widget.show_all()

        self.use_progress = self.ftv._config.get("experimental.familytreeview-tree-builder-use-progress")
        if self.use_progress:
            self.progress_meter = ProgressMeter(
                "FamilyTreeView",
                can_cancel=True,
                parent=self.uistate.window,
            )
            self.progress_meter._ProgressMeter__dialog.hide()
            self.progress_meter.set_pass(
                header=_("Building tree..."),
                mode=ProgressMeter.MODE_ACTIVITY,
            )

        self.process_person(
            root_person_handle, 0, 0,
            ahnentafel=1
        )

        if self.use_progress:
            self.cancel_checks_to_show_progress_meter()
            self.progress_meter.close()
            self.progress_meter = None

        if window is not None:
            self.widget_manager.main_widget.remove(image)
            self.widget_manager.main_widget.pack_start(widget, True, True, 0)
            # Make sure there are no pending events (to compute widget
            # sizes to correctly center the root person).
            while Gtk.events_pending():
                Gtk.main_iteration()

        self.ftv._set_filter_status()

    def schedule_check_to_show_progress_meter(self, activity=False):
        self.cancel_checks_to_show_progress_meter()

        if self.progress_meter._ProgressMeter__dialog.get_visible():
            # Nothing to do if already visible.
            return

        if activity:
            delay = self.check_to_show_progress_meter_activity_delay
        else:
            delay = self.check_to_show_progress_meter_fraction_delay
        event_source_id = GLib.timeout_add(
            delay,
            self.check_to_show_progress_meter,
            activity,
        )
        self.check_to_show_progress_meter_event_sources.append(
            GLib.main_context_default().find_source_by_id(event_source_id)
        )

    def check_to_show_progress_meter(self, activity=False):
        # TODO Drawback of the current implementation: If none of the
        # multiple passes triggers to show the progress meter, it may
        # still take longer than the threshold to build the tree.
        mode = self.progress_meter._ProgressMeter__mode
        if activity:
            if mode == ProgressMeter.MODE_ACTIVITY:
                # If still in activity mode, this will take long.
                # (Activity is used for fast dry runs.)
                self.progress_meter._ProgressMeter__dialog.show()
                self.cancel_checks_to_show_progress_meter()
            # else: Just switched to fraction mode but not yet cancelled
            # this call.
        else:
            index = self.progress_meter._ProgressMeter__pbar_index
            max_index = self.progress_meter._ProgressMeter__pbar_max
            delay = self.check_to_show_progress_meter_fraction_delay
            threshold = self.show_progress_meter_time_threshold
            if index/max_index < delay/threshold:
                # This will take longer than the threshold so show the
                # progress meter.
                self.progress_meter._ProgressMeter__dialog.show()
                self.cancel_checks_to_show_progress_meter()

    def cancel_checks_to_show_progress_meter(self):
        for source in self.check_to_show_progress_meter_event_sources:
            if not source.is_destroyed():
                GLib.source_remove(source.get_id())
        self.check_to_show_progress_meter_event_sources.clear()

    def get_cancelled(self):
        if not self.use_progress:
            return False
        if self.progress_meter is None:
            return True
        return self.progress_meter.get_cancelled()

    def get_y_of_generation(self, generation):
        # negative y is up
        y = -generation*self.canvas_manager.generation_offset
        if generation > 2:
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
        descendant_subtree_bounds=None, # needed for placement of aunts/uncles with descendants
        skip_family_handle=None, # needed when processing a parent to skip main family
        child_handle_with_other_parents_to_collapse=None, # needed when expanding other families of this person
    ):
        step = False
        if self.use_progress:
            if self.progress_meter._ProgressMeter__mode == ProgressMeter.MODE_FRACTION:
                if person_handle not in self.progress_pass_person_handles and not dry_run:
                    self.progress_pass_person_handles.append(person_handle)
                    step = True
            else: # ProgressMeter.MODE_ACTIVITY:
                if person_handle not in self.progress_pass_person_handles:
                    self.progress_pass_person_handles.append(person_handle)
                step = True # always show activity
        if step:
            self.progress_meter.step()
        else:
            # Prevent Gramps from freezing. ProgressMeter.step() also
            # does this.
            while Gtk.events_pending():
                Gtk.main_iteration()

        person_width = self.canvas_manager.person_width

        # Initialize subtree left and right bounds of the subtree and the generation.
        person_bounds = {"st_l": 0, "st_r": 0, "gs_l": 0, "gs_r": 0} # wrt x (left is usually negative, right is usually positive)
        if descendant_subtree_bounds is not None:
            person_bounds["st_l"] = descendant_subtree_bounds["st_l"]
            person_bounds["st_r"] = descendant_subtree_bounds["st_r"]

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
                person_box_bounds = self.widget_manager.add_person(person_handle, x_person, person_generation, alignment, ahnentafel=ahnentafel)
            person_bounds.update(person_box_bounds)
        else:
            person_bounds.update({"bx_t": 0, "bx_b": 0}) # replacement values
        person_bounds["st_l"] = min(person_bounds["st_l"], -person_width/2)
        person_bounds["st_r"] = max(person_bounds["st_r"], person_width/2)
        person_bounds["gs_l"] = min(person_bounds["gs_l"], -person_width/2)
        person_bounds["gs_r"] = max(person_bounds["gs_r"], person_width/2)

        if person is None:
            # Trying to process relatives doesn't make sense.
            return person_bounds

        if process_families and not self.get_cancelled():
            if self.use_progress and not dry_run and person_generation == 0 and x_person == 0:
                self.progress_meter.set_pass(
                    header=_("Building families and descendants..."),
                    mode=ProgressMeter.MODE_ACTIVITY,
                )
            person_bounds = self.process_families(person_handle, person_bounds, x_person, person_generation, dry_run, process_descendants, skip_family_handle=skip_family_handle, child_handle_with_other_parents_to_collapse=child_handle_with_other_parents_to_collapse)

        # person_bounds subtree includes all families of the person and it's spouse including all their children.
        # The ancestors have to be processed after the families (and their children) so that siblings of this person and the parents' other spouses' descendants can move to the outwards.

        if process_ancestors and not self.get_cancelled():
            # parents, siblings etc.
            if not dry_run and person_generation == 0 and self.ftv._config.get("experimental.familytreeview-adaptive-ancestor-generation-dist"):
                if self.use_progress and x_person == 0:
                    self.progress_meter.set_pass(
                        header=_("Preparing to build ancestors..."),
                        mode=ProgressMeter.MODE_ACTIVITY,
                    )
                    self.schedule_check_to_show_progress_meter(activity=True)
                    self.progress_pass_person_handles = []

                # This dry_run is required for the generation distance. By filling self.num_connections_per_generation, the generation distance can be chosen to be no larger than necessary.
                # deepcopy is required here to avoid changed person_bounds due to dry_run.
                self.process_ancestors(person, deepcopy(person_bounds), x_person, person_generation, ahnentafel, alignment, dry_run=True)
                # Reset generation spread after dry run to start over.
                self.generation_spread = {}

                if self.use_progress and x_person == 0:
                    self.progress_meter.set_pass(
                        header=_("Building ancestors..."),
                        total=len(self.progress_pass_person_handles),
                        mode=ProgressMeter.MODE_FRACTION,
                    )
                    self.schedule_check_to_show_progress_meter()
                    self.progress_pass_person_handles = []
            person_bounds = self.process_ancestors(person, person_bounds, x_person, person_generation, ahnentafel, alignment, dry_run=dry_run)

        return person_bounds

    def process_families(self, person_handle, person_bounds, x_person, person_generation, dry_run, process_descendants, skip_family_handle=None, child_handle_with_other_parents_to_collapse=None):
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

        children_possible = person_generation <= 1

        for i_family, family_handle in enumerate(family_handles):
            if self.get_cancelled():
                break
            if skip_family_handle is None:
                is_primary_family = i_family == 0
            elif skip_family_handle == family_handle:
                # This family has already been processed. Only add the expander.
                if not dry_run and len(family_handles) > 1 and self.expander_types_shown[key]["default_hidden"]:
                    family = self.dbstate.db.get_family_from_handle(family_handle)
                    person_is_s1 = family.get_father_handle() == person_handle
                    if child_handle_with_other_parents_to_collapse is None or person_generation > 1:
                        collapse_on_expand = None
                    else:
                        collapse_on_expand = [(child_handle_with_other_parents_to_collapse, "other_parents")]
                    self.add_other_families_expander(person_handle, x_person, person_generation, person_is_s1, key, expand_other_families, collapse_on_expand=collapse_on_expand)
                continue
            else:
                is_primary_family = False
            if not is_primary_family and not expand_other_families:
                continue

            family = self.dbstate.db.get_family_from_handle(family_handle)
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            person_is_s1 = father_handle == person_handle

            if not dry_run and i_family == 0 and len(family_handles) > 1 and self.expander_types_shown["other_families"]["default_hidden"]:
                if child_handle_with_other_parents_to_collapse is None or person_generation > 1:
                    collapse_on_expand = None
                else:
                    collapse_on_expand = [(child_handle_with_other_parents_to_collapse, "other_parents")]
                self.add_other_families_expander(person_handle, x_person, person_generation, person_is_s1, "other_families", expand_other_families, collapse_on_expand=collapse_on_expand)

            if is_primary_family:
                x_family = x_person + (-1+2*person_is_s1)*(person_width/2+spouse_sep/2)
            else:
                # At this point, person_bounds includes the person's family and the children of previous families
                children_bounds = {"st_l": 0, "st_r": 0}
                if process_descendants and children_possible:
                    # This is not the main/primary family of person, it has to move to the side.
                    # Do a dry run of the children of this families to know how much space they will need.
                    # The primary family was processed before so the width their children is known, no dry-run required.
                    dummy_x = 0
                    dummy_dry_run = True
                    x_family = 0 # for dry-run
                    family_bounds = None # family_bounds is not needed for dry run of self.process_children
                    children_bounds = self.process_children(children_bounds, dummy_x, person_generation, dummy_dry_run, family, x_family, family_bounds)

                if children_possible:
                    # Place the family so there is enough space for family and children.
                    if person_is_s1:
                        # Family will be on the left
                        x_family = x_person + person_bounds["st_l"] - max(family_width/2, children_bounds["st_r"]) - self.canvas_manager.other_families_sep
                    else:
                        x_family = x_person + person_bounds["st_r"] + max(family_width/2, -children_bounds["st_l"]) + self.canvas_manager.other_families_sep
                else:
                    if person_is_s1:
                        # Family will be on the left
                        x_family = x_person + person_bounds["gs_l"] - family_width/2 - self.canvas_manager.other_families_sep
                    else:
                        x_family = x_person + person_bounds["gs_r"] + family_width/2 + self.canvas_manager.other_families_sep

            if not dry_run:
                family_bounds = self.widget_manager.add_family(family_handle, x_family, person_generation)
            else:
                family_bounds = None
            person_bounds["st_l"] = min(person_bounds["st_l"], x_family-x_person-family_width/2)
            person_bounds["st_r"] = max(person_bounds["st_r"], x_family-x_person+family_width/2)
            person_bounds["gs_l"] = min(person_bounds["gs_l"], x_family-x_person-family_width/2)
            person_bounds["gs_r"] = max(person_bounds["gs_r"], x_family-x_person+family_width/2)

            # Now, person_bounds includes the current family but not the children.

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

            # If family box is as wide as both spouses, this shouldn't change anything.
            person_bounds["st_l"] = min(person_bounds["st_l"], (x_spouse - x_person) - person_width/2)
            person_bounds["st_r"] = max(person_bounds["st_r"], (x_spouse - x_person) + person_width/2)
            person_bounds["gs_l"] = min(person_bounds["gs_l"], (x_spouse - x_person) - person_width/2)
            person_bounds["gs_r"] = max(person_bounds["gs_r"], (x_spouse - x_person) + person_width/2)

            # Now, person_bounds includes the current family but not the descendants.

            # children
            if process_descendants:
                person_bounds = self.process_children(person_bounds, x_person, person_generation, dry_run, family, x_family, family_bounds)

            # Now, person_bounds includes the descendants.

            # Spouse's other families after children, so there is enough space for all children.
            if spouse_handle is not None:
                # Since spouse is not processed here (no self.process_person() here), there is no spouse_bounds.
                # Children's subtree size is in person_bounds. The relative person_bounds have to be converted to the position of the spouse.
                spouse_bounds["st_l"] = person_bounds["st_l"] - (x_spouse - x_person)
                spouse_bounds["st_r"] = person_bounds["st_r"] - (x_spouse - x_person)
                spouse_bounds["gs_l"] = person_bounds["gs_l"] - (x_spouse - x_person)
                spouse_bounds["gs_r"] = person_bounds["gs_r"] - (x_spouse - x_person)

                spouse = self.ftv.get_person_from_handle(spouse_handle)
                spouse_family_handles = spouse.get_family_handle_list()
                if len(spouse_family_handles) > 1 and (
                    i_family == 0 # i_family > 0: person's other families: They should not have an expander for other families of spouse.
                    and skip_family_handle is None # Since other families of the spouse can be the first (i_family == 0) of the spouse,
                    # also skip if the current call to process_families() is run on the spouse (skip_family_handle wouldn't be None).
                ):
                    spouse_bounds = self.process_families(spouse_handle, spouse_bounds, x_spouse, person_generation, dry_run, process_descendants, skip_family_handle=family_handle, child_handle_with_other_parents_to_collapse=child_handle_with_other_parents_to_collapse)
                    # expander was added by process_families

                person_bounds["st_l"] = min(person_bounds["st_l"], (x_spouse - x_person) + spouse_bounds["st_l"])
                person_bounds["st_r"] = max(person_bounds["st_r"], (x_spouse - x_person) + spouse_bounds["st_r"])
                person_bounds["gs_l"] = min(person_bounds["gs_l"], (x_spouse - x_person) + spouse_bounds["gs_l"])
                person_bounds["gs_r"] = max(person_bounds["gs_r"], (x_spouse - x_person) + spouse_bounds["gs_r"])

        # Now, person_bounds subtree includes all families of the person and it's spouse with all descendants.

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

        if not dry_run and self.use_progress and x_person == 0 and person_generation == 0:
            self.progress_meter.set_pass(
                header=_("Preparing to build descendants..."),
                mode=ProgressMeter.MODE_ACTIVITY,
            )
            self.schedule_check_to_show_progress_meter(activity=True)
            self.progress_pass_person_handles = []

        child_handles = [ref.ref for ref in child_refs]
        if self.ftv._config.get("experimental.familytreeview-filter-person-prune"):
            child_handles = self.filter_person_handles(child_handles)
        children_subtree_width = 0
        children_bounds = []
        for child_handle in child_handles:
            if self.get_cancelled():
                break
            # Process child at x=0 to get relative subtree bounds.
            child_bounds = self.process_person(child_handle, 0, child_generation, dry_run=True, process_ancestors=False)
            children_bounds.append(child_bounds)
            child_subtree_width = child_bounds["st_r"] - child_bounds["st_l"]
            if child_subtree_width > 0 and children_subtree_width > 0:
                children_subtree_width += child_sep
            children_subtree_width += child_subtree_width
        x_child = x_family - children_subtree_width/2 # subtree should be centered

        if not dry_run:
            if self.use_progress and x_person == 0 and person_generation == 0:
                self.progress_meter.set_pass(
                    header=_("Building descendants..."),
                    total=len(self.progress_pass_person_handles),
                    mode=ProgressMeter.MODE_FRACTION,
                )
                self.schedule_check_to_show_progress_meter()
                self.progress_pass_person_handles = []
            for i_child, child_handle in enumerate(child_handles):
                if self.get_cancelled():
                    break
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

            # reset to generic progress
            if self.use_progress and x_person == 0 and person_generation == 0:
                self.progress_meter.set_pass(
                    header=_("Building families and descendants..."),
                    mode=ProgressMeter.MODE_ACTIVITY,
                )
                self.schedule_check_to_show_progress_meter(activity=True)
        person_bounds["st_l"] = min(person_bounds["st_l"], x_family-x_person-children_subtree_width/2) # /2: descendants are centered
        person_bounds["st_r"] = max(person_bounds["st_r"], x_family-x_person+children_subtree_width/2)
        return person_bounds

    def process_siblings(self, person_bounds, x_person, person_handle, person_generation, person_alignment, dry_run, parent_family, x_parent_family, parent_family_bottom, side, which, m=None):
        # Person is one of the children of parent_family.
        # That person is already processed, only their siblings needs to be processed.

        # side is "b" (both), "l" (left) or "r" (right)
        # which is "b" (both), "y" (younger/after person in list) or "o" (older/before in list)

        sibling_sep = self.canvas_manager.sibling_sep

        child_refs = parent_family.get_child_ref_list()
        if len(child_refs) <= 1:
            # Skip if there are no siblings. 1 since root child already processed.
            return person_bounds

        sibling_generation = person_generation

        # siblings expander
        expand_children = self.get_expand(person_handle, "siblings")
        if not dry_run and self.expander_types_shown["siblings"]["default_hidden"]:
            bottom_family_offset = self.canvas_manager.bottom_family_offset
            expander_sep = self.canvas_manager.expander_sep
            expander_size = self.canvas_manager.expander_size
            if side == "b":
                if person_alignment in ["r", "c"]:
                    side_ = "l"
                else:
                    side_ = "r"
            else:
                side_ = side
            if side_ == "l":
                x_expander = x_parent_family - (expander_sep + expander_size)
                ang = 135
            else: # side_ == "r"
                x_expander = x_parent_family + (expander_sep + expander_size)
                ang = 45

            y_expander = self.get_y_of_generation(person_generation+1) + bottom_family_offset + expander_sep + expander_size/2
            collapse_on_expand = [(person_handle, "other_parents")]
            self.add_expander(x_expander, y_expander, expand_children, ang, person_handle, "siblings", collapse_on_expand=collapse_on_expand)

        if not expand_children:
            return person_bounds

        child_handles = [ref.ref for ref in child_refs]
        if self.ftv._config.get("experimental.familytreeview-filter-person-prune"):
            child_handles = self.filter_person_handles(child_handles)
        person_index = child_handles.index(person_handle)
        if which == "y":
            # younger (after person in the list)
            sibling_handles = ([], child_handles[person_index+1:])
        elif which == "o":
            # older (before person in the list)
            sibling_handles = (child_handles[:person_index], [])
        else:
            sibling_handles = (child_handles[:person_index], child_handles[person_index+1:])

        if side == "b":
            sides = [False, True]
        elif side == "l":
            sides = [False]
            sibling_handles = (sibling_handles[0] + sibling_handles[1], [])
        elif side == "r":
            sides = [True]
            sibling_handles = ([], sibling_handles[0] + sibling_handles[1])

        for is_right in sides:
            sibling_handles_on_side = sibling_handles[int(is_right)]
            lr = "r" if is_right else "l"
            if len(sibling_handles_on_side) == 0:
                continue
            if not is_right:
                sibling_handles_on_side = reversed(sibling_handles_on_side)
            if is_right:
                x_sibling = x_person + person_bounds["st_r"]
            else:
                x_sibling = x_person + person_bounds["st_l"]
            for sibling_handle in sibling_handles_on_side:
                process_descendants = person_generation <= 1
                # dry_run to know how much space is required on inner side.
                sibling_bounds = self.process_person(sibling_handle, 0, sibling_generation, dry_run=True, process_ancestors=False, process_descendants=process_descendants)
                if is_right:
                    x_sibling += -sibling_bounds["st_l"] + sibling_sep
                else:
                    x_sibling -= sibling_bounds["st_r"] + sibling_sep
                sibling_bounds = self.process_person(sibling_handle, x_sibling, sibling_generation, dry_run=dry_run, process_ancestors=False, process_descendants=process_descendants)
                if not dry_run:
                    dashed = self.get_dashed(parent_family, sibling_handle)
                    self.widget_manager.add_connection(
                        x_parent_family, parent_family_bottom, x_sibling, sibling_bounds["bx_t"],
                        ym=(parent_family_bottom+sibling_bounds["bx_t"]-self.canvas_manager.badge_radius)/2,
                        m=m,
                        dashed=dashed,
                        handle1=parent_family.handle, handle2=None # None: If there are siblings, clicking near the parent is ambiguous.
                    )
                x_sibling += sibling_bounds["st_"+lr]
            if is_right:
                person_bounds["st_r"] = max(
                    person_bounds["st_r"],
                    x_sibling-x_person
                )
                person_bounds["gs_r"] = max(
                    person_bounds["gs_r"],
                    x_sibling-x_person-sibling_bounds["st_r"]+sibling_bounds["gs_r"]
                )
            else:
                person_bounds["st_l"] = min(
                    person_bounds["st_l"],
                    x_sibling-x_person
                )
                person_bounds["gs_l"] = min(
                    person_bounds["gs_l"],
                    x_sibling-x_person-sibling_bounds["st_l"]+sibling_bounds["gs_l"]
                )
        return person_bounds

    def process_ancestors(self, person, person_bounds, x_person, person_generation, ahnentafel, alignment, dry_run=False):

        # The person_bounds st_l/r includes all families of the person and it's spouse including all their children.

        parent_generation = person_generation + 1
        max_generation = self.ftv._config.get("appearance.familytreeview-num-ancestor-generations-default")

        is_parent_family_of_root = parent_generation == 1

        person_handle = person.get_handle()

        person_width = self.canvas_manager.person_width
        family_width = self.canvas_manager.family_width
        spouse_sep = self.canvas_manager.spouse_sep
        grandparent_families_sep = self.canvas_manager.grandparent_families_sep
        ancestor_sep = self.canvas_manager.ancestor_sep
        other_parent_families_sep = self.canvas_manager.other_parent_families_sep

        if not dry_run:
            person_height = self.canvas_manager.person_height
            badge_radius = self.canvas_manager.badge_radius # prevent overlap
            expander_sep = self.canvas_manager.expander_sep
            expander_size = self.canvas_manager.expander_size

        parent_family_handle_list = person.get_parent_family_handle_list()

        expand_main_parents = False
        expand_other_parents = False
        if len(parent_family_handle_list) > 0:
            if parent_generation <= max_generation:
                sub_key = "default_shown"
            else:
                sub_key = "default_hidden"
            default = parent_generation <= max_generation
            expand_main_parents = self.get_expand(person_handle, "parents", default=default)

            if not dry_run and (
                self.expander_types_shown["parents"][sub_key]
                or (
                    expand_main_parents
                    and len(parent_family_handle_list) > 1
                    and self.expander_types_shown["other_parents"]["default_hidden"]
                )
            ):
                # both expanders need y
                y_expander = self.get_y_of_generation(person_generation) - person_height - badge_radius - expander_sep - expander_size/2

            if not dry_run and self.expander_types_shown["parents"][sub_key]:
                self.add_expander(x_person, y_expander, expand_main_parents, -90, person_handle, "parents")

            # Other parents expander is only visible if main parents expander is expanded:
            if expand_main_parents and len(parent_family_handle_list) > 1:
                expand_other_parents = self.get_expand(person_handle, "other_parents")
                if not dry_run and self.expander_types_shown["other_parents"]["default_hidden"]:
                    main_family = self.dbstate.db.get_family_from_handle(parent_family_handle_list[0])
                    if alignment == "l":
                        x_expander = x_person + (expander_sep + expander_size)
                        ang = -45
                        parent_to_collapse_handle = main_family.get_mother_handle()
                    else: # "c", "r"
                        x_expander = x_person - (expander_sep + expander_size)
                        ang = -135
                        parent_to_collapse_handle = main_family.get_father_handle()
                    if is_parent_family_of_root:
                        collapse_on_expand = [
                            (parent_to_collapse_handle, "other_families"), # TODO better: children of other families)
                            (person_handle, "siblings"),
                        ]
                    else:
                        # For older generations, other families (and their children) don't need to be collapsed since their descendants cannot be shown.
                        collapse_on_expand = [
                            (person_handle, "siblings"),
                        ]
                    self.add_expander(x_expander, y_expander, expand_other_parents, ang, person_handle, "other_parents", collapse_on_expand=collapse_on_expand)

        enumerated_parent_family_handle_list = list(enumerate(parent_family_handle_list))
        if len(enumerated_parent_family_handle_list) == 0:
            return person_bounds
        if person_generation > 1 and ((x_person > 0) ^ (alignment == "l")):
            # Start with last parent family in innermost spot
            enumerated_parent_family_handle_list = reversed(enumerated_parent_family_handle_list)
        elif is_parent_family_of_root:
            # Main parents last so their siblings are not between main parents and other parents
            enumerated_parent_family_handle_list = enumerated_parent_family_handle_list[1:] + [enumerated_parent_family_handle_list[0]]

        i_parent_family_processed = -1 # will be increased to 0
        for i, parent_family_handle in enumerated_parent_family_handle_list:
            if self.get_cancelled():
                break

            if parent_family_handle is None:
                continue

            is_main_parent_family = i == 0

            if is_main_parent_family:
                if not expand_main_parents:
                    return person_bounds
            else:
                if not expand_other_parents:
                    # Don't return/break. If family list is reversed
                    # above, the main parent family can be last
                    # iteration.
                    continue

            family = self.dbstate.db.get_family_from_handle(parent_family_handle)

            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()

            if (
                self.ftv._config.get("experimental.familytreeview-filter-person-prune")
                and len(
                    self.filter_person_handles([father_handle, mother_handle])
                ) == 0
            ):
                continue

            i_parent_family_processed += 1
            first_family_processed = i_parent_family_processed == 0

            if person_generation >= 1 and first_family_processed:
                # Only for generations with multiple parents on one side
                # and only once if there are multiple parents,
                # as they share the horizontal part of the connection.
                if dry_run:
                    self.num_connections_per_generation.setdefault(person_generation, [0, 0])
                    self.num_connections_per_generation[person_generation][int(x_person > 0)] += 1
                else:
                    self.i_connections_per_generation.setdefault(person_generation, [-1, -1]) # none, 1st will be 0
                    self.i_connections_per_generation[person_generation][int(x_person > 0)] += 1

            if is_parent_family_of_root:
                # In most cases this needs to be False
                # (mother is not inner but right which is treated similarly).
                # It only needs to be True if other parents of the root person are processed
                # and the root person is the father in his main family.
                mother_first = not is_main_parent_family and alignment == "r"
            else:
                # grandparents and above
                # On the left side of the tree, the right parent is the inner one.
                mother_first = x_person < 0

            # Ancestors of each generation need to be added from the middle, so inner parent need to be first.
            if mother_first:
                inner_parent_handle = mother_handle
                inner_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel + 1
                inner_parent_alignment = "l"
                outer_parent_handle = father_handle
                outer_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel
                outer_parent_alignment = "r"
            else: # father first (e.g. father inner or parents_of_root)
                inner_parent_handle = father_handle
                inner_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel
                inner_parent_alignment = "r"
                outer_parent_handle = mother_handle
                outer_parent_ahnentafel = None if ahnentafel is None else 2*ahnentafel + 1
                outer_parent_alignment = "l"

            inner_parent_family_handles = None
            if is_parent_family_of_root and is_main_parent_family:
                # parent family of active person is centered
                x_family = 0
                self.generation_spread[parent_generation] = [x_family - family_width/2, x_family + family_width/2]
            else: # not main parents of root (root's other parents or other generation)
                # Since the inner parent has their other parents towards the middle, room needs to be reserved for them.
                extra_left = 0
                extra_right = 0
                if inner_parent_handle is not None:
                    inner_parent = self.ftv.get_person_from_handle(inner_parent_handle)
                    inner_parent_family_handles = inner_parent.get_family_handle_list()
                    if len(inner_parent_family_handles) > 1:
                        # See the note below where the inner parent is actually processed.
                        inner_parent_bounds = {
                            "st_l": -person_width/2,
                            "st_r": person_width/2,
                            "gs_l": -person_width/2,
                            "gs_r": person_width/2
                        }
                        # Only dry_run, no handle to collapse needed:
                        process_descendants = is_parent_family_of_root and is_main_parent_family
                        inner_parent_bounds = self.process_families(inner_parent_handle, inner_parent_bounds, 0, parent_generation, True, process_descendants, skip_family_handle=parent_family_handle)
                        # Extra space that has to be added between previous (inner) family (or middle) and this parent family make room for other families.
                        extra_left = inner_parent_bounds["gs_l"] + person_width/2
                        extra_right = inner_parent_bounds["gs_r"] - person_width/2

                    # We need to dry_run the siblings of the inner parent (only gen 2 and above have this problem).
                    # They will not be processed below, but this requires the inner parent's parent family position,
                    # which depends on the inner parent position, which depends on how much space their siblings need.
                    if is_main_parent_family and parent_generation >= 2:
                        # Only the siblings of the main family can be shown

                        # TODO Get whether parent family of person's spouse is expanded.
                        # If this is the case, set side="b" (both) and which for each side.

                        if inner_parent_alignment == "l":
                            side = "r"
                        else:
                            side = "l"
                        grandparent_family_handle = inner_parent.get_main_parents_family_handle()
                        grandparent_family = self.ftv.get_family_from_handle(grandparent_family_handle)
                        if grandparent_family is not None and self.get_expand(inner_parent_handle, "parents"):
                            # replacement values
                            if (inner_parent_alignment == "l") ^ mother_first: # mother_first: assumption that this will stay the same
                                x_inner_parent_ = 105
                                x_grandparent_family_ = 175
                            else:
                                x_inner_parent_ = -105
                                x_grandparent_family_ = -175
                            which = "b"
                            grandparent_family_bottom = 0 # replacement
                            inner_parent_bounds_ = {"st_l": -65, "st_r": 65, "gs_l": -65, "gs_r": 65}
                            inner_parent_bounds_ = self.process_siblings(inner_parent_bounds_, x_inner_parent_, inner_parent_handle, parent_generation, inner_parent_alignment, True, grandparent_family, x_grandparent_family_, grandparent_family_bottom, side, which, None)
                            extra_left += inner_parent_bounds_["st_l"] + person_width/2
                            extra_right += inner_parent_bounds_["st_r"] - person_width/2

                if parent_generation not in self.generation_spread:
                    if is_parent_family_of_root:
                        # is_main_parent_family is false here.
                        # Ass space of main parents so other parents are placed correctly.
                        # This is required if other families are processed first since they need to be between main parents and main parents' siblings.
                        # family_width can be used here as other families of main parents are allowed if there are other parents.
                        # Don't use person_bounds st_l/r here as other parent's descendants aren't shown here.
                        self.generation_spread[parent_generation] = [-family_width/2, family_width/2]
                    else:
                        # Every generation of grandparents and above needs to be initialized.
                        # ancestor_sep is added below again.
                        self.generation_spread[parent_generation] = [-grandparent_families_sep/2+ancestor_sep, grandparent_families_sep/2-ancestor_sep]

                if is_parent_family_of_root:
                    # other parents (is_main_parent_family is false here)
                    if alignment != "l": # "c", "r"
                        x_family = self.generation_spread[parent_generation][0] - (other_parent_families_sep + family_width/2) - extra_right
                        self.generation_spread[parent_generation][0] = x_family - family_width/2
                    else: # "l"
                        x_family = self.generation_spread[parent_generation][1] + (other_parent_families_sep + family_width/2) - extra_left
                        self.generation_spread[parent_generation][1] = x_family + family_width/2
                elif x_person < 0:
                    x_family = min(x_person, self.generation_spread[parent_generation][0] - (ancestor_sep + family_width/2) - extra_right)
                    self.generation_spread[parent_generation][0] = x_family - family_width/2
                else:
                    x_family = max(x_person, self.generation_spread[parent_generation][1] + (ancestor_sep + family_width/2) - extra_left)
                    self.generation_spread[parent_generation][1] = x_family + family_width/2

            if not dry_run:
                family_bounds = self.widget_manager.add_family(parent_family_handle, x_family, parent_generation)
            else:
                family_bounds = {"bx_b": 0} # replacement value

            if not dry_run:
                # m is required for siblings and parents so they can share one horizontal line.
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
            else:
                # Replacement value. Not required but something needs to be passed to process_siblings.
                m = None

            if is_main_parent_family:
                # Only the siblings of the main family can be shown.
                if is_parent_family_of_root:
                    # We can show siblings on both sides (true birth order) as spouse's parent's cant be expanded.
                    # TODO When there are expanders for the spouse or to make this work for more generations:
                    # - determine if spouse's parents are expanded
                    # - determine spouse's other families' width
                    # - determine if other parents of children are expanded on that side
                    # Incorporate all into the gap to leave for those when placing the siblings on the side of the spouse.
                    side = "b"
                    which = "b"
                else:
                    if alignment == "l":
                        side = "r"
                    else:
                        side = "l"
                    which = "b"
                person_bounds = self.process_siblings(person_bounds, x_person, person_handle, person_generation, alignment, dry_run, family, x_family, family_bounds["bx_b"], side, which, m)

            x_father = x_family - spouse_sep/2 - person_width/2
            x_mother = x_family + spouse_sep/2 + person_width/2

            if mother_first:
                inner_parent_x = x_mother
                outer_parent_x = x_father
            else:
                inner_parent_x = x_father
                outer_parent_x = x_mother

            inner_parent_bounds = self.process_parent(person_bounds, x_person, alignment, dry_run, parent_generation, person_handle, person_width, parent_family_handle, is_main_parent_family, inner_parent_handle, inner_parent_ahnentafel, inner_parent_alignment, inner_parent_x)

            outer_parent_bounds = self.process_parent(person_bounds, x_person, alignment, dry_run, parent_generation, person_handle, person_width, parent_family_handle, is_main_parent_family, outer_parent_handle, outer_parent_ahnentafel, outer_parent_alignment, outer_parent_x)

            if mother_first:
                new_left = outer_parent_x + outer_parent_bounds[f"gs_l"]
                new_right = inner_parent_x + inner_parent_bounds[f"gs_r"]
            else:
                new_left = inner_parent_x + inner_parent_bounds[f"gs_l"]
                new_right = outer_parent_x + outer_parent_bounds[f"gs_r"]
            self.generation_spread[parent_generation][0] = min(
                self.generation_spread[parent_generation][0],
                new_left
            )
            self.generation_spread[parent_generation][1] = max(
                self.generation_spread[parent_generation][1],
                new_right
            )

            if is_parent_family_of_root:
                # Siblings and other families can expand descendants so they need to move to a free spot wrt existing descendants.
                if mother_first:
                    new_left = outer_parent_x + outer_parent_bounds[f"st_l"]
                    new_right = inner_parent_x + inner_parent_bounds[f"st_r"]
                else:
                    new_left = inner_parent_x + inner_parent_bounds[f"st_l"]
                    new_right = outer_parent_x + outer_parent_bounds[f"st_r"]
                person_bounds["st_l"] = min(person_bounds["st_l"], new_left)
                person_bounds["st_r"] = max(person_bounds["st_r"], new_right)

            if not dry_run:
                # connections between family and spouses
                self.widget_manager.add_connection(
                    inner_parent_x, inner_parent_bounds["bx_b"],
                    inner_parent_x, family_bounds["bx_t"],
                    # very short, no handles
                )
                self.widget_manager.add_connection(
                    outer_parent_x, outer_parent_bounds["bx_b"],
                    outer_parent_x, family_bounds["bx_t"],
                    # very short, no handles
                )

                parent_family = self.dbstate.db.get_family_from_handle(parent_family_handle)
                dashed = self.get_dashed(parent_family, person.handle)

                self.widget_manager.add_connection(
                    family_bounds["x"], family_bounds["bx_b"], x_person, person_bounds["bx_t"],
                    ym=(family_bounds["bx_b"]+person_bounds["bx_t"]-self.canvas_manager.badge_radius)/2,
                    m=m, dashed=dashed, handle1=parent_family_handle, handle2=person.handle
                )
        return person_bounds

    def process_parent(self, person_bounds, x_person, alignment, dry_run, parent_generation, person_handle, person_width, parent_family_handle, is_main_parent_family, this_parent_handle, this_parent_ahnentafel, this_parent_alignment, this_parent_x):
        if this_parent_handle is not None:
            if parent_generation == 1 and is_main_parent_family:
                # Only pass descendent data to root's main parents,
                # generations above and root's other parents cannot show descendants.
                descendant_subtree_bounds = {
                    "st_l": person_bounds["st_l"]+(x_person-this_parent_x),
                    "st_r": person_bounds["st_r"]+(x_person-this_parent_x)
                }
            else:
                descendant_subtree_bounds = None
            if (
                # compare "l", as alignment "c" (e.g. no spouse) is like "r" here
                (alignment == "l") == (this_parent_alignment == "l")
                # only main parents' other families can have descendants which would intersect
                and is_main_parent_family
            ):
                child_handle_with_other_parents_to_collapse = person_handle
            else:
                child_handle_with_other_parents_to_collapse = None
            this_parent_bounds = self.process_person(
                this_parent_handle,
                this_parent_x,
                parent_generation,
                dry_run=dry_run,
                alignment=this_parent_alignment,
                process_families=True,
                process_ancestors=is_main_parent_family,
                process_descendants=parent_generation<=1, # only matters for other parents as skip_family_handle is passed
                ahnentafel=this_parent_ahnentafel,
                descendant_subtree_bounds=descendant_subtree_bounds,
                skip_family_handle=parent_family_handle,
                child_handle_with_other_parents_to_collapse=child_handle_with_other_parents_to_collapse
            )

        else:
            # this parent is missing
            if not dry_run:
                this_parent_bounds = self.add_missing_person(this_parent_x, parent_generation, this_parent_alignment)
            else:
                this_parent_bounds = {"st_l": -person_width/2, "st_r": person_width/2, "gs_l": -person_width/2, "gs_r": person_width/2}
        return this_parent_bounds

    def add_missing_person(self, x_person, person_generation, alignment, dry_run=False):
        person_width = self.canvas_manager.person_width

        person_bounds = {"st_l": 0, "st_r": 0}

        if not dry_run:
            person_box_bounds = self.widget_manager.add_missing_person(x_person, person_generation, alignment)
            person_bounds.update(person_box_bounds)
        person_bounds["st_l"] = -person_width/2
        person_bounds["st_r"] = person_width/2
        person_bounds["gs_l"] = -person_width/2
        person_bounds["gs_r"] = person_width/2

        return person_bounds

    def filter_matches_person_handle(self, handle):
        if self.filtered_person_handles is None:
            # no filtering
            return True
        return handle in self.filtered_person_handles

    def filter_person_handles(self, handles):
        if self.filtered_person_handles is None:
            # no filtering
            return handles
        handles = [
            h for h in handles if (
                h is not None and len(h) > 0
                and h in self.filtered_person_handles
            )
        ]
        return handles

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

    def add_expander(self, x_expander, y_expander, expanded, ang_collapsed, handle, key, collapse_on_expand=None):
        def expander_clicked(root_item, target, event):
            # The fallback False should not be used, because self.expanded.setdefault()[key] = val is used before each call of self.add_expander().
            expand = not self.expanded.get(handle, {}).get(key, False)
            self.expanded.setdefault(handle, {})[key] = expand

            if expand and collapse_on_expand is not None:
                # Collapse all expanders that would cause overlapping lines, etc.
                for handle_, key_ in collapse_on_expand:
                    self.expanded.setdefault(handle_, {})[key_] = False

            offset = self.canvas_manager.get_center_in_units()
            self.ftv.close_info_and_rebuild(self, offset=offset)

        if expanded:
            ang = ang_collapsed + 180
        else:
            ang = ang_collapsed
        self.widget_manager.add_expander(x_expander, y_expander, ang, expander_clicked)

    def add_other_families_expander(self, person_handle, x_person, person_generation, person_is_s1, key, expanded, collapse_on_expand=None):
        person_width = self.canvas_manager.person_width

        # We can't use a button since canvas can be zoomed.
        expander_size = self.canvas_manager.expander_size
        expander_sep = self.canvas_manager.expander_sep
        # Expander for other families always on the outside of the main family:
        x_expander = x_person - (-1+2*person_is_s1)*(person_width/2 + expander_size/2 + expander_sep)
        y_expander = self.get_y_of_generation(person_generation) - expander_size/2
        ang = 0 + person_is_s1*180
        self.add_expander(x_expander, y_expander, expanded, ang, person_handle, key, collapse_on_expand=collapse_on_expand)
