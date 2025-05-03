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


from gi.repository import Gtk

from gramps.gen.display.name import displayer as name_displayer

from family_tree_view_info_widget_manager import FamilyTreeViewInfoWidgetManager
from family_tree_view_timeline import FamilyTreeViewTimeline
from family_tree_view_utils import get_gettext, import_GooCanvas


GooCanvas = import_GooCanvas()

_ = get_gettext()

class FamilyTreeViewPanelManager(FamilyTreeViewInfoWidgetManager):
    def __init__(self, widget_manager):
        super().__init__(widget_manager)

        self.spacing = 10
        self.margin = 5

        self.panel_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.panel_widget.add(self.create_panel_header())
        self.panel_scrolled = Gtk.ScrolledWindow(propagate_natural_width=True, propagate_natural_height=True)
        self.panel_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.panel_content.set_margin_top(self.margin)
        self.panel_content.set_margin_start(self.margin)
        self.panel_content.set_margin_end(self.margin)
        self.panel_content.set_margin_bottom(self.margin)
        self.panel_content.set_spacing(self.spacing)
        self.panel_scrolled.add(self.panel_content)
        self.panel_widget.add(self.panel_scrolled)

        self.displayed_object = None

    def create_panel_header(self):
        panel_header_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.END)

        image = Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.LARGE_TOOLBAR)
        close_button = Gtk.Button(image=image)
        close_button.connect("clicked", lambda button: self.widget_manager.close_panel())
        panel_header.add(close_button)

        panel_header_container.add(panel_header)
        panel_header_container.add(Gtk.Separator())
        return panel_header_container

    def reset_panel(self):
        for child in self.panel_content.get_children():
            self.panel_content.remove(child)
        self.displayed_object = None

    def open_person_panel(self, person_handle, x_person, generation):
        self.reset_panel()

        person = self.ftv.get_person_from_handle(person_handle)
        name_str = name_displayer.display_name(person.get_primary_name())

        overview_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overview_section.set_spacing(self.spacing)

        base_info = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        base_info.set_spacing(self.spacing)
        image = self.create_image_widget(person)
        if image is not None:
            base_info.add(image)
        names = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        names.set_spacing(self.spacing)
        name = Gtk.Label()
        name.set_markup(f"<big><b>{name_str}</b></big>") # TODO size
        name.set_line_wrap(True)
        name.set_xalign(0)
        names.add(name)
        alt_names = self.create_alt_names_widget(person)
        names.add(alt_names)
        base_info.add(names)
        overview_section.add(base_info)
        main_events = self.create_person_base_events_widget(person)
        overview_section.add(main_events)

        families = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        families.set_spacing(self.spacing)
        for family_grid in self.create_parent_family_widgets(person):
            families.add(family_grid)
        overview_section.add(families)
        self.panel_content.add(overview_section)

        buttons = self.create_person_buttons_widget(person_handle, x_person, generation, panel_button=False)
        self.panel_content.add(buttons)

        self.panel_content.add(Gtk.Separator())

        tags_expander = Gtk.Expander(label=_("Tags"))
        tags_expander.set_expanded(True)
        tags_section = self.create_tags_widget(person)
        tags_expander.add(tags_section)
        self.panel_content.add(tags_expander)

        self.panel_content.add(Gtk.Separator())

        timeline_expander = Gtk.Expander(label=_("Timeline"))
        timeline_expander.set_expanded(True)
        timeline = FamilyTreeViewTimeline(self.widget_manager, person, self.panel_scrolled)
        timeline_expander.add(timeline.main_widget_container)
        self.panel_content.add(timeline_expander)

        self.panel_content.add(Gtk.Separator())

        gallery_expander = Gtk.Expander(label=_("Gallery"))
        gallery_expander.set_expanded(True)
        gallery_section = self.create_gallery(person)
        gallery_expander.add(gallery_section)
        self.panel_content.add(gallery_expander)

        self.panel_content.add(Gtk.Separator())

        attributes_expander = Gtk.Expander(label=_("Attributes"))
        attributes_expander.set_expanded(True)
        attributes_section = self.create_attributes(person)
        attributes_expander.add(attributes_section)
        self.panel_content.add(attributes_expander)

        self.widget_manager.show_panel()

        self.displayed_object = ("person", person_handle)

        return True

    def open_family_panel(self, family_handle, x_family, generation):
        self.reset_panel()

        family = self.ftv.dbstate.db.get_family_from_handle(family_handle)

        main_events = self.create_family_base_events_widget(family)
        self.panel_content.add(main_events)

        parents_grid = self.create_parents_widget(family)
        self.panel_content.add(parents_grid)

        children_grid = self.create_children_widget(family)
        self.panel_content.add(children_grid)

        buttons = self.create_family_buttons_widget(family_handle, x_family, generation, panel_button=False)
        self.panel_content.add(buttons)

        tags = self.create_tags_widget(family)
        self.panel_content.add(tags)

        self.panel_content.add(Gtk.Separator())

        timeline_expander = Gtk.Expander(label=_("Timeline"))
        timeline_expander.set_expanded(True)
        timeline = FamilyTreeViewTimeline(self.widget_manager, family, self.panel_scrolled)
        timeline_expander.add(timeline.main_widget_container)
        self.panel_content.add(timeline_expander)

        self.panel_content.add(Gtk.Separator())

        attributes_expander = Gtk.Expander(label=_("Attributes"))
        attributes_expander.set_expanded(True)
        attributes_section = self.create_attributes(family)
        attributes_expander.add(attributes_section)
        self.panel_content.add(attributes_expander)

        self.widget_manager.show_panel()

        self.displayed_object = ("family", family_handle)

        return True
