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

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from gramps.gen.datehandler import get_date
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.lib import Person
from gramps.gen.utils.alive import probably_alive
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback, get_marriage_or_fallback, get_divorce_or_fallback
from gramps.gen.utils.file import media_path_full
from gramps.gen.utils.thumbnails import get_thumbnail_image
from gramps.gui.utils import color_graph_box
from gramps.gui.widgets import Photo

from family_tree_view_utils import get_contrast_color, get_gettext
if TYPE_CHECKING:
    from family_tree_view_widget_manager import FamilyTreeViewWidgetManager


_ = get_gettext()

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
                background-color: @theme_bg_color;
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

    def create_person_name_label_for_grid(self, person):
        uri = f"gramps://Person/handle/{person.handle}"
        name = name_displayer.display_name(person.get_primary_name())
        label = self.create_label_for_grid(markup=
            name
            + f" <a href=\"{uri}\" title=\""
            + _("Set {name} as active person").format(name=name)
            + "\">\u2794</a>" # rightwards arrow
        )
        # TODO Increase font size of arrow without changing line height.
        # Tried to increase the size of the error with
        # <big><big><big><span line_height=\"{1/1.2**3}\">...</span></big></big></big>
        # but the line height wasn't correct, even though <big> scales
        # by 1.2.
        label.connect("activate-link", lambda label, uri:
            self.ftv.open_uri(uri)
        )
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

    def create_image_widget(self, obj, img_width=100, img_height=100, obj_type="person", only_media=False):
        image_spec = self.ftv.get_image_spec(obj, obj_type)
        if image_spec[0] in ["path", "pixbuf"]:
            color = None
        elif only_media:
            # If not a path or pixbuf is available and only media is
            # requested (no avatar), return None.
            return None
        elif obj_type == "person":
            alive = probably_alive(obj, self.ftv.dbstate.db)
            gender = obj.get_gender()
            _, color = color_graph_box(alive, gender)
        else: # "family"
            color = "#000" # black
        return self.create_image_from_image_spec(image_spec, img_width, img_height, color=color)

    def create_image_from_image_spec(self, image_spec, img_width, img_height, color=None):
        if image_spec[0] in ["path", "svg_path", "pixbuf"]:
            if image_spec[0] == "path":
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(image_spec[1])
            elif image_spec[0] == "svg_path":
                svg_factor = 16 # if 1: too pixelated, if too large: slow
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(image_spec[1], img_width*svg_factor, img_height*svg_factor)
            else:
                pixbuf = image_spec[1]
            scale = min(
                img_width / pixbuf.get_width(),
                img_height / pixbuf.get_height(),
            )
            pixbuf = pixbuf.scale_simple(
                round(pixbuf.get_width() * scale),
                round(pixbuf.get_height() * scale),
                GdkPixbuf.InterpType.BILINEAR
            )
            image = Gtk.Image.new_from_pixbuf(pixbuf)
        else: # svg_data_callback
            data, width, height = image_spec[1](img_width, img_height)
            svg_code = """<svg xmlns="http://www.w3.org/2000/svg">"""
            svg_code += f"""<path fill="{color}" d="{data}" />"""
            svg_code += "</svg>"

            pixbuf_loader = GdkPixbuf.PixbufLoader()
            pixbuf_loader.write(svg_code.encode())
            try:
                pixbuf_loader.close()
            except GLib.Error:
                # Error on MacOS, Gramps 6.0.0 for SVGs:
                # gi.repository.GLib.GError: gdk-pixbuf-error-quark: Unrecognized image file format (3)
                # Use white pixbuf of correct size as replacement
                pixbuf = GdkPixbuf.Pixbuf.new(
                    GdkPixbuf.Colorspace.RGB, True, 8,
                    img_width, img_height
                )
                pixbuf.fill(0xFFFFFFFF)
            else:
                pixbuf = pixbuf_loader.get_pixbuf()
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

                event_data_label = self.create_label_for_grid(name_displayer.display_name(alt_name))
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

            place_name = self.ftv.get_place_name_from_event(event)
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
                    parent_name_label = self.create_person_name_label_for_grid(parent)
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
                parent_name_label = self.create_person_name_label_for_grid(parent)
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

            child_name_label = self.create_person_name_label_for_grid(child)
            grid.attach(child_name_label, 1, i_row, 1, 1)

            child_dates_label = self.create_birth_death_label_for_grid(child)
            grid.attach(child_dates_label, 2, i_row, 1, 1)

            i_row += 1
        return grid

    def create_person_buttons_widget(self, person_handle, x_person, generation, panel_button=True):
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        edit_button = self.create_button(_("Edit"), icon="gtk-edit")
        edit_button.connect("clicked", lambda *_: self.ftv.edit_person(person_handle))
        buttons.pack_start(edit_button, False, False, 0)

        home_person = self.ftv.dbstate.db.get_default_person()
        set_home_button = self.create_button(_("Set home"), icon="go-home")
        if home_person is not None:
            set_home_button.set_sensitive(home_person.handle!=person_handle)
        set_home_button.connect("clicked", lambda *_: self.ftv.set_home_person(person_handle, also_set_active=False))
        buttons.pack_start(set_home_button, False, False, 0)

        set_active_button = self.create_button(_("Set active"), char="\u2794") # rightwards arrow
        set_active_button.set_sensitive(self.ftv.get_active() != person_handle)
        set_active_button.connect("clicked", lambda *_: self.ftv.set_active_person(person_handle))
        buttons.pack_start(set_active_button, False, False, 0)

        if panel_button:
            self.open_panel_button = self.create_button(_("Open panel"), icon="sidebar-show-right")
            self.open_panel_button_opens = True
            def cb_open_panel_button(*args):
                if self.open_panel_button_opens:
                    self.widget_manager.panel_manager.open_person_panel(person_handle, x_person, generation)
                    new_label = _("Close panel")
                else:
                    self.widget_manager.close_panel()
                    new_label = _("Open panel")
                self.open_panel_button.get_children()[0].get_children()[1].set_label(new_label)
                self.open_panel_button_opens = not self.open_panel_button_opens
            self.open_panel_button.connect("clicked", cb_open_panel_button)
            buttons.pack_start(self.open_panel_button, False, False, 0)

        add_relative_button = self.create_button(_("Add relative"), icon="list-add")
        add_relative_button.connect("clicked",
            self.widget_manager.person_add_relative_clicked,
            person_handle, x_person, generation
        )
        buttons.pack_start(add_relative_button, False, False, 0)

        return buttons

    def create_family_buttons_widget(self, family_handle, x_family, generation, panel_button=True):

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        edit_button = self.create_button(_("Edit"), icon="gtk-edit")
        edit_button.connect("clicked", lambda *_: self.ftv.edit_family(family_handle))
        buttons.pack_start(edit_button, False, False, 0)

        if self.ftv._config.get("interaction.familytreeview-family-info-box-set-active-button"):
            set_active_button = self.create_button(_("Set active"), char="\u2794") # rightwards arrow
            set_active_button.set_sensitive(self.ftv.get_active_family_handle() != family_handle)
            set_active_button.connect("clicked", lambda *_: self.ftv.set_active_family(family_handle))
            buttons.pack_start(set_active_button, False, False, 0)

        if panel_button:
            self.open_panel_button = self.create_button(_("Open panel"), icon="sidebar-show-right")
            self.open_panel_button_opens = True
            def cb_open_panel_button(*args):
                if self.open_panel_button_opens:
                    self.widget_manager.panel_manager.open_family_panel(family_handle, x_family, generation)
                    new_label = _("Close panel")
                else:
                    self.widget_manager.close_panel()
                    new_label = _("Open panel")
                self.open_panel_button.get_children()[0].get_children()[1].set_label(new_label)
                self.open_panel_button_opens = not self.open_panel_button_opens
            self.open_panel_button.connect("clicked", cb_open_panel_button)
            buttons.pack_start(self.open_panel_button, False, False, 0)

        add_relative_button = self.create_button(_("Add relative"), icon="list-add")
        add_relative_button.connect("clicked",
            self.widget_manager.family_add_relative_clicked,
            family_handle, x_family, generation
        )
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
        tags_flow.set_max_children_per_line(GLib.MAXUINT8) # no limit, larger is slow
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

    def create_gallery(self, obj):
        gallery_flow_box = Gtk.FlowBox()
        gallery_flow_box.set_selection_mode(Gtk.SelectionMode.NONE)
        gallery_flow_box.set_max_children_per_line(GLib.MAXUINT8) # no limit, larger is slow
        media_list = obj.get_media_list()
        for media_ref in media_list:
            media_handle = media_ref.get_reference_handle()
            media = self.ftv.dbstate.db.get_media_from_handle(media_handle)
            path = media_path_full(self.ftv.dbstate.db, media.get_path())
            photo = Photo()
            pixbuf = get_thumbnail_image(
                path,
                media.get_mime_type(),
                media_ref.get_rectangle()
            )
            photo.set_pixbuf(path, pixbuf)
            gallery_flow_box.add(photo)
        return gallery_flow_box

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
