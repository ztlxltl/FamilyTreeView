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

from gi import require_version
require_version("Rsvg", "2.0")
from gi.repository import Gdk, Gtk, Rsvg

from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.datehandler import get_date
from gramps.gen.lib import Person
from gramps.gen.utils.alive import probably_alive
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback, get_marriage_or_fallback, get_divorce_or_fallback
from gramps.gui.utils import color_graph_box

from family_tree_view_icons import get_svg_data
from family_tree_view_utils import get_contrast_color
if TYPE_CHECKING:
    from family_tree_view_widget_manager import FamilyTreeViewWidgetManager


_ = GRAMPS_LOCALE.translation.gettext

class FamilyTreeViewInfoWidgetManager:
    def __init__(self, widget_manager: "FamilyTreeViewWidgetManager"):
        """Super class of info box and panel."""

        self.widget_manager = widget_manager
        self.ftv = widget_manager.ftv
        self.canvas_manager = widget_manager.canvas_manager

        self.grid_column_spacing = 5
        self.grid_row_spacing = 5
        self.widget_manager.add_to_provider("""
            #ftv-small-btn {
                padding: 2px 8px;
            }
            #ftv-tag {
                padding: 5px;
                border-top-left-radius: 10000px;
                border-bottom-left-radius: 10000px;
            }
            #ftv-tag-circle {
                padding: 5px;
                background-color: #ddd;
                border-radius: 5px;
                margin-right: 5px;
            }
        """)

    def create_label_for_grid(self, text=None, markup=None):
        label = Gtk.Label()
        if text is not None:
            label.set_text(text)
        if markup is not None:
            label.set_markup(markup)
        label.set_line_wrap(True)
        label.set_xalign(0) # left align
        label.set_yalign(0) # top align
        return label

    def create_birth_death_label_for_grid(self, person):
        birth_or_fallback = get_birth_or_fallback(self.ftv.dbstate.db, person)
        death_or_fallback = get_death_or_fallback(self.ftv.dbstate.db, person)
        s = ""
        if birth_or_fallback is not None:
            s += f"{self.ftv.get_symbol(birth_or_fallback.type)} {get_date(birth_or_fallback)}"
        if birth_or_fallback is not None and death_or_fallback is not None:
            s += "\n"
        if death_or_fallback is not None:
            s += f"{self.ftv.get_symbol(death_or_fallback.type)} {get_date(death_or_fallback)}"
        return self.create_label_for_grid(s)

    def create_image_widget(self, person, img_width=100, img_height=100):
        image_spec = self.ftv.get_image_spec(person)
        if image_spec[0] == "path":
            image = Gtk.Image.new_from_file(image_spec[1])
        else:
            alive = probably_alive(person, self.ftv.dbstate.db)
            gender = person.get_gender()

            background_color, border_color = color_graph_box(alive, gender)
            data = get_svg_data(image_spec[1], 0, 0, img_width, img_height)
            svg_code = """<svg xmlns="http://www.w3.org/2000/svg">"""
            for d in data:
                svg_code += f"""<path fill="{border_color}" d="{d}" />"""
            svg_code += "</svg>"

            pixbuf = Rsvg.Handle.new_from_data(svg_code.encode()).get_pixbuf()
            image = Gtk.Image.new_from_pixbuf(pixbuf)

        return image

    def create_alt_names_widget(self, person):
        grid = Gtk.Grid()
        grid.set_column_spacing(self.grid_column_spacing)
        grid.set_row_spacing(self.grid_row_spacing)
        alt_names = person.get_alternate_names()
        i_row = 0
        for alt_name in alt_names:
            if alt_name is not None:
                name_type_label = self.create_label_for_grid(f"{_(str(alt_name.get_type()))}:")
                grid.attach(name_type_label, 0, i_row, 1, 1)

                event_data_label = self.create_label_for_grid(self.ftv.name_display.display_name(alt_name))
                grid.attach(event_data_label, 1, i_row, 1, 1)

                i_row += 1
        return grid

    def create_person_base_events_widget(self, person):
        birth_or_fallback = get_birth_or_fallback(self.ftv.dbstate.db, person)
        death_or_fallback = get_death_or_fallback(self.ftv.dbstate.db, person)
        grid = self.create_event_grid([birth_or_fallback, death_or_fallback])
        return grid

    def create_family_base_events_widget(self, family):
        marriage_or_fallback = get_marriage_or_fallback(self.ftv.dbstate.db, family)
        divorce_or_fallback = get_divorce_or_fallback(self.ftv.dbstate.db, family)
        grid = self.create_event_grid([marriage_or_fallback, divorce_or_fallback])
        return grid

    def create_event_grid(self, events):
        grid = Gtk.Grid()
        grid.set_column_spacing(self.grid_column_spacing)
        grid.set_row_spacing(self.grid_row_spacing)

        i_row = 0
        for event in events:
            if event is None:
                continue
            event_type_label = self.create_label_for_grid(markup=f"<b>{_(str(event.type))}</b>")
            grid.attach(event_type_label, 0, i_row, 1, 1)

            place_name = self.ftv.get_full_place_name(event.get_place_handle())
            if place_name is not None:
                event_data_label = self.create_label_for_grid(f"{get_date(event)}\n{place_name}")
                grid.attach(event_data_label, 1, i_row, 1, 1)

            i_row += 1
        return grid

    def create_parent_family_widgets(self, person):
        grids = []
        person_handle = person.get_handle()
        family_handles = person.get_parent_family_handle_list()
        for family_handle in family_handles:
            family = self.ftv.dbstate.db.get_family_from_handle(family_handle)
            if family is None:
                continue
            child_ref = [ref for ref in family.get_child_ref_list() if ref.ref == person_handle][0]
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()

            grid = Gtk.Grid()
            grid.set_column_spacing(self.grid_column_spacing)
            grid.set_row_spacing(self.grid_row_spacing)
            i_row = 0
            for parent_handle, relation in [(father_handle, child_ref.get_father_relation()), (mother_handle, child_ref.get_mother_relation())]:
                parent = self.ftv.get_person_from_handle(parent_handle)
                if parent is None:
                    s =  _("Parent [unknown]")
                elif parent.gender == Person.FEMALE:
                    s = _("Mother")
                elif parent.gender == Person.MALE:
                    s = _("Father")
                else:
                    s =  _("Parent")
                if relation is not None:
                    s += f" ({_(str(relation))})"
                if parent is not None:
                    s += ":"
                parent_type_label = self.create_label_for_grid(s)
                grid.attach(parent_type_label, 0, i_row, 1, 1)

                if parent is not None:
                    parent_name_label = self.create_label_for_grid(self.ftv.name_display.display_name(parent.get_primary_name()))
                    grid.attach(parent_name_label, 1, i_row, 1, 1)

                    parent_dates_label = self.create_birth_death_label_for_grid(parent)
                    grid.attach(parent_dates_label, 2, i_row, 1, 1)

                i_row += 1
            grids.append(grid)
        return grids

    def create_parents_widget(self, family):
        grid = Gtk.Grid()
        grid.set_column_spacing(self.grid_column_spacing)
        grid.set_row_spacing(self.grid_row_spacing)

        father_handle = family.get_father_handle()
        mother_handle = family.get_mother_handle()

        i_row = 0
        for parent_handle in [father_handle, mother_handle]:
            parent = self.ftv.get_person_from_handle(parent_handle)
            if parent is None:
                s =  _("Parent [unknown]")
            elif parent.gender == Person.FEMALE:
                s = _("Mother")
            elif parent.gender == Person.MALE:
                s = _("Father")
            else:
                s =  _("Parent")
            if parent is not None:
                s += ":"
            parent_type_label = self.create_label_for_grid(s)
            grid.attach(parent_type_label, 0, i_row, 1, 1)

            if parent is not None:
                parent_name_label = self.create_label_for_grid(self.ftv.name_display.display_name(parent.get_primary_name()))
                grid.attach(parent_name_label, 1, i_row, 1, 1)

                parent_dates_label = self.create_birth_death_label_for_grid(parent)
                grid.attach(parent_dates_label, 2, i_row, 1, 1)

            i_row += 1
        return grid

    def create_children_widget(self, family):
        grid = Gtk.Grid()
        grid.set_column_spacing(self.grid_column_spacing)
        grid.set_row_spacing(self.grid_row_spacing)

        i_row = 0
        for child_ref in family.get_child_ref_list():
            child_handle = child_ref.ref
            child = self.ftv.get_person_from_handle(child_handle)
            if child.gender == Person.FEMALE:
                s = _("Daughter")
            elif child.gender == Person.MALE:
                s = _("Son")
            else:
                s =  _("Child")
            father_relation = child_ref.get_father_relation()
            mother_relation = child_ref.get_mother_relation()
            if father_relation is not None or mother_relation is not None:
                if father_relation is None:
                    father_relation = _("unspecified")
                if mother_relation is None:
                    mother_relation = _("unspecified")
                s += f"\n({_(str(father_relation))}, {_(str(mother_relation))})"
            s += ":"
            child_type_label = self.create_label_for_grid(s)
            grid.attach(child_type_label, 0, i_row, 1, 1)

            child_name_label = self.create_label_for_grid(self.ftv.name_display.display_name(child.get_primary_name()))
            grid.attach(child_name_label, 1, i_row, 1, 1)

            child_dates_label = self.create_birth_death_label_for_grid(child)
            grid.attach(child_dates_label, 2, i_row, 1, 1)

            i_row += 1
        return grid

    def create_person_buttons_widget(self, person_handle, panel_button=True):
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        edit_button = self.create_button("Edit", icon="gtk-edit")
        edit_button.connect("clicked", lambda *_: self.ftv.edit_person(person_handle))
        buttons.pack_start(edit_button, False, False, 0)

        set_home_button = self.create_button("Set home", icon="go-home")
        home_person = self.ftv.dbstate.db.get_default_person()
        if home_person is not None:
            set_home_button.set_sensitive(home_person.handle!=person_handle)
        set_home_button.connect("clicked", lambda *_: self.ftv.set_home_person(person_handle, also_set_active=False))
        buttons.pack_start(set_home_button, False, False, 0)

        set_active_button = self.create_button("Set active", char="\u2794") # rightwards arrow
        set_active_button.set_sensitive(self.ftv.get_active() != person_handle)
        offset = None # TODO
        set_active_button.connect("clicked", lambda *_: self.ftv.set_active_person(person_handle, offset=offset))
        buttons.pack_start(set_active_button, False, False, 0)

        if panel_button:
            open_panel_button = self.create_button("Open panel", char="\u25e8") # Square with right half black
            open_panel_button.connect("clicked", lambda*_: self.widget_manager.panel_manager.open_person_panel(person_handle))
            buttons.pack_start(open_panel_button, False, False, 0)

        add_relative_button = self.create_button("Add relative", icon="list-add")
        add_relative_button.set_sensitive(False)
        buttons.pack_start(add_relative_button, False, False, 0)

        return buttons

    def create_family_buttons_widget(self, family_handle, panel_button=True):

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        edit_button = self.create_button("Edit", icon="gtk-edit")
        edit_button.connect("clicked", lambda *_: self.ftv.edit_family(family_handle))
        buttons.pack_start(edit_button, False, False, 0)

        if self.ftv._config.get("interaction.familytreeview-family-info-box-set-active-button"):
            set_active_button = self.create_button("Set active", char="\u2794") # rightwards arrow
            set_active_button.set_sensitive(self.ftv.get_active_family() != family_handle)
            set_active_button.connect("clicked", lambda *_: self.ftv.set_active_family(family_handle))
            buttons.pack_start(set_active_button, False, False, 0)

        if panel_button:
            open_panel_button = self.create_button("Open panel", char="\u25e8") # Square with Right Half Black
            open_panel_button.connect("clicked", lambda*_: self.widget_manager.panel_manager.open_family_panel(family_handle))
            buttons.pack_start(open_panel_button, False, False, 0)

        add_relative_button = self.create_button("Add relative", icon="list-add")
        add_relative_button.set_sensitive(False)
        buttons.pack_start(add_relative_button, False, False, 0)

        return buttons

    def create_button(self, label, icon=None, char=None):
        button = Gtk.Button()
        button.set_name("ftv-small-btn")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        if icon is not None:
            image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR)
            box.pack_start(image, False, False, 0)

        if char is not None:
            char_label = Gtk.Label()
            char_label.set_markup(f"<big>{char}</big>")
            box.pack_start(char_label, False, False, 0)

        label = Gtk.Label(label)
        label.set_line_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)

        box.pack_start(label, False, False, 0)
        button.add(box)
        return button

    def create_tags_widget(self, obj):
        tags_flow = Gtk.FlowBox()
        tags_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        tag_handle_list = obj.get_tag_list()
        for tag_handle in tag_handle_list:
            tag = self.ftv.dbstate.db.get_tag_from_handle(tag_handle)
            tag_widget = Gtk.Box()
            tag_widget.set_name("ftv-tag")
            tag_widget.set_halign(Gtk.Align.START)

            # background color
            rgba_bg = Gdk.RGBA()
            rgba_bg.parse(tag.get_color())
            tag_widget.override_background_color(Gtk.StateFlags.NORMAL, rgba_bg)

            # text color
            rgba = Gdk.RGBA()
            rgba.parse(get_contrast_color(rgba_bg))
            tag_widget.override_color(Gtk.StateFlags.NORMAL, rgba)

            # hole
            circle_widget = Gtk.Box()
            circle_widget.set_name("ftv-tag-circle")
            circle_widget.set_vexpand(False)
            circle_widget.set_valign(Gtk.Align.CENTER)
            tag_widget.add(circle_widget)

            # text
            label_widget = Gtk.Label(tag.get_name())
            tag_widget.add(label_widget)

            tags_flow.add(tag_widget)
        return tags_flow

    def create_attributes(self, obj):
        grid = Gtk.Grid()
        grid.set_column_spacing(self.grid_column_spacing)
        grid.set_row_spacing(self.grid_row_spacing)

        i_row = 0
        for attr in obj.get_attribute_list():
            if attr is None:
                continue
            attr_type_label = self.create_label_for_grid(_(str(attr.get_type())))
            grid.attach(attr_type_label, 0, i_row, 1, 1)

            attr_value_label = self.create_label_for_grid(attr.get_value())
            grid.attach(attr_value_label, 1, i_row, 1, 1)

            i_row += 1
        return grid