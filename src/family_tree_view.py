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


import inspect
import os
from sqlite3 import InterfaceError
import traceback

import cairo
from gi.repository import GdkPixbuf, GLib, Gtk

from gramps.gen.config import config
from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.errors import HandleError
from gramps.gen.lib import EventType
from gramps.gen.utils.callback import Callback
from gramps.gen.utils.file import find_file, media_path_full
from gramps.gen.utils.symbols import Symbols
from gramps.gen.utils.thumbnails import get_thumbnail_path
from gramps.gui.editors import EditFamily, EditPerson
from gramps.gui.pluginmanager import GuiPluginManager
from gramps.gui.views.bookmarks import PersonBookmarks
from gramps.gui.views.navigationview import NavigationView
from gramps.cli.clidbman import CLIDbManager

from abbreviated_name_display import AbbreviatedNameDisplay
from family_tree_view_badge_manager import FamilyTreeViewBadgeManager
from family_tree_view_config_provider import FamilyTreeViewConfigProvider
from family_tree_view_icons import get_family_avatar_svg_data, get_person_avatar_svg_data
from family_tree_view_widget_manager import FamilyTreeViewWidgetManager


_ = GRAMPS_LOCALE.translation.gettext

class FamilyTreeView(NavigationView, Callback):
    ADDITIONAL_UI = [
        # "Edit" menu:
        """
        <section id="CommonEdit" groups="RW">
            <item>
                <attribute name="action">win.PrintView</attribute>
                <attribute name="label" translatable="yes">Print...</attribute>
            </item>
            <item>
                <attribute name="action">win.ExportSvgView</attribute>
                <attribute name="label" translatable="yes">Export as SVG...</attribute>
            </item>
        </section>
        """,
        # "Go" menu:
        """
        <placeholder id="CommonGo">
            <section>
                <item>
                    <attribute name="action">win.Back</attribute>
                    <attribute name="label" translatable="yes">_Back</attribute>
                </item>
                <item>
                    <attribute name="action">win.Forward</attribute>
                    <attribute name="label" translatable="yes">_Forward</attribute>
                </item>
            </section>
            <section>
                <item>
                    <attribute name="action">win.HomePerson</attribute>
                    <attribute name="label" translatable="yes">_Home</attribute>
                </item>
            </section>
        </placeholder>
        """,
        # Toolbar buttons:
        """
        <placeholder id="CommonNavigation">
            <child groups="RO">
                <object class="GtkToolButton">
                    <property name="icon-name">go-previous</property>
                    <property name="action-name">win.Back</property>
                    <property name="tooltip_text" translatable="yes">Go to the previous object in the history</property>
                    <property name="label" translatable="yes">_Back</property>
                    <property name="use-underline">True</property>
                </object>
                <packing>
                    <property name="homogeneous">False</property>
                </packing>
            </child>
            <child groups="RO">
                <object class="GtkToolButton">
                    <property name="icon-name">go-next</property>
                    <property name="action-name">win.Forward</property>
                    <property name="tooltip_text" translatable="yes">Go to the next object in the history</property>
                    <property name="label" translatable="yes">_Forward</property>
                    <property name="use-underline">True</property>
                </object>
                <packing>
                    <property name="homogeneous">False</property>
                </packing>
            </child>
            <child groups="RO">
                <object class="GtkToolButton">
                    <property name="icon-name">go-home</property>
                    <property name="action-name">win.HomePerson</property>
                    <property name="tooltip_text" translatable="yes">Go to the home person</property>
                    <property name="label" translatable="yes">_Home</property>
                    <property name="use-underline">True</property>
                </object>
                <packing>
                    <property name="homogeneous">False</property>
                </packing>
            </child>
        </placeholder>
        """,
        """
        <placeholder id="BarCommonEdit">
            <child groups="RO">
                <object class="GtkToolButton">
                    <property name="icon-name">document-print</property>
                    <property name="action-name">win.PrintView</property>
                    <property name="tooltip_text" translatable="yes">Print or save the tree</property>
                    <property name="label" translatable="yes">Print...</property>
                    <property name="use-underline">True</property>
                </object>
                <packing>
                    <property name="homogeneous">False</property>
                </packing>
            </child>
            <child groups="RO">
                <object class="GtkToolButton">
                    <property name="icon-name">document-export</property>
                    <property name="action-name">win.ExportSvgView</property>
                    <property name="tooltip_text" translatable="yes">Export the tree as SVG</property>
                    <property name="label" translatable="yes">Export as SVG...</property>
                    <property name="use-underline">True</property>
                </object>
                <packing>
                    <property name="homogeneous">False</property>
                </packing>
            </child>
        </placeholder>
        """,
    ]

    CONFIGSETTINGS = FamilyTreeViewConfigProvider.get_config_settings()

    __signals__ = {
        "abbrev-rules-changed": None,
    }

    def __init__(self, pdata, dbstate, uistate, nav_group=0):
        self.badge_manager = FamilyTreeViewBadgeManager(self)
        self.config_provider = FamilyTreeViewConfigProvider(self)

        NavigationView.__init__(self, _("FamilyTreeView"), pdata, dbstate, uistate, PersonBookmarks, nav_group)
        Callback.__init__(self)

        self.dbstate = dbstate
        self.uistate = uistate
        self.nav_group = nav_group
        self.dbstate.connect("database-changed", self._cb_db_changed)
        self.uistate.connect("nameformat-changed", self.close_info_and_rebuild)

        self.additional_uis.append(self.ADDITIONAL_UI)

        self.symbols = Symbols()
        self.widget_manager = FamilyTreeViewWidgetManager(self)
        self.abbrev_name_display = AbbreviatedNameDisplay(self)

        # FTV needs to update the tree on theme change to ensure line color, expander colors, etc. are updated.
        # Note that the following will also update the tree each time when the window loses focus:
        # self.widget_manager.main_widget.connect("style-updated", self.close_info_and_rebuild)
        # TODO This doesn't seem to work, although the themes addon sets the "gtk-theme-name" property of Gtk.Settings.get_default():
        # Gtk.Settings.get_default().connect("notify::gtk-theme-name", self.close_info_and_rebuild)
        # TODO Workaround: Connect to configs set by themes addon.
        for key in [
            "preferences.theme",
            "preferences.theme-dark-variant",
            "preferences.font"
        ]:
            if config.is_set(key):
                # Wait for idle as the theme update takes a bit.
                # The tree has to rebuild after the theme is applied.
                config.connect(key, lambda *args: GLib.idle_add(self.close_info_and_rebuild))

        # There doesn't seem to be a signal for updating colors.
        # TODO This is not an ideal solution.
        for config_name in config.get_section_settings("colors"):
            config.connect("colors." + config_name, self.close_info_and_rebuild)

        self.generic_filter = None

        self.addons_registered_badges = False

        self.print_settings = None
        self.print_margin = 20

    def navigation_type(self):
        return "Person"

    def can_configure(self):
        # can_configure is the first method called when other addons can find FamilyTreeView.
        self.let_addons_register_badges()

        # The actual purpose of this method:
        return True

    def let_addons_register_badges(self):
        if self.addons_registered_badges:
            return

        # let all badge addons register their badges
        pluginManager = GuiPluginManager.get_instance()
        data = pluginManager.get_plugin_data("family_tree_view_badge_addon")
        for fcn in data:
            try:
                fcn(self.dbstate, self.uistate, self.badge_manager)
            except TypeError as e:
                # TODO drop support for this in a future update
                if len(traceback.extract_tb(e.__traceback__)) == 1:
                    # Wrong signature for fnc.
                    fcn(self.dbstate, self.uistate)
                else:
                    raise
        self.addons_registered_badges = True

    def define_actions(self):
        super().define_actions()
        self._add_action("PrintView", self.print_view, "<PRIMARY><SHIFT>P")
        self._add_action("ExportSvgView", self.export_svg_view,)

    def config_connect(self):
        self.config_provider.config_connect(self._config, self.cb_update_config)

    def cb_update_config(self, client, connection_id, entry, data):

        # Required to apply changed number of generations to show.
        self.widget_manager.tree_builder.reset()

        self.close_info_and_rebuild()

    def _get_configure_page_funcs(self):
        return self.config_provider.get_configure_page_funcs()

    def _cb_db_changed(self, db):
        self._change_db(db)
        self.close_info_and_rebuild()

    def build_widget(self):
        # Widget is built during __init__ and only returned here.
        return self.widget_manager.main_widget

    def build_tree(self):
        # In other NavigationViews, both build_tree and goto_handle call
        # the main buildup of the view. But it looks like after
        # build_tree() is called, goto_handle() is almost always called
        # as well, so the tree is reloaded immediately, i.e. loaded
        # twice. Since goto_handle() is more precise (i.e. which person
        # should be the active person), only build the tree if
        # goto_handle() will not be called.

        # Apparently there are only two cases where the tree needs to
        # update when this function is called (i.e. goto_handle() is not
        # called and no connected signal is emitted):
        # - empty db and other similar cases
        # - sidebar filter is applied

        if self.check_and_handle_empty_db():
            return

        rebuild_now = True

        # If self.build_tree() is called by PageView.set_active(),
        # self.goto_handle() is always called by
        # NavigationView.goto_active() afterwards, if the return value
        # of self.uistate.get_active() is not considered false (e.g. not
        # an empty string). Therefore, don't rebuild the tree in this
        # situation as goto_handle() will be called.
        caller_frame_info = inspect.stack()[1] # 0 is this call to build_tree
        if (
            caller_frame_info.function == "set_active"
            and os.path.basename(caller_frame_info.filename) == "pageview.py"
        ):
            active = self.uistate.get_active(
                self.navigation_type(),
                self.navigation_group()
            )
            if active:
                rebuild_now = False

        # Maybe there are more cases which can be identified...

        if rebuild_now:
            self.rebuild_tree()

    def goto_handle(self, handle):
        # See also self.build_tree().

        if handle:
            try:
                person = self.get_person_from_handle(handle)
            except InterfaceError:
                # not a person
                pass
            else:
                if person is not None:
                    # a person
                    self.change_active(handle)
        self.rebuild_tree()
        self.uistate.modify_statusbar(self.dbstate)

    def _connect_db_signals(self):
        self.callman.add_db_signal("person-update", self._object_updated)
        self.callman.add_db_signal("family-update", self._object_updated)
        self.callman.add_db_signal("event-update", self._object_updated)

    def _object_updated(self, handle):
        offset = self.widget_manager.canvas_manager.get_center_in_units()
        self.close_info_and_rebuild(offset=offset)

    def close_info_and_rebuild(self, *_, offset=None): # *_ required when used as callback
        self.widget_manager.info_box_manager.close_info_box()
        self.widget_manager.close_panel()
        self.rebuild_tree(offset=offset)

    def rebuild_tree(self, offset=None):
        self.uistate.set_busy_cursor(True)

        self.widget_manager.reset_tree()

        if not self.check_and_handle_special_db_cases():
            # no special case had to be handled

            root_person_handle = self.get_active()
            if isinstance(root_person_handle, list):
                # it's a list (with one element) sometimes
                # TODO Can this still happen?
                root_person_handle = root_person_handle[0]

            if root_person_handle is not None and len(root_person_handle) > 0: # handle can be empty string
                if offset is None:
                    # If there is no offset, the new tree is not closely related to the previous one.
                    self.widget_manager.tree_builder.reset()
                self.widget_manager.tree_builder.prepare_redraw()
                self.widget_manager.tree_builder.process_person(root_person_handle, 0, 0, ahnentafel=1)
                if offset is None:
                    self.widget_manager.canvas_manager.move_to_center()
                else:
                    self.widget_manager.canvas_manager.move_to_center(*offset)
        self.uistate.set_busy_cursor(False)

    def check_and_handle_special_db_cases(self):
        """Returns True if special cases were handled (no tree should be built)."""
        if not self.dbstate.db.is_open():
            # no db loaded
            if len(CLIDbManager(self.dbstate).current_names) == 0: # TODO This condition has not been tested yet!
                # no db to load
                # TODO Show some replacement text, e.g. 
                # "No database to load. Create or import one."
                # (where import creates one first).
                pass
            else:
                # no db loaded but can be loaded
                # TODO Show some replacement text, e.g. 
                # "No database loaded. Load, create or import one."
                # (where import creates one first).
                pass
            return True
        if self.check_and_handle_empty_db():
            return True

        # A db with people is loaded.

        no_active = len(self.get_active()) == 0 # returns handle str with length 0 if no active
        no_home = self.dbstate.db.get_default_handle() is None # returns None if no home
        if no_active and no_home:
            # neither an active nor a home person
            # TODO Show some replacement text, e.g. 
            # "No person selected to display the tree for. Please select a person."
            return True
        if no_active and not no_home:
            self.set_active_person(self.dbstate.db.get_default_handle())
        elif no_home and not no_active:
            self.set_home_person(self.get_active())
        # If both are set, everything is alright.
        return False

    def check_and_handle_empty_db(self):
        if self.dbstate.db.get_number_of_people() == 0:
            # db has no people
            # show missing person
            self.widget_manager.add_missing_person(0, 0, "c")
            return True
        return False

    def get_image_spec(self, obj, obj_type):
        if obj_type == "person":
            data_callback = get_person_avatar_svg_data
        else:
            data_callback = get_family_avatar_svg_data

        if obj is None:
            return ("svg_data_callback", data_callback)

        media_list = obj.get_media_list()
        if not media_list:
            return ("svg_data_callback", data_callback)

        media_handle = media_list[0].get_reference_handle()
        media = self.dbstate.db.get_media_from_handle(media_handle)
        media_mime_type = media.get_mime_type()
        if media_mime_type[0:5] == "image":
            rectangle = media_list[0].get_rectangle()
            path = media_path_full(self.dbstate.db, media.get_path())
            image_resolution = self._config.get("appearance.familytreeview-person-image-resolution")
            if image_resolution == -1:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
                if rectangle is not None:
                    width = pixbuf.get_width()
                    height = pixbuf.get_height()
                    upper_x = min(rectangle[0], rectangle[2]) / 100.0
                    lower_x = max(rectangle[0], rectangle[2]) / 100.0
                    upper_y = min(rectangle[1], rectangle[3]) / 100.0
                    lower_y = max(rectangle[1], rectangle[3]) / 100.0
                    sub_x = round(upper_x * width)
                    sub_y = round(upper_y * height)
                    sub_width = round((lower_x - upper_x) * width)
                    sub_height = round((lower_y - upper_y) * height)
                    if sub_width > 0 and sub_height > 0:
                        pixbuf = pixbuf.new_subpixbuf(sub_x, sub_y, sub_width, sub_height)
                return ("pixbuf", pixbuf)
            else:
                image_path = get_thumbnail_path(path, rectangle=rectangle, size=image_resolution)
                image_path = find_file(image_path)
                return ("path", image_path)

        return ("svg_data_callback", data_callback)

    def get_full_place_name(self, place_handle):
        """gramps.gen.utils.libformatting.get_place_name without character limit"""
        if place_handle:
            place = self.dbstate.db.get_place_from_handle(place_handle)
            if place:
                place_name = place_displayer.display(self.dbstate.db, place)
                return place_name

    def get_full_place_name_from_event(self, event):
        if event:
            place_name = place_displayer.display_event(self.dbstate.db, event)
            return place_name

    def set_home_person(self, person_handle, also_set_active=False):
        if self.get_person_from_handle(person_handle) is not None:
            self.dbstate.db.set_default_person_handle(person_handle)
            if also_set_active:
                self.set_active_person(person_handle)
            else:
                self.widget_manager.info_box_manager.close_info_box()
                self.rebuild_tree()

    def set_active_person(self, person_handle):
        if self.get_person_from_handle(person_handle) is not None:
            self.widget_manager.info_box_manager.close_info_box()
            self.change_active(person_handle)
            # self.change_active() emits the active-changed signal which
            # is connected to self.goto_handle().

    def set_active_family(self, family_handle):
        if self.get_family_from_handle(family_handle) is not None:
            self.widget_manager.info_box_manager.close_info_box()
            self.change_active_family(family_handle)
            # Tree is not rebuilt since navigation type is not "Person".

    def get_person_from_handle(self, handle):
        try:
            return self.dbstate.db.get_person_from_handle(handle)
        except HandleError:
            return None

    def get_family_from_handle(self, handle):
        try:
            return self.dbstate.db.get_family_from_handle(handle)
        except HandleError:
            return None

    def get_active_family(self):
        nav_group = 0 # TODO not sure about this
        hobj = self.uistate.get_history("Family", nav_group)
        return hobj.present()

    def get_symbol(self, event_type):
        if event_type == EventType.DEATH:
            if self.uistate and self.uistate.symbols:
                return self.symbols.get_death_symbol_for_char(self.uistate.death_symbol)
            else:
                return self.symbols.get_death_symbol_fallback(self.symbols.DEATH_SYMBOL_LATIN_CROSS)

        if event_type == EventType.BIRTH:
            symbol = self.symbols.SYMBOL_BIRTH
        elif event_type == EventType.BAPTISM:
            symbol = self.symbols.SYMBOL_BAPTISM
        elif event_type == EventType.CREMATION:
            symbol = self.symbols.SYMBOL_CREMATED
        elif event_type == EventType.BURIAL:
            symbol = self.symbols.SYMBOL_BURIED
        elif event_type == EventType.MARRIAGE:
            symbol = self.symbols.SYMBOL_MARRIAGE
        elif event_type == EventType.DIVORCE:
            symbol = self.symbols.SYMBOL_DIVORCE
        else:
            # no symbol for other events
            return ""

        if self.uistate and self.uistate.symbols:
            return self.symbols.get_symbol_for_string(symbol)
        else:
            return self.symbols.get_symbol_fallback(symbol)

    def change_active_family(self, handle):
        nav_group = 0 # TODO not sure about this
        hobj = self.uistate.get_history("Family", nav_group)
        if handle and not hobj.lock and not (handle == hobj.present()):
            hobj.push(handle)

    # editing windows

    def edit_person(self, person_handle):
        person = self.get_person_from_handle(person_handle)
        if person is not None:
            EditPerson(self.dbstate, self.uistate, [], person)

    def edit_family(self, family_handle):
        family = self.dbstate.db.get_family_from_handle(family_handle)
        if family is not None:
            EditFamily(self.dbstate, self.uistate, [], family)

    # printing

    def print_view(self, *args):
        print_operation = Gtk.PrintOperation()
        if (self.print_settings is not None):
            print_operation.set_print_settings(self.print_settings)

        # Since there is no universal way to split the tree across multiple pages,
        # the entire tree is printed on a custom page that can be pre-processed.
        print_operation.set_n_pages(1)
        page_setup = Gtk.PageSetup()
        page_setup.set_left_margin(self.print_margin, Gtk.Unit.POINTS)
        page_setup.set_top_margin(self.print_margin, Gtk.Unit.POINTS)
        page_setup.set_right_margin(self.print_margin, Gtk.Unit.POINTS)
        page_setup.set_bottom_margin(self.print_margin, Gtk.Unit.POINTS)
        canvas_bounds = self.widget_manager.canvas_manager.canvas_bounds
        padding = self.widget_manager.canvas_manager.canvas_padding
        tree_width = canvas_bounds[2] - canvas_bounds[0] - 2*padding
        tree_height = canvas_bounds[3] - canvas_bounds[1] - 2*padding
        if self._config.get("interaction.familytreeview-printing-scale-to-page"):
            # TODO How to get the page size used by Windows' print to PDF?
            # Use the smallest dimension of Letter and A4.
            min_paper_height = 11 * 72 # in -> pt # height of letter (A4 has 11.7)
            min_paper_width = 8.268 * 72 # in -> pt # width of A4 (Letter has 8.5)
            scale = min(
                (min_paper_height - 2*self.print_margin)/tree_height,
                (min_paper_width - 2*self.print_margin)/tree_width
            )
        else:
            scale = 1
        paper_width = tree_width*scale + 2*self.print_margin
        paper_height = tree_height*scale + 2*self.print_margin
        paper_size = Gtk.PaperSize.new_custom("custom-matching-tree", "Tree Size", paper_width, paper_height, Gtk.Unit.POINTS)
        page_setup.set_paper_size(paper_size)
        print_operation.set_default_page_setup(page_setup)

        print_operation.connect("draw-page", self.draw_page, scale)
        res = print_operation.run(Gtk.PrintOperationAction.PRINT_DIALOG, self.uistate.window)
        if res == Gtk.PrintOperationResult.APPLY:
            self.print_settings = print_operation.get_print_settings()

    def draw_page(self, print_operation, print_context, page_nr, scale):
        # NOTE: Zoom of canvas doesn't need to be considered here.
        cr = print_context.get_cairo_context()
        canvas_bounds = self.widget_manager.canvas_manager.canvas_bounds
        padding = self.widget_manager.canvas_manager.canvas_padding
        cr.scale(scale, scale)

        # On Windows, there is an extra scale factor, see
        # https://mail.gnome.org/archives/gtk-app-devel-list/2012-June/msg00092.html
        # x0 (and y0) should be the margin, but on Windows they are
        # different and can be used to calculate the extra scale factor:
        extra_scale = cr.get_matrix().x0 / self.print_margin
        cr.scale(extra_scale, extra_scale)

        cr.translate(-canvas_bounds[0]-padding, -canvas_bounds[1]-padding)
        bounds = None # entire canvas
        self.widget_manager.canvas_manager.canvas.render(cr, bounds, 0.0)

    def export_svg_view(self, *args):

        # Ask where to save it.
        dialog = Gtk.FileChooserDialog(
            title=_("Export tree as SVG"),
            transient_for=self.uistate.window,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        filter_svg = Gtk.FileFilter()
        filter_svg.set_name(_("SVG files"))
        filter_svg.add_mime_type("image/svg+xml")
        dialog.add_filter(filter_svg)

        filter_any = Gtk.FileFilter()
        filter_any.set_name(_("Any files"))
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

        response = dialog.run()

        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        file_name = dialog.get_filename()
        dialog.destroy()

        if file_name[:-4].lower() != ".svg":
            file_name += ".svg"

        # TODO Catch errors of cairo write.
        # Can't find a way to catch cairo.IOError. Also,
        # os.access(os.path.dirname(file_name), os.W_OK) and
        # os.access(file_name, os.W_OK) don't help.

        # actual export
        canvas_bounds = self.widget_manager.canvas_manager.canvas_bounds
        padding = self.widget_manager.canvas_manager.canvas_padding
        width = canvas_bounds[2]-canvas_bounds[0]-2*padding
        height = canvas_bounds[3]-canvas_bounds[1]-2*padding
        with cairo.SVGSurface(file_name, width, height) as surface:
            context = cairo.Context(surface)
            context.translate(-canvas_bounds[0]-padding, -canvas_bounds[1]-padding)
            bounds = None
            self.widget_manager.canvas_manager.canvas.render(context, bounds, 0.0)
            surface.finish()

        # message: completed
        dialog = Gtk.MessageDialog(
            transient_for=self.uistate.window,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Export completed.",
        )
        dialog.format_secondary_text(
            f"Tree was saved: {file_name}"
        )
        dialog.run()
        dialog.destroy()
