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

from gi.repository import GLib, Gtk, Pango

from gramps.gen.config import config
from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.datehandler import get_date
from gramps.gen.lib.eventroletype import EventRoleType
from gramps.gen.lib.family import Family
from gramps.gen.lib.person import Person
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback, get_marriage_or_fallback, get_divorce_or_fallback

from family_tree_view_utils import calculate_min_max_age_at_event, get_label_line_height, import_GooCanvas
if TYPE_CHECKING:
    from family_tree_view_widget_manager import FamilyTreeViewWidgetManager


GooCanvas = import_GooCanvas()

_ = GRAMPS_LOCALE.translation.gettext

DAYS_PER_YEAR = 365.2425 # on average in Gregorian calendar
DAYS_PER_MONTH = DAYS_PER_YEAR / 12; # on average
DAYS_PER_WEEK = 7
UNIT_LIST = [
    (1, 1, _("age in days"), _("time in days")),
    (1, 2, _("age in days"), _("time in days")),
    (1, 5, _("age in days"), _("time in days")),
    (1/DAYS_PER_WEEK, 1, _("age in weeks"), _("time in weeks")),
    (1/DAYS_PER_WEEK, 2, _("age in weeks"), _("time in weeks")),
    (1/DAYS_PER_MONTH, 1, _("age in ~months"), _("time in ~months")), # ~ since 1/12th year is used, not 1 month
    (1/DAYS_PER_MONTH, 3, _("age in ~months"), _("time in ~months")),
    (1/DAYS_PER_MONTH, 6, _("age in ~months"), _("time in ~months")),
    (1/DAYS_PER_YEAR, 1, _("age in years"), _("time in years")),
    (1/DAYS_PER_YEAR, 2, _("age in years"), _("time in years")),
    (1/DAYS_PER_YEAR, 5, _("age in years"), _("time in years")),
    (1/DAYS_PER_YEAR, 10, _("age in years"), _("time in years")),
    (1/DAYS_PER_YEAR, 20, _("age in years"), _("time in years")),
    (1/DAYS_PER_YEAR, 50, _("age in years"), _("time in years")),
    (1/DAYS_PER_YEAR, 100, _("age in years"), _("time in years"))
]

class FamilyTreeViewTimeline:
    def __init__(self, widget_manager: "FamilyTreeViewWidgetManager", obj, scroll_window):
        self.widget_manager = widget_manager
        self.ftv = self.widget_manager.ftv
        self.obj = obj
        self.scroll_window = scroll_window

        self.event_margin = 8
        self.event_margin_right = 3
        self.event_padding = 8

        self.widget_manager.add_to_provider(f"""
            .ftv-timeline-event-own {{
                background-color: #FFF;
                margin: {self.event_margin}px {self.event_margin_right}px {self.event_margin}px {self.event_margin}px;
                border-radius: 5px;
                padding: {self.event_padding}px;
                box-shadow: 0 0 5px 0 rgba(0, 0, 0, 0.5);
            }}
            .ftv-timeline-event-relatives {{
                background-color: #EEE;
                margin: {self.event_margin}px {self.event_margin_right}px {self.event_margin}px {self.event_margin}px;
                border-radius: 5px;
                padding: {self.event_padding}px;
                box-shadow: inset 0 0 5px 0 rgba(0, 0, 0, 0.5);
            }}
        """)

        if isinstance(self.obj, Person):
            self.obj_type = "P"
            self.start_event = get_birth_or_fallback(self.ftv.dbstate.db, self.obj)
            self.end_event = get_death_or_fallback(self.ftv.dbstate.db, self.obj)
            self.primary_event_ref_list = [
                (None, (), ref) # None marks primary event
                for ref in self.obj.get_primary_event_ref_list()
            ]
            self.non_primary_event_ref_list = [
                ("self", (self.obj,), ref)
                for ref in self.obj.get_event_ref_list()
                if ref.get_role() != EventRoleType.PRIMARY
            ]
            def ref_will_be_on_timeline(ref):
                event = self.ftv.dbstate.db.get_event_from_handle(ref.ref)
                # These must be the same criteria as in the final filtering.
                return (
                    not event.date.is_empty()
                    and self.start_event.date.get_sort_value() <= event.date.get_sort_value()
                    and event.date.get_sort_value() <= self.end_event.date.get_sort_value()
                )
            has_non_primary_events = any(
                ref.get_role() != EventRoleType.PRIMARY
                for ref in self.obj.get_event_ref_list()
                if ref_will_be_on_timeline(ref)
            )
            timeline_mode_idx = self.ftv._config.get("appearance.familytreeview-timeline-mode-default-person")
            if has_non_primary_events:
                self.timeline_modes = [
                    "Primary own events",
                    "All own events",
                    "Primary own and relatives' events",
                    "All own and relatives' events"
                ]
            else:
                self.timeline_modes = [
                    "Own events",
                    "Own and relatives' events"
                ]
                timeline_mode_idx //= 2
        elif isinstance(self.obj, Family):
            self.obj_type = "F"
            self.start_event = get_marriage_or_fallback(self.ftv.dbstate.db, self.obj)
            self.end_event = get_divorce_or_fallback(self.ftv.dbstate.db, self.obj)
            self.primary_event_ref_list = [
                (None, (), ref) # None marks primary event
                for ref in self.obj.get_event_ref_list()
            ]
            self.timeline_modes = [
                "Family events",
                "Family and parents' event",
                "Family and children's events",
                "Family, parents' and children's events"
            ]
            timeline_mode_idx = self.ftv._config.get("appearance.familytreeview-timeline-mode-default-family")
        else:
            raise ValueError("obj needs to be a Person or a Family")

        self.timeline_mode = self.timeline_modes[timeline_mode_idx]

        self.timeline_canvas_width = 120
        self.timeline_time_marker_x = 35 # enough margin for tick labels
        self.timeline_event_marker_x = self.timeline_canvas_width - 10
        self.timeline_top_margin = 30 # enough for time unit
        self.timeline_bottom_margin = self.event_margin + self.event_padding + 5 # ca. mid of last line of last event
        self.timeline_marker_radius = 2

        self.main_widget_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        mode_store = Gtk.ListStore(str, str)
        for mode in self.timeline_modes:
            mode_store.append([mode, _(mode)])
        mode_combo = Gtk.ComboBox.new_with_model(mode_store)
        renderer = Gtk.CellRendererText()
        mode_combo.pack_start(renderer, True)
        mode_combo.add_attribute(renderer, "text", 1)
        mode_combo.set_active(timeline_mode_idx)
        mode_combo.connect("scroll-event", self.propagate_to_panel) # don't scroll combo
        self.main_widget_container.add(mode_combo)

        self.main_widget = None
        self.create_timeline()

        mode_combo.connect("changed", self.timeline_mode_changed)

    def propagate_to_panel(self, widget, event):
        Gtk.propagate_event(self.scroll_window, event)
        return True

    def reset_timeline(self):
        if self.main_widget is not None:
            self.main_widget.destroy()
            self.main_widget = None

    def create_timeline(self):
        if self.obj_type == "P":
            if "Primary own" in self.timeline_mode or "Own" in self.timeline_mode:
                event_ref_list = []
            elif "All own" in self.timeline_mode:
                event_ref_list = self.non_primary_event_ref_list.copy()
            if "relatives' events" in self.timeline_mode:
                # all families where person is spouse and all families where person is child
                family_handles = (
                    [(False, family_handle) for family_handle in self.obj.get_family_handle_list()]
                    + [(True, family_handle) for family_handle in self.obj.get_parent_family_handle_list()]
                )
                for is_parent_family, family_handle in family_handles:
                    # family
                    family = self.ftv.dbstate.db.get_family_from_handle(family_handle)
                    event_ref_list += [
                        ("parent family" if is_parent_family else "family", (self.obj, family), ref)
                        for ref in family.get_event_ref_list()
                    ]
                    # parents
                    for parent_handle in [family.get_father_handle(), family.get_mother_handle()]:
                        if parent_handle is not None and parent_handle != self.obj.get_handle():
                            parent = self.ftv.get_person_from_handle(parent_handle)
                            event_ref_list += [
                                ("parent" if is_parent_family else "spouse", (self.obj, family, parent), ref)
                                for ref in parent.get_primary_event_ref_list()
                            ]
                    # children / siblings
                    for child_ref in family.get_child_ref_list():
                        child_handle = child_ref.ref
                        if child_handle is not None and child_handle != self.obj.get_handle(): # only siblings
                            child = self.ftv.get_person_from_handle(child_handle)
                            event_ref_list += [
                                ("sibling" if is_parent_family else "child", (self.obj, family, child), ref)
                                for ref in child.get_primary_event_ref_list()
                            ]

        elif self.obj_type == "F":
            event_ref_list = []
            if "parents'" in self.timeline_mode:
                for parent_handle in [self.obj.get_father_handle(), self.obj.get_mother_handle()]:
                    if parent_handle is not None and parent_handle != self.obj.get_handle():
                        parent = self.ftv.get_person_from_handle(parent_handle)
                        event_ref_list += [
                            ("spouse", (self.obj, parent), ref)
                            for ref in parent.get_primary_event_ref_list()
                        ]
            if "children's" in self.timeline_mode:
                for child_ref in self.obj.get_child_ref_list():
                    child_handle = child_ref.ref
                    if child_handle is not None and child_handle != self.obj.get_handle(): # only siblings
                        child = self.ftv.get_person_from_handle(child_handle)
                        event_ref_list +=[
                            ("child", (self.obj, child), ref)
                            for ref in child.get_primary_event_ref_list()
                        ]

        primary_event_and_ref_list = [
            (rel_type, rel, self.ftv.dbstate.db.get_event_from_handle(ref.ref), ref)
            for rel_type, rel, ref in self.primary_event_ref_list
        ]
        event_and_ref_list = [
            (rel_type, rel, self.ftv.dbstate.db.get_event_from_handle(ref.ref), ref)
            for rel_type, rel, ref in event_ref_list
        ]

        event_and_ref_list = primary_event_and_ref_list + event_and_ref_list
        event_and_ref_list.sort(key=lambda e: e[2].date.get_sort_value()) # 2: event

        # NOTE: These must be the same criteria as in the initial filtering in ref_will_be_on_timeline.
        # remove events without dates
        event_and_ref_list = [
            (rel_type, rel, event, ref)
            for rel_type, rel, event, ref in event_and_ref_list
            if not event.date.is_empty()
        ]

        # Remove non-primary events before birth and after death.
        if self.obj_type == "P":
            if self.start_event is not None:
                event_and_ref_list = [
                    (rel_type, rel, event, ref)
                    for rel_type, rel, event, ref in event_and_ref_list
                    if (
                        self.start_event.date.get_sort_value() <= event.date.get_sort_value()
                        or rel_type is None # keep all primary events
                    )
                ]
            if self.end_event is not None:
                event_and_ref_list = [
                    (rel_type, rel, event, ref)
                    for rel_type, rel, event, ref in event_and_ref_list
                    if (
                        event.date.get_sort_value() <= self.end_event.date.get_sort_value()
                        or rel_type is None # keep all primary events
                    )
                ]

        self.main_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        if len(event_and_ref_list) == 0:
            self.main_widget.add(Gtk.Label(_("No timeline to show.")))
            return self.main_widget

        timeline_canvas = GooCanvas.Canvas()
        # Bounds are set by self.draw_timeline.
        timeline_canvas.set_size_request(self.timeline_canvas_width, -1) # only width, height unset

        timeline_label_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        calendar = config.get("preferences.calendar-format-report")
        short_age = self.ftv._config.get("appearance.familytreeview-timeline-short-age")
        if not short_age:
            age_precision = age_precision = config.get("preferences.age-display-precision")

        event_labels = []
        for i, (rel_type, rel, event, ref) in enumerate(event_and_ref_list):
            if event is None:
                continue
            event_age_str = ""
            if self.start_event is not None:
                if short_age:
                    min_max_age = calculate_min_max_age_at_event(self.start_event, event, calendar)
                    if min_max_age is not None:
                        min_age, max_age = min_max_age
                        if min_age == max_age:
                            age = str(min_age)
                        else:
                            age = f"{min_age} - {max_age}"
                        event_age_str = f"({age}) "
                else:
                    age_str = (event.date - self.start_event.date).format(precision=age_precision)
                    event_age_str = f"({age_str}) "
            event_type = _(str(event.type))
            event_date_str = get_date(event)
            event_place_str = self.ftv.get_full_place_name_from_event(event)
            if event_place_str is None: # no place
                event_place_str = ""
            else:
                event_place_str = ",\n" + event_place_str

            if rel_type is None: # primary event
                markup = f"{event_age_str}<b>{event_type}</b>:\n{event_date_str}{event_place_str}"
                class_name = "ftv-timeline-event-own"
            else:
                # We could also use find_backlink_handles,
                # but it would require extra steps to get the primary person
                # if there are multiple persons.
                # TODO "step-", "half-" using relationship
                relationship_type = rel_type
                if relationship_type == "parent":
                    if rel[-1].get_gender() == Person.FEMALE:
                        relationship_type = "mother"
                    elif rel[-1].get_gender() == Person.MALE:
                        relationship_type = "father"
                elif relationship_type == "sibling":
                    if rel[-1].get_gender() == Person.FEMALE:
                        relationship_type = "sister"
                    elif rel[-1].get_gender() == Person.MALE:
                        relationship_type = "brother"
                elif relationship_type == "child":
                    if rel[-1].get_gender() == Person.FEMALE:
                        relationship_type = "daughter"
                    elif rel[-1].get_gender() == Person.MALE:
                        relationship_type = "son"
                elif relationship_type == "spouse":
                    if rel[-1].get_gender() == Person.FEMALE:
                        relationship_type = "wife"
                    elif rel[-1].get_gender() == Person.MALE:
                        relationship_type = "husband"
                if isinstance(rel[-1], Person):
                    relative_name = self.ftv.name_display.display_name(rel[-1].get_primary_name())
                    markup = f"{event_age_str}{event_type} of {relationship_type} <b>{relative_name}</b>:\n{event_date_str}{event_place_str}"
                else:
                    markup = f"{event_age_str}{event_type} of <b>{relationship_type}</b>:\n{event_date_str}{event_place_str}"
                class_name = "ftv-timeline-event-relatives"
            event_label = Gtk.Label()
            event_label.set_markup(markup)
            event_label.set_line_wrap(True)
            event_label.set_xalign(0) # left align
            event_label.get_style_context().add_class(class_name)
            if i == 0:
                event_label.set_margin_top(
                    self.timeline_top_margin
                    - (self.event_margin + self.event_padding)
                    - get_label_line_height(event_label)/2
                )
            event_labels.append(event_label)
            timeline_label_container.add(event_label)

        self.main_widget.connect("size-allocate", lambda timeline_section, allocation:
            self.timeline_section_size_allocate(timeline_section, allocation, event_and_ref_list, timeline_canvas, event_labels)
        )

        self.main_widget.pack_start(timeline_canvas, False, False, 0) # don't expand, timeline canvas should have constant width
        self.main_widget.pack_start(timeline_label_container, True, True, 0)

        timeline_canvas.connect("scroll-event", self.propagate_to_panel)

        self.main_widget_container.add(self.main_widget)

    def timeline_section_size_allocate(self, timeline_section, allocation, event_and_ref_list, timeline_canvas, event_labels):
        GLib.idle_add(self.draw_timeline, event_and_ref_list, timeline_canvas, event_labels)

    def timeline_mode_changed(self, mode_combo):
        active_iter = mode_combo.get_active_iter()
        if active_iter is None:
            return

        model = mode_combo.get_model()
        mode = model[active_iter][0] # 0: non-translated
        self.timeline_mode = mode
        self.reset_timeline()
        self.create_timeline()
        self.main_widget_container.show_all()

    def draw_timeline(self, event_and_ref_list, timeline_canvas, event_labels):
        if self.obj is None or len(event_and_ref_list) == 0:
            return

        if self.start_event is None:
            return

        root_item = timeline_canvas.get_root_item()

        # TODO only ticks if there is a birth or replacement

        # remove all canvas elements
        for i in range(root_item.get_n_children()-1, -1, -1):
            root_item.remove_child(i)

        canvas_allocation = timeline_canvas.get_allocation()
        canvas_height = canvas_allocation.height
        timeline_canvas.set_bounds(0, 0, canvas_allocation.width, canvas_allocation.height)

        event_sort_values = [event.date.get_sort_value() for rel_type, rel, event, ref in event_and_ref_list]
        min_sort_values = min(event_sort_values)
        max_sort_values = max(event_sort_values)
        num_days = max_sort_values - min_sort_values
        pos_num_days = max_sort_values - self.start_event.date.get_sort_value()
        timeline_height = canvas_height - self.timeline_top_margin - self.timeline_bottom_margin
        if num_days == 0 or pos_num_days == 0 or timeline_height == 0:
            pos_timeline_height = timeline_height
            num_ticks = 1
            tick_dist = 0
            tick_unit_factor = 0
            if self.obj_type == "P":
                tick_unit_name = _("age in years")
            elif self.obj_type == "F":
                tick_unit_name = _("time in years")
        else:
            # timeline line
            self.draw_line(
                root_item,
                self.timeline_time_marker_x, self.timeline_top_margin,
                self.timeline_time_marker_x, canvas_height-self.timeline_bottom_margin
            )

            # timeline ticks
            pos_timeline_height = pos_num_days / num_days * timeline_height
            if pos_timeline_height == 0:
                return
            min_tick_dist = 50 # TODO 5*font_size
            # determine best tick interval
            num_ticks = 0
            while True:
                # get the first tick unit whose ticks are far enough apart
                for i in range(len(UNIT_LIST)):
                    num_base_units, unit_factor, unit_name_years, unit_name_time = UNIT_LIST[i]
                    num_base_units *= num_days
                    num_ticks = num_base_units / unit_factor
                    tick_dist = pos_timeline_height / num_ticks
                    if tick_dist >= min_tick_dist or i == len(UNIT_LIST)-1:
                        tick_unit_factor = unit_factor
                        if self.obj_type == "P":
                            tick_unit_name = unit_name_years
                        elif self.obj_type == "F":
                            tick_unit_name = unit_name_time
                        break
                num_ticks = round(pos_timeline_height/tick_dist-0.5) + 1; # + 1 for tick at 0
                # decrease tick interval if too few ticks
                if num_ticks >= 2:
                    break
                else:
                    if min_tick_dist/2 <= 5: # threshold: line height
                        break
                    min_tick_dist /= 2

        tick_length = 8
        x_tick = self.timeline_time_marker_x - tick_length*3/2
        zero_event_offset = timeline_height - pos_timeline_height
        for i_tick in range(num_ticks):
            y_tick = tick_dist * i_tick + self.timeline_top_margin + zero_event_offset
            self.draw_line(
                root_item,
                self.timeline_time_marker_x-tick_length, y_tick,
                self.timeline_time_marker_x, y_tick
            )

            font_desc = self.main_widget_container.get_style_context().get_font(Gtk.StateFlags.NORMAL)
            tick_label = GooCanvas.CanvasText(
                parent=root_item,
                x=x_tick,
                y=y_tick,
                text=f"{i_tick*tick_unit_factor}",
                alignment=Pango.Alignment.RIGHT,
                anchor=GooCanvas.CanvasAnchorType.EAST,
                width=self.timeline_time_marker_x,
                font_desc=font_desc
            )
            if i_tick == 0:
                ink_extend_rect, logical_extend_rect =  tick_label.get_natural_extents()
                Pango.extents_to_pixels(logical_extend_rect)
                GooCanvas.CanvasText(
                    parent=root_item,
                    x=x_tick - logical_extend_rect.width, # left align to tick_label
                    y=self.timeline_top_margin - logical_extend_rect.height/2, # line above (in case there is a 0 at the first event)
                    text=tick_unit_name,
                    alignment=Pango.Alignment.LEFT,
                    anchor=GooCanvas.CanvasAnchorType.SOUTH_WEST,
                    font_desc=font_desc
                )

        prev_y_time = None
        prev_first_line_center = None
        for i, (event_sort_value, event_label) in enumerate(zip(event_sort_values, event_labels)):
            try:
                y_time_rel = (event_sort_value - min_sort_values) / (max_sort_values - min_sort_values)
            except ZeroDivisionError:
                y_time_rel = 0
            y_time = y_time_rel * timeline_height + self.timeline_top_margin

            connect_to_previous = prev_y_time is not None and y_time - prev_y_time < 2*self.timeline_marker_radius

            if not connect_to_previous:
                GooCanvas.CanvasEllipse(
                    parent=root_item,
                    center_x=self.timeline_time_marker_x,
                    center_y=y_time,
                    radius_x=self.timeline_marker_radius,
                    radius_y=self.timeline_marker_radius,
                    fill_color="#000"
                )

            label_allocation = event_label.get_allocation()
            logical_extend_rect = get_label_line_height(event_label)
            first_line_height = logical_extend_rect
            first_line_center = label_allocation.y - canvas_allocation.y + self.event_margin + self.event_padding + first_line_height/2

            GooCanvas.CanvasEllipse(
                parent=root_item,
                center_x=self.timeline_event_marker_x,
                center_y=first_line_center,
                radius_x=self.timeline_marker_radius,
                radius_y=self.timeline_marker_radius,
                fill_color="#000"
            )

            # connecting line
            if connect_to_previous:
                self.draw_line(
                    root_item,
                    self.timeline_event_marker_x, prev_first_line_center,
                    self.timeline_event_marker_x, first_line_center
                )
            else:
                self.draw_line(
                    root_item,
                    self.timeline_time_marker_x, y_time,
                    self.timeline_event_marker_x, first_line_center
                )

            if not connect_to_previous:
                prev_y_time = y_time
            prev_first_line_center = first_line_center

    def draw_line(self, parent, x1, y1, x2, y2):
        data = f"""
            M {x1} {y1}
            L {x2} {y2}
        """
        GooCanvas.CanvasPath(
            parent=parent,
            data=data
        )