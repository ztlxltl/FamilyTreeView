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


from contextlib import suppress
import inspect
import os
from sqlite3 import InterfaceError
import traceback

import cairo
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from gramps.gen.config import config
from gramps.gen.const import CUSTOM_FILTERS
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.errors import HandleError, WindowActiveError
from gramps.gen.lib import ChildRef, EventType, Family, FamilyRelType, Person, Surname
from gramps.gen.utils.callback import Callback
from gramps.gen.utils.file import find_file, media_path_full
from gramps.gen.utils.symbols import Symbols
from gramps.gen.utils.thumbnails import get_thumbnail_path
from gramps.gui.editors import EditFamily, EditPerson, FilterEditor
from gramps.gui.pluginmanager import GuiPluginManager
from gramps.gui.views.bookmarks import PersonBookmarks
from gramps.gui.views.navigationview import NavigationView
from gramps.cli.clidbman import CLIDbManager

from abbreviated_name_display import AbbreviatedNameDisplay
from family_tree_view_badge_manager import FamilyTreeViewBadgeManager
from family_tree_view_config_provider import FamilyTreeViewConfigProvider
from family_tree_view_icons import get_family_avatar_svg_data, get_person_avatar_svg_data
from family_tree_view_utils import get_gettext
from family_tree_view_widget_manager import FamilyTreeViewWidgetManager


_ = get_gettext()

class FamilyTreeView(NavigationView, Callback):
    ADDITIONAL_UI = [
        # "Family Trees" menu: 
        # Export as SVG is also added here since list views have their
        # export here.
        """
        <placeholder id="LocalExport">
            <item>
                <attribute name="action">win.ExportSvgView</attribute>
                <attribute name="label" translatable="yes">Export view as SVG...</attribute>
            </item>
        </placeholder>
        """,
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
        """
        <placeholder id="otheredit">
            <item>
                <attribute name="action">win.FilterEditPerson</attribute>
                <attribute name="label" translatable="yes">Person Filter Editor</attribute>
            </item>
            <item>
                <attribute name="action">win.FilterEditFamily</attribute>
                <attribute name="label" translatable="yes">Family Filter Editor</attribute>
            </item>
        </placeholder>
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
                    <property name="icon-name">document-save</property>
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

        self.additional_uis.append(self.ADDITIONAL_UI)

        self.generic_filter = None

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
            try:
                # Wait for idle as the theme update takes a bit.
                # The tree has to rebuild after the theme is applied.
                if key == "preferences.font":
                    # If the font changes (font includes the font size),
                    # also reset the boxes (line height, best name
                    # abbreviations).
                    config.connect(key, lambda *args: GLib.idle_add(self.widget_manager.canvas_manager.reset_boxes))
                config.connect(key, lambda *args: GLib.idle_add(self._cb_global_appearance_config_changed))
            except (AttributeError, KeyError):
                # Config keys not set, e.g. Themes/ThemesPrefs plugin
                # not installed. Unfortunately, config.is_set(key) and
                # ConfigManager._validate_section_and_setting (in
                # config.connect()) don't guarantee that
                # config.connect() will work because they only check
                # ConfigManager.data, not ConfigManager.callbacks. For
                # some reason, they can be out of sync.
                pass

        # There doesn't seem to be a signal for updating colors.
        # TODO This is not an ideal solution.
        for config_name in config.get_section_settings("colors"):
            config.connect("colors." + config_name, self._cb_global_appearance_config_changed)

        # Register callbacks after initializing other managers to
        # rebuild the tree after specific resets.
        self.dbstate.connect("database-changed", self._cb_db_changed)
        self.dbstate.connect("no-database", self._cb_db_closed)
        self.uistate.connect("nameformat-changed", self.rebuild_tree)

        self.addons_registered_badges = False

        self.print_settings = None
        self.print_margin = 20
        self.export_padding = 50

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
        self._add_action("ExportSvgView", self.export_svg_view)
        self._add_action("FilterEditPerson", self.open_person_filter_editor)
        self._add_action("FilterEditFamily", self.open_family_filter_editor)

    def config_connect(self):
        self.config_provider.config_connect(self._config, self.cb_update_config)

    def cb_update_config(self, client, connection_id, entry, data):
        # This method is called explicitly sometimes when the config
        # value is a mutable object. Refactoring may be appropriate.

        # Required to apply changed box size or number of lines for abbreviated names.
        self.widget_manager.canvas_manager.reset_boxes()

        # reset: Required to apply changed number of generations to show.
        self.rebuild_tree(reset=True)

    def _get_configure_page_funcs(self):
        return self.config_provider.get_configure_page_funcs()

    def _cb_db_changed(self, db):
        # When changing the db, the tree could rebuild tree times:
        # - goto_handle() called by NavigationView.goto_active() on
        #   receiving the active-changed signal (emitted while clearing
        #   the history after database-changed is emitted by
        #   CLIManager._post_load_newdb_nongui())
        # - database-changed signal
        # - goto_handle() called by NavigationView.goto_active() called
        #   indirectly by ViewManager._post_load_newdb_gui()
        # The call to goto_handle() due to the active-changed signal
        # caused by a db change is identified and ignored. The
        # database-changed signal is not used to rebuild the tree, only
        # to update callbacks by a base class. Only the call to
        # goto_handle() caused by "changing" the active view is used to
        # rebuild the tree.

        # If the database is closed, this signal is also emitted. We use
        # the no-database signal to handle this case.

        self._change_db(db)

    def _cb_db_closed(self):
        # Clear the tree.

        # When opening a database, DbLoader.read_file() indirectly emits
        # the no-database signal twice, once when closing the previous
        # database and once just before using the next database in
        # DbState.change_database(). We don't have to necessarily clear
        # the visualization in those cases, so we don't identify them as
        # clearing is fast.

        self.widget_manager.reset_tree()
        self.widget_manager.canvas_manager.move_to_center()

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

        if self.check_and_handle_special_db_cases():
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

        # The filter is applied each time, since changes to the database
        # that affect the filter result must be taken into account.\
        # TODO Maybe keep track if there were db updates and only run
        # filter if there were. Note that filter changes also need to be
        # tracked. hash(self.generic_filter) doesn't change if rules are
        # being added, but it changes every time the filter button is
        # clicked since a new GenericFilter object is instantiated.
        self.widget_manager.tree_builder.reset_filtered()

        if rebuild_now:
            self.rebuild_tree()

    def goto_handle(self, handle):
        # See also self.build_tree().

        # See self._cb_db_changed() for context.
        stack = inspect.stack()
        if ("_post_load_newdb_nongui", "grampscli.py") in [
            (frame.function, os.path.basename(frame.filename))
            for frame in stack
        ]:
            return

        goto_handle_was_called = False
        if handle:
            try:
                person = self.get_person_from_handle(handle)
            except InterfaceError:
                # not a person
                pass
            else:
                # By setting the the active person, goto_handle will be
                # called again if it's a different person.
                if person is not None and handle != self.get_active():
                    # It's a person and not the active person.
                    self.change_active(handle)
                    goto_handle_was_called = True
        if not goto_handle_was_called:
            self.rebuild_tree()
            self.uistate.modify_statusbar(self.dbstate)

    def set_active(self):
        NavigationView.set_active(self)
        self._set_filter_status()

    def _set_filter_status(self):
        try:
            self.widget_manager
        except AttributeError:
            # initializing
            self.uistate.status.clear_filter()
            return

        text = self.uistate.viewmanager.active_page.get_title()
        text += (": %d/%d" % (
            self.widget_manager.num_persons_added,
            self.dbstate.db.get_number_of_people(),
        ))
        if self.widget_manager.tree_builder.filtered_person_handles is not None:
            text += (" (Filter: %d/%d)" % (
                self.widget_manager.num_persons_matching_filter_added,
                len(self.widget_manager.tree_builder.filtered_person_handles),
            ))
        self.uistate.status.set_filter(text)

    def _connect_db_signals(self):
        # Only connect to the update signals. Connecting to the add
        # signal would result in multiple rebuilds. In all cases where a
        # person/family/event is added, it is only relevant if it linked
        # to something that is already present in the database. It seems
        # like the corresponding update signal is triggered in those
        # cases. Deletion doesn't need to be considered as you cannot
        # delete objects from within FTV. You have to change the view to
        # delte an object and changing back triggers a rebuild.
        self.callman.add_db_signal("person-update", self._object_updated)
        self.callman.add_db_signal("family-update", self._object_updated)
        self.callman.add_db_signal("event-update", self._object_updated)

    def _object_updated(self, handle):
        if self.active:
            # The view will be updated when it is activated
            # (NavigationView.set_active() causes build_tree and
            # goto_handle to be called).
            offset = self.widget_manager.canvas_manager.get_center_in_units()
            self.rebuild_tree(offset=offset)

    def _cb_global_appearance_config_changed(self, *args):
        if self.active:
            # The view will be updated when it is activated
            # (NavigationView.set_active() causes build_tree and
            # goto_handle to be called).
            offset = self.widget_manager.canvas_manager.get_center_in_units()
            self.rebuild_tree(offset=offset)

    def rebuild_tree(self, *_, offset=None, reset=False): # *_ required when used as callback
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
                # If there is no offset, the new tree is not closely
                # related to the previous one.
                reset = reset or offset is None
                self._rebuild_tree(root_person_handle, offset, reset=reset)
        self.uistate.set_busy_cursor(False)

    def _rebuild_tree(self, root_person_handle, offset=None, reset=False):
        self.widget_manager.hide_close_tree_overlay_button()

        # Hide the widget temporarily to avoid flickering. See code of
        # widget manager for more info. 
        # If the widget is not in a window, it's not visible yet and we
        # don't need to hide it.
        widget = self.widget_manager.main_container_paned
        window = widget.get_window()
        if window is not None and window.is_viewable():
            alloc = widget.get_allocation()
            pixbuf = Gdk.pixbuf_get_from_window(window, alloc.x, alloc.y, alloc.width, alloc.height)
            self.widget_manager.replacement_image.set_from_pixbuf(pixbuf)
            self.widget_manager.main_container_stack.set_visible_child_name("image")

        self.widget_manager.tree_builder.build_tree(root_person_handle, reset=reset)

        if offset is None:
            self.widget_manager.canvas_manager.move_to_center()
        else:
            self.widget_manager.canvas_manager.move_to_center(*offset)

        if window is not None:
            self.widget_manager.main_container_stack.set_visible_child_name("actual")

    def check_and_handle_special_db_cases(self):
        """Returns True if special cases were handled (no tree should be built)."""
        if not self.dbstate.db.is_open():
            # No database is loaded.
            self.widget_manager.reset_tree()
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
            self.widget_manager.canvas_manager.move_to_center()
            return True
        if self.dbstate.db.get_number_of_people() == 0:
            # There are no people in the database. show a missing
            # person.
            self.widget_manager.reset_tree()
            self.widget_manager.add_missing_person(0, 0, "c", "root", None)
            self.widget_manager.canvas_manager.move_to_center()
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

    def get_place_name_without_limit(self, place_handle):
        """gramps.gen.utils.libformatting.get_place_name without character limit"""
        if place_handle:
            place = self.dbstate.db.get_place_from_handle(place_handle)
            if place:
                place_name = place_displayer.display(self.dbstate.db, place)
                return place_name

    def get_place_name_from_event(self, event, fmt=-1): # -1 is default
        if event:
            place_name = place_displayer.display_event(self.dbstate.db, event, fmt=fmt)
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

    def get_active_family_handle(self):
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
        self.change_active_obj(handle, "Family")

    def change_active_obj(self, handle, obj_class):
        nav_group = 0 # TODO not sure about this
        hobj = self.uistate.get_history(obj_class, nav_group)
        if handle and not hobj.lock and not (handle == hobj.present()):
            hobj.push(handle)

    def open_uri(self, uri):
        if not uri.startswith("gramps://"):
            return Gtk.show_uri_on_window(uri)
        obj_class, prop, value = uri[9:].split("/", 2)
        if prop != "handle":
            # TODO gramps_id
            return False

        if obj_class == "Person":
            self.change_active(value)
        else:
            self.change_active_obj(value, obj_class)

        return True

    # editing windows: edit objects

    def edit_person(self, person_handle):
        person = self.get_person_from_handle(person_handle)
        if person is None:
            return

        with suppress(WindowActiveError):
            EditPerson(self.dbstate, self.uistate, [], person)

    def edit_family(self, family_handle):
        family = self.dbstate.db.get_family_from_handle(family_handle)
        if family is None:
            return

        with suppress(WindowActiveError):
            EditFamily(self.dbstate, self.uistate, [], family)

    # editing windows: filters

    def open_person_filter_editor(self, *args):
        with suppress(WindowActiveError):
            FilterEditor("Person", CUSTOM_FILTERS, self.dbstate, self.uistate)

    def open_family_filter_editor(self, *args):
        with suppress(WindowActiveError):
            FilterEditor("Family", CUSTOM_FILTERS, self.dbstate, self.uistate)

    # editing windows: new objects

    def add_new_person(self, set_active=False, set_home=False):
        person = Person()
        # The editor window requires a surname.
        person.primary_name.add_surname(Surname())
        person.primary_name.set_primary_surname(0)

        def callback(obj):
            # This is the only case where a person is added without
            # modifying an object. No callback for adding objects was
            # connected using callman.add_db_signal(). Therefore we need
            # to trigger rebuilding the tree. See comments in
            # self._connect_db_signals() for more details. Note that
            # setting the home or active person triggers a rebuild.
            handle = obj.handle
            if set_home:
                self.set_home_person(handle, also_set_active=set_active)
            elif set_active:
                self.set_active_person(handle)
            else:
                self.widget_manager.info_box_manager.close_info_box()
                self.rebuild_tree()

        with suppress(WindowActiveError):
            EditPerson(self.dbstate, self.uistate, [], person, callback)

    def add_new_parent_to_family(self, family_handle, is_first_spouse):
        family = self.get_family_from_handle(family_handle)
        if family is None:
            return

        with suppress(WindowActiveError):
            edit_window = EditFamily(self.dbstate, self.uistate, [], family)
            # TODO WindowActiveError: Can we get the active window and
            # use it instead of creating a new one?
            with suppress(WindowActiveError): # suppress separately for each window
                if is_first_spouse:
                    edit_window.add_father_clicked(None)
                else:
                    edit_window.add_mother_clicked(None)

    def add_new_parent_family(self, person_handle, add_parent=0, add_sibling=False):
        person = self.get_person_from_handle(person_handle)
        if person is None:
            return
        family = Family()
        family.set_relationship(FamilyRelType(FamilyRelType.UNKNOWN))
        ref = ChildRef()
        ref.set_reference_handle(person_handle)
        family.add_child_ref(ref)
        with suppress(WindowActiveError):
            edit_window = EditFamily(self.dbstate, self.uistate, [], family)
            with suppress(WindowActiveError): # suppress separately for each window
                if add_parent == 1:
                    edit_window.add_father_clicked(None)
                elif add_parent == 2:
                    edit_window.add_mother_clicked(None)
                # else and_parent == 0: do nothing
            with suppress(WindowActiveError): # suppress separately for each window
                if add_sibling:
                    edit_window.child_list.add_button_clicked(None)

    def add_new_family(self, person_handle, person_is_first, add_spouse=False, add_child=False):
        """
        Add a new family for a new spouse of person_handle.  If `person_is_first`,
        the person takes the first position, and the new spouse takes the second
        position.
        """
        person = self.get_person_from_handle(person_handle)
        if person is None:
            return
        family = Family()
        family.set_relationship(FamilyRelType(FamilyRelType.UNKNOWN))
        if person_is_first:
            family.set_father_handle(person_handle)
        else:
            family.set_mother_handle(person_handle)
        with suppress(WindowActiveError):
            edit_window = EditFamily(self.dbstate, self.uistate, [], family)
            with suppress(WindowActiveError): # suppress separately for each window
                if add_spouse:
                    if person_is_first: # person is father, add mother
                        edit_window.add_mother_clicked(None)
                    else:
                        edit_window.add_father_clicked(None)
            with suppress(WindowActiveError): # suppress separately for each window
                if add_child:
                    edit_window.child_list.add_button_clicked(None)

    def add_new_spouse(self, family_handle, new_spouse_is_first):
        family = self.dbstate.db.get_family_from_handle(family_handle)
        with suppress(WindowActiveError):
            edit_window = EditFamily(self.dbstate, self.uistate, [], family)
            with suppress(WindowActiveError): # suppress separately for each window
                if new_spouse_is_first:
                    edit_window.add_father_clicked(None)
                else:
                    edit_window.add_mother_clicked(None)

    def add_new_child(self, family_handle):
        family = self.dbstate.db.get_family_from_handle(family_handle)
        with suppress(WindowActiveError):
            edit_window = EditFamily(self.dbstate, self.uistate, [], family)
            with suppress(WindowActiveError): # suppress separately for each window
                edit_window.child_list.add_button_clicked(None)

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
        tree_width = canvas_bounds[2] - canvas_bounds[0] - 2*padding + 2*self.export_padding
        tree_height = canvas_bounds[3] - canvas_bounds[1] - 2*padding + 2*self.export_padding
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

        cr.translate(
            -canvas_bounds[0]-padding+self.export_padding,
            -canvas_bounds[1]-padding+self.export_padding
        )
        self.render_canvas_to_context(cr)

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
            Gtk.STOCK_SAVE,
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

        recent_dir = self._config.get("paths.familytreeview-recent-export-dir")
        dialog.set_current_folder(recent_dir)
        dbname = self.dbstate.db.get_dbname()
        dialog.set_current_name(f"untitled_FTV_export_of_{dbname}.svg")

        response = dialog.run()

        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return

        file_name = dialog.get_filename()
        dir_name = os.path.dirname(file_name)
        self._config.set("paths.familytreeview-recent-export-dir", dir_name)
        dialog.destroy()

        if file_name[-4:].lower() != ".svg":
            file_name += ".svg"

        # TODO Catch errors of cairo write.
        # Can't find a way to catch cairo.IOError. Also,
        # os.access(os.path.dirname(file_name), os.W_OK) and
        # os.access(file_name, os.W_OK) don't help.

        # actual export
        canvas_bounds = self.widget_manager.canvas_manager.canvas_bounds
        padding = self.widget_manager.canvas_manager.canvas_padding
        width = canvas_bounds[2]-canvas_bounds[0]-2*padding+2*self.export_padding
        height = canvas_bounds[3]-canvas_bounds[1]-2*padding+2*self.export_padding
        with cairo.SVGSurface(file_name, width, height) as surface:
            context = cairo.Context(surface)
            context.translate(
                -canvas_bounds[0]-padding+self.export_padding,
                -canvas_bounds[1]-padding+self.export_padding
            )
            self.render_canvas_to_context(context)
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

    def render_canvas_to_context(self, context, bounds=None):
        hide_expanders = self._config.get("interaction.familytreeview-printing-export-hide-expanders")
        if hide_expanders:
            self.widget_manager.canvas_manager.set_expander_visible(False)
        try:
            self.widget_manager.canvas_manager.canvas.render(context, bounds, 1.0)
        finally:
            if hide_expanders:
                self.widget_manager.canvas_manager.set_expander_visible(True)
