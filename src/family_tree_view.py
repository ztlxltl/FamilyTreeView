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


from sqlite3 import InterfaceError
import traceback

from gi.repository import Gtk

from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.errors import HandleError
from gramps.gen.lib import EventType
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
from family_tree_view_widget_manager import FamilyTreeViewWidgetManager


_ = GRAMPS_LOCALE.translation.gettext

class FamilyTreeView(NavigationView):
    ADDITIONAL_UI = [
        # "Edit" menu:
        """
        <section id="CommonEdit" groups="RW">
            <item>
                <attribute name="action">win.PrintView</attribute>
                <attribute name="label" translatable="yes">Print...</attribute>
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
        </placeholder>
        """,
    ]

    CONFIGSETTINGS = FamilyTreeViewConfigProvider.get_config_settings()

    def __init__(self, pdata, dbstate, uistate, nav_group=0):
        self.badge_manager = FamilyTreeViewBadgeManager(self)
        self.config_provider = FamilyTreeViewConfigProvider(self)

        NavigationView.__init__(self, _("FamilyTreeView"), pdata, dbstate, uistate, PersonBookmarks, nav_group)

        self.dbstate = dbstate
        self.uistate = uistate
        self.nav_group = nav_group
        self.dbstate.connect("database-changed", self._cb_db_changed)
        self.uistate.connect("nameformat-changed", self.close_info_and_rebuild)

        self.additional_uis.append(self.ADDITIONAL_UI)

        self.symbols = Symbols()
        self.widget_manager = FamilyTreeViewWidgetManager(self)
        self.abbrev_name_display = AbbreviatedNameDisplay(self)

        self.processed_person_handles = []

        self.addons_registered_badges = False

        self.print_settings = None

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
        # Cannot build tree without handle.
        # See self.goto_handle

        # The apparently only case which needs to be covered here is an empty db:
        self.check_and_handle_empty_db()

    def goto_handle(self, handle):
        # In other implementations, both build_tree and goto_handle call the main buildup of the view.
        # But it looks like after build_tree is called, goto_handle is always called as well,
        # so the tree would be reloaded immediately, i.e. loaded twice.
        # The apparently only case in which only build_tree is when FTV is opened the first time 
        # after Gramps started and the db is empty (no people).

        person_handle = None
        if handle:
            try:
                person = self.get_person_from_handle(handle)
            except InterfaceError:
                # not a person
                pass
            else:
                if person is not None:
                    # a person
                    person_handle = handle
        self.change_active(person_handle)
        self.rebuild_tree()
        self.uistate.modify_statusbar(self.dbstate)

    def _connect_db_signals(self):
        self.callman.add_db_signal("person-update", self.close_info_and_rebuild)
        self.callman.add_db_signal("family-update", self.close_info_and_rebuild)
        self.callman.add_db_signal("event-update", self.close_info_and_rebuild)

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

    def get_image_spec(self, person):
        if person is None:
            return ("svg_default", "avatar_simple")

        media_list = person.get_media_list()
        if not media_list:
            return ("svg_default", "avatar_simple")

        media_handle = media_list[0].get_reference_handle()
        media = self.dbstate.db.get_media_from_handle(media_handle)
        media_mime_type = media.get_mime_type()
        if media_mime_type[0:5] == "image":
            rectangle = media_list[0].get_rectangle()
            path = media_path_full(self.dbstate.db, media.get_path())
            image_path = get_thumbnail_path(path, rectangle=rectangle)
            image_path = find_file(image_path)
            return ("path", image_path)

        return ("svg_default", "avatar_simple")

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
            self.change_active(person_handle)
            self.widget_manager.info_box_manager.close_info_box()
            self.rebuild_tree()

    def set_active_family(self, family_handle):
        if self.get_family_from_handle(family_handle) is not None:
            self.change_active_family(family_handle)
            self.widget_manager.info_box_manager.close_info_box()
            # no rebuild_tree

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
        margin = 10
        page_setup.set_left_margin(margin, Gtk.Unit.POINTS)
        page_setup.set_top_margin(margin, Gtk.Unit.POINTS)
        page_setup.set_right_margin(margin, Gtk.Unit.POINTS)
        page_setup.set_bottom_margin(margin, Gtk.Unit.POINTS)
        canvas_bounds = self.widget_manager.canvas_manager.canvas_bounds
        padding = self.widget_manager.canvas_manager.canvas_padding
        paper_width = canvas_bounds[2] - canvas_bounds[0] - 2*padding + 2*margin
        paper_height = canvas_bounds[3] - canvas_bounds[1] - 2*padding + 2*margin
        paper_size = Gtk.PaperSize.new_custom("custom-matching-tree", "Tree Size", paper_width, paper_height, Gtk.Unit.POINTS)
        page_setup.set_paper_size(paper_size)
        print_operation.set_default_page_setup(page_setup)

        print_operation.connect("draw-page", self.draw_page)
        # print_operation.connect("paginate", lambda print_operation, print_context: True) # True = done
        res = print_operation.run(Gtk.PrintOperationAction.PRINT_DIALOG, self.uistate.window)
        if res == Gtk.PrintOperationResult.APPLY:
            self.print_settings = print_operation.get_print_settings()

    def draw_page(self, print_operation, print_context, page_nr):
        # NOTE: Zoom of canvas doesn't need to be considered here
        cr = print_context.get_cairo_context()
        canvas_bounds = self.widget_manager.canvas_manager.canvas_bounds
        padding = self.widget_manager.canvas_manager.canvas_padding
        cr.translate(-canvas_bounds[0]-padding, -canvas_bounds[1]-padding)
        bounds = None # entire canvas
        self.widget_manager.canvas_manager.canvas.render(cr, bounds, 0.0)
