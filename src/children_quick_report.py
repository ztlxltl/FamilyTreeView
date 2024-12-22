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


from gramps.gen.simple import SimpleAccess, SimpleDoc
from gramps.gen.const import GRAMPS_LOCALE
from gramps.gui.plug.quick import QuickTable


_ = GRAMPS_LOCALE.translation.gettext

def run(database, document, person):
    """
    Loops through the families that the person is a parent in, and display
    the information about the children.
    """

    # setup the simple access functions
    sdb = SimpleAccess(database)
    sdoc = SimpleDoc(document)

    # display the title
    sdoc.title(_("Children of %s") % sdb.name(person))
    sdoc.paragraph("")

    stab = QuickTable(sdb)
    sdoc.header1(_("Children"))
    stab.columns(
        _("Person"),
        _("Gender"),
        _("Date")
    )

    # loop through each family in which the person is a parent
    for family in sdb.parent_in(person):
        # loop through each child in the family
        for child in sdb.children(family):
            stab.row(
                child,
                sdb.gender(child),
                sdb.birth_date(child)
            )
            document.has_data = True
    stab.write(sdoc)
