#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2025-      ztlxltl
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
import os
import sys
import unittest

# Since the test runs without Gramps, prevent warnings by specifying a
# version.
from gi import require_version
require_version("Gtk", "3.0")
require_version("Pango", "1.0")

try:
    sys.path.append(os.environ["GRAMPSDIR"])
except KeyError:
    print("run\n    export GRAMPSDIR=~/Gramps\nor equivalent")
    exit()

from gramps.gen.lib import Name, NameOriginType, Surname
from gramps.gen.display.name import displayer as name_displayer

sys.path.append("src")

from abbreviated_name_display import AbbreviatedNameDisplay
from family_tree_view_config_provider_names import DEFAULT_ABBREV_RULES


# Dummy classes

class DummyDisplayState:
    def connect(*args):
        pass

class DummyFamilyTreeView:
    def __init__(self, config):
        self._config = config
        self.uistate = DummyDisplayState()
        pass

    def connect(*args):
        pass


def get_dummy_ftv(
    num, always=True,
    all_caps_style="all_caps",
    call_name_style="none", call_name_mode="call",
    primary_surname_style="none", primary_surname_mode="primary_surname",
    rules=None
):
    return DummyFamilyTreeView({
        "names.familytreeview-abbrev-name-format-id": num,
        "names.familytreeview-abbrev-name-format-always": always,
        "names.familytreeview-abbrev-name-all-caps-style": all_caps_style,
        "names.familytreeview-abbrev-name-call-name-style": call_name_style,
        "names.familytreeview-abbrev-name-call-name-mode": call_name_mode,
        "names.familytreeview-abbrev-name-primary-surname-style": primary_surname_style,
        "names.familytreeview-abbrev-name-primary-surname-mode": primary_surname_mode,
        "names.familytreeview-name-abbrev-rules": deepcopy(DEFAULT_ABBREV_RULES) if rules is None else rules
    })

# Actual tests

class NameAbbreviationTest(unittest.TestCase):
    def tearDown(self):
        name_displayer.clear_custom_formats()

    def _add_custom_name_format(self, name_format):
        name_displayer.add_name_format(name_format, name_format)

    def _test_name_with_num(
        self, name, num, result,
        all_caps_style="all_caps",
        call_name_style="none",
        primary_surname_style="none"
    ):
        abbrev_name_display = AbbreviatedNameDisplay(get_dummy_ftv(
            num, always=True,
            all_caps_style=all_caps_style,
            call_name_style=call_name_style,
            primary_surname_style=primary_surname_style
        ))

        name_num = abbrev_name_display.get_num_for_name_abbrev(name)
        assert name_num == num # get_dummy_ftv: always=True

        abbrev_names = abbrev_name_display.get_abbreviated_names(name, name_num)
        self.assertEqual(abbrev_names, result)

    def _test_example_name_with_num(
        self, num, result,
        all_caps_style="all_caps",
        call_name_style="none",
        primary_surname_style="none"
    ):
        name = Name()
        name.set_first_name("Edwin Jose")
        name.set_call_name("Jose")
        name.set_title("Dr.")
        name.set_suffix("Sr")
        name.set_nick_name("Ed")

        example_surname_1 = Surname()
        example_surname_1.set_primary(True)
        example_surname_1.set_prefix("von der")
        example_surname_1.set_surname("Smith")
        example_surname_1.set_connector("and")
        name.add_surname(example_surname_1)

        example_surname_2 = Surname()
        example_surname_2.set_primary(False)
        example_surname_2.set_surname("Weston")
        name.add_surname(example_surname_2)

        example_surname_3 = Surname()
        example_surname_3.set_primary(False)
        example_surname_3.set_surname("Wilson")
        example_surname_3.set_origintype(NameOriginType(NameOriginType.PATRONYMIC))
        name.add_surname(example_surname_3)

        name.set_family_nick_name("Underhills")

        self._test_name_with_num(
            name, num, result,
            all_caps_style=all_caps_style,
            call_name_style=call_name_style,
            primary_surname_style=primary_surname_style
        )

    def _test_double_barrelled_and_prefixes_with_num(
        self, num, result,
        all_caps_style="all_caps",
        call_name_style="none",
        primary_surname_style="none"
    ):
        test_name = Name()
        test_name.set_first_name("Mary Anne Mary-Anne MaryAnne")
        test_name.set_call_name("Anne")

        for prefix, surname, connector, primary in [
            (None, "McCarthy", "-", False),
            (None, "O'Brien", None, True),
            (None, "FitzGerald-d'Este", None, False),
        ]:
            test_surname = Surname()
            test_surname.set_primary(primary)
            if prefix is not None:
                test_surname.set_prefix(prefix)
            test_surname.set_surname(surname)
            if connector is not None:
                test_surname.set_connector(connector)
            test_name.add_surname(test_surname)

        self._test_name_with_num(
            test_name, num, result,
            all_caps_style=all_caps_style,
            call_name_style=call_name_style,
            primary_surname_style=primary_surname_style
        )

    # tests with example name and different formats

    def test_example_name_with_num_1(self):
        self._test_example_name_with_num(
            1,
            [
                "von der Smith and Weston Wilson, Edwin Jose Sr",
                "von der Smith and Weston Wilson, E. Jose Sr",
                "von der Smith and Weston Wilson, E. J. Sr",
                "von der Smith a. Weston Wilson, E. J. Sr",
                "von d. Smith a. Weston Wilson, E. J. Sr",
                "v. d. Smith a. Weston Wilson, E. J. Sr",
                "v. d. Smith a. Weston W., E. J. Sr",
                "v. d. Smith a. W. W., E. J. Sr",
                "v. d. Smith a. W. W., J. Sr",
                "v. d. Smith a. W. W., J.",
                "v. d. Smith W. W., J.",
                "v. Smith W. W., J.",
                "Smith W. W., J.",
                "Smith W., J.",
                "Smith, J.",
                "S., J.",
                "S.",
            ]
        )

    def test_example_name_with_num_2(self):
        self._test_example_name_with_num(
            2,
            [
                "Edwin Jose von der Smith and Weston Wilson Sr",
                "E. Jose von der Smith and Weston Wilson Sr",
                "E. J. von der Smith and Weston Wilson Sr",
                "E. J. von der Smith a. Weston Wilson Sr",
                "E. J. von d. Smith a. Weston Wilson Sr",
                "E. J. v. d. Smith a. Weston Wilson Sr",
                "E. J. v. d. Smith a. Weston W. Sr",
                "E. J. v. d. Smith a. W. W. Sr",
                "J. v. d. Smith a. W. W. Sr",
                "J. v. d. Smith a. W. W.",
                "J. v. d. Smith W. W.",
                "J. v. Smith W. W.",
                "J. Smith W. W.",
                "J. Smith W.",
                "J. Smith",
                "J. S.",
                "S.",
            ]
        )

    # 3 (PTFN) is deprecated

    def test_example_name_with_num_4(self):
        self._test_example_name_with_num(
            4,
            [
                "Edwin Jose",
                "E. Jose",
                "E. J.",
                "J.",
                "",
            ]
        )

    def test_example_name_with_num_5(self):
        self._test_example_name_with_num(
            5,
            [
                "Smith and Weston, Edwin Jose Wilson Sr von der",
                "Smith and Weston, E. Jose Wilson Sr von der",
                "Smith and Weston, E. J. Wilson Sr von der",
                "Smith a. Weston, E. J. Wilson Sr von der",
                "Smith a. Weston, E. J. Wilson Sr von d.",
                "Smith a. Weston, E. J. Wilson Sr v. d.",
                "Smith a. Weston, E. J. W. Sr v. d.",
                "Smith a. W., E. J. W. Sr v. d.",
                "Smith a. W., J. W. Sr v. d.",
                "Smith a. W., J. W. v. d.",
                "Smith a. W., J. W. v.",
                "Smith a. W., J. W.",
                "Smith W., J. W.",
                "Smith W., J.",
                "Smith, J.",
                "S., J.",
                "S.",
            ]
        )

    # tests with double barrelled name and prefixes and different all
    # caps styles

    def test_double_barrelled_and_prefixes_with_num_1(self):
        self._test_double_barrelled_and_prefixes_with_num(
            1,
            [
                "McCarthy-O'Brien FitzGerald-d'Este, Mary Anne Mary-Anne MaryAnne",
                "McCarthy-O'Brien FitzGerald-d'Este, Mary Anne Mary-Anne MaryA.",
                "McCarthy-O'Brien FitzGerald-d'Este, Mary Anne Mary-Anne M.A.",
                "McCarthy-O'Brien FitzGerald-d'Este, Mary Anne Mary-A. M.A.",
                "McCarthy-O'Brien FitzGerald-d'Este, Mary Anne M.-A. M.A.",
                "McCarthy-O'Brien FitzGerald-d'Este, M. Anne M.-A. M.A.",
                "McCarthy-O'Brien FitzGerald-d'Este, M. A. M.-A. M.A.",
                "McCarthy-O'Brien FitzGerald-d'E., M. A. M.-A. M.A.",
                "McCarthy-O'Brien FitzG.-d'E., M. A. M.-A. M.A.",
                "McC.-O'Brien FitzG.-d'E., M. A. M.-A. M.A.",
                "McC.-O'Brien FitzG.-d'E., M. A. M.-A.", # TODO maybe don't remove M.A. together?
                "McC.-O'Brien FitzG.-d'E., M. A. M.",
                "McC.-O'Brien FitzG.-d'E., M. A.",
                "McC.-O'Brien FitzG.-d'E., A.",
                "McC. O'Brien FitzG.-d'E., A.",
                "McC. O'Brien FitzG., A.",
                "McC. O'Brien, A.",
                "O'Brien, A.",
                "O'B., A.",
                "O'B.",
            ]
        )

    def test_double_barrelled_and_prefixes_with_num_1_all_caps(self):
        self._add_custom_name_format("SURNAME, GIVEN SUFFIX")
        self._test_double_barrelled_and_prefixes_with_num(
            -1,
            [
                "McCARTHY-O'BRIEN FitzGERALD-d'ESTE, MARY ANNE MARY-ANNE MARYANNE",
                "McCARTHY-O'BRIEN FitzGERALD-d'ESTE, MARY ANNE MARY-ANNE MARYA.",
                "McCARTHY-O'BRIEN FitzGERALD-d'ESTE, MARY ANNE MARY-ANNE M.A.",
                "McCARTHY-O'BRIEN FitzGERALD-d'ESTE, MARY ANNE MARY-A. M.A.",
                "McCARTHY-O'BRIEN FitzGERALD-d'ESTE, MARY ANNE M.-A. M.A.",
                "McCARTHY-O'BRIEN FitzGERALD-d'ESTE, M. ANNE M.-A. M.A.",
                "McCARTHY-O'BRIEN FitzGERALD-d'ESTE, M. A. M.-A. M.A.",
                "McCARTHY-O'BRIEN FitzGERALD-d'E., M. A. M.-A. M.A.",
                "McCARTHY-O'BRIEN FitzG.-d'E., M. A. M.-A. M.A.",
                "McC.-O'BRIEN FitzG.-d'E., M. A. M.-A. M.A.",
                "McC.-O'BRIEN FitzG.-d'E., M. A. M.-A.",
                "McC.-O'BRIEN FitzG.-d'E., M. A. M.",
                "McC.-O'BRIEN FitzG.-d'E., M. A.",
                "McC.-O'BRIEN FitzG.-d'E., A.",
                "McC. O'BRIEN FitzG.-d'E., A.",
                "McC. O'BRIEN FitzG., A.",
                "McC. O'BRIEN, A.",
                "O'BRIEN, A.",
                "O'B., A.",
                "O'B.",
            ]
        )

    def test_double_barrelled_and_prefixes_with_num_1_small_caps(self):
        self._add_custom_name_format("SURNAME, GIVEN SUFFIX")
        self._test_double_barrelled_and_prefixes_with_num(
            -1,
            [
                "M<small>C</small>C<small>ARTHY</small>-O'B<small>RIEN</small> F<small>ITZ</small>G<small>ERALD</small>-<small>D</small>'E<small>STE</small>, M<small>ARY</small> A<small>NNE</small> M<small>ARY</small>-A<small>NNE</small> M<small>ARY</small>A<small>NNE</small>",
                "M<small>C</small>C<small>ARTHY</small>-O'B<small>RIEN</small> F<small>ITZ</small>G<small>ERALD</small>-<small>D</small>'E<small>STE</small>, M<small>ARY</small> A<small>NNE</small> M<small>ARY</small>-A<small>NNE</small> M<small>ARY</small>A.",
                "M<small>C</small>C<small>ARTHY</small>-O'B<small>RIEN</small> F<small>ITZ</small>G<small>ERALD</small>-<small>D</small>'E<small>STE</small>, M<small>ARY</small> A<small>NNE</small> M<small>ARY</small>-A<small>NNE</small> M.A.",
                "M<small>C</small>C<small>ARTHY</small>-O'B<small>RIEN</small> F<small>ITZ</small>G<small>ERALD</small>-<small>D</small>'E<small>STE</small>, M<small>ARY</small> A<small>NNE</small> M<small>ARY</small>-A. M.A.",
                "M<small>C</small>C<small>ARTHY</small>-O'B<small>RIEN</small> F<small>ITZ</small>G<small>ERALD</small>-<small>D</small>'E<small>STE</small>, M<small>ARY</small> A<small>NNE</small> M.-A. M.A.",
                "M<small>C</small>C<small>ARTHY</small>-O'B<small>RIEN</small> F<small>ITZ</small>G<small>ERALD</small>-<small>D</small>'E<small>STE</small>, M. A<small>NNE</small> M.-A. M.A.",
                "M<small>C</small>C<small>ARTHY</small>-O'B<small>RIEN</small> F<small>ITZ</small>G<small>ERALD</small>-<small>D</small>'E<small>STE</small>, M. A. M.-A. M.A.",
                "M<small>C</small>C<small>ARTHY</small>-O'B<small>RIEN</small> F<small>ITZ</small>G<small>ERALD</small>-<small>D</small>'E., M. A. M.-A. M.A.",
                "M<small>C</small>C<small>ARTHY</small>-O'B<small>RIEN</small> F<small>ITZ</small>G.-<small>D</small>'E., M. A. M.-A. M.A.",
                "M<small>C</small>C.-O'B<small>RIEN</small> F<small>ITZ</small>G.-<small>D</small>'E., M. A. M.-A. M.A.",
                "M<small>C</small>C.-O'B<small>RIEN</small> F<small>ITZ</small>G.-<small>D</small>'E., M. A. M.-A.",
                "M<small>C</small>C.-O'B<small>RIEN</small> F<small>ITZ</small>G.-<small>D</small>'E., M. A. M.",
                "M<small>C</small>C.-O'B<small>RIEN</small> F<small>ITZ</small>G.-<small>D</small>'E., M. A.",
                "M<small>C</small>C.-O'B<small>RIEN</small> F<small>ITZ</small>G.-<small>D</small>'E., A.",
                "M<small>C</small>C. O'B<small>RIEN</small> F<small>ITZ</small>G.-<small>D</small>'E., A.",
                "M<small>C</small>C. O'B<small>RIEN</small> F<small>ITZ</small>G., A.",
                "M<small>C</small>C. O'B<small>RIEN</small>, A.",
                "O'B<small>RIEN</small>, A.",
                "O'B., A.",
                "O'B.",
            ],
            all_caps_style="small_caps"
        )

    def test_double_barrelled_and_prefixes_with_num_1_bold(self):
        self._add_custom_name_format("SURNAME, GIVEN SUFFIX")
        self._test_double_barrelled_and_prefixes_with_num(
            -1,
            [
                "<b>Mc</b><b>Carthy</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>Gerald</b>-<b>d'</b><b>Este</b>, <b>Mary</b> <b>Anne</b> <b>Mary</b>-<b>Anne</b> <b>Mary</b><b>Anne</b>",
                "<b>Mc</b><b>Carthy</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>Gerald</b>-<b>d'</b><b>Este</b>, <b>Mary</b> <b>Anne</b> <b>Mary</b>-<b>Anne</b> <b>Mary</b><b>A.</b>",
                "<b>Mc</b><b>Carthy</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>Gerald</b>-<b>d'</b><b>Este</b>, <b>Mary</b> <b>Anne</b> <b>Mary</b>-<b>Anne</b> <b>M.A.</b>",
                "<b>Mc</b><b>Carthy</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>Gerald</b>-<b>d'</b><b>Este</b>, <b>Mary</b> <b>Anne</b> <b>Mary</b>-<b>A.</b> <b>M.A.</b>",
                "<b>Mc</b><b>Carthy</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>Gerald</b>-<b>d'</b><b>Este</b>, <b>Mary</b> <b>Anne</b> <b>M.</b>-<b>A.</b> <b>M.A.</b>",
                "<b>Mc</b><b>Carthy</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>Gerald</b>-<b>d'</b><b>Este</b>, <b>M.</b> <b>Anne</b> <b>M.</b>-<b>A.</b> <b>M.A.</b>",
                "<b>Mc</b><b>Carthy</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>Gerald</b>-<b>d'</b><b>Este</b>, <b>M.</b> <b>A.</b> <b>M.</b>-<b>A.</b> <b>M.A.</b>",
                "<b>Mc</b><b>Carthy</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>Gerald</b>-<b>d'</b><b>E.</b>, <b>M.</b> <b>A.</b> <b>M.</b>-<b>A.</b> <b>M.A.</b>",
                "<b>Mc</b><b>Carthy</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>G.</b>-<b>d'</b><b>E.</b>, <b>M.</b> <b>A.</b> <b>M.</b>-<b>A.</b> <b>M.A.</b>",
                "<b>Mc</b><b>C.</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>G.</b>-<b>d'</b><b>E.</b>, <b>M.</b> <b>A.</b> <b>M.</b>-<b>A.</b> <b>M.A.</b>",
                "<b>Mc</b><b>C.</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>G.</b>-<b>d'</b><b>E.</b>, <b>M.</b> <b>A.</b> <b>M.</b>-<b>A.</b>",
                "<b>Mc</b><b>C.</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>G.</b>-<b>d'</b><b>E.</b>, <b>M.</b> <b>A.</b> <b>M.</b>",
                "<b>Mc</b><b>C.</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>G.</b>-<b>d'</b><b>E.</b>, <b>M.</b> <b>A.</b>",
                "<b>Mc</b><b>C.</b>-<b>O'</b><b>Brien</b> <b>Fitz</b><b>G.</b>-<b>d'</b><b>E.</b>, <b>A.</b>",
                "<b>Mc</b><b>C.</b> <b>O'</b><b>Brien</b> <b>Fitz</b><b>G.</b>-<b>d'</b><b>E.</b>, <b>A.</b>",
                "<b>Mc</b><b>C.</b> <b>O'</b><b>Brien</b> <b>Fitz</b><b>G.</b>, <b>A.</b>",
                "<b>Mc</b><b>C.</b> <b>O'</b><b>Brien</b>, <b>A.</b>",
                "<b>O'</b><b>Brien</b>, <b>A.</b>",
                "<b>O'B.</b>, <b>A.</b>",
                "<b>O'B.</b>",
            ],
            all_caps_style="bold"
        )

    # tests with combined styles

    def test_example_name_with_num_1_combined_1(self):
        """bold (primary surname) in small caps (all caps)"""
        self._add_custom_name_format("SURNAME, Given Suffix")
        self._test_example_name_with_num(
            -1,
            [
                "<small>VON</small> <small>DER</small> <b>S<small>MITH</small></b> <small>AND</small> W<small>ESTON</small> W<small>ILSON</small>, Edwin <u>Jose</u> Sr",
                "<small>VON</small> <small>DER</small> <b>S<small>MITH</small></b> <small>AND</small> W<small>ESTON</small> W<small>ILSON</small>, E. <u>Jose</u> Sr",
                "<small>VON</small> <small>DER</small> <b>S<small>MITH</small></b> <small>AND</small> W<small>ESTON</small> W<small>ILSON</small>, E. <u>J.</u> Sr",
                "<small>VON</small> <small>DER</small> <b>S<small>MITH</small></b> <small>A</small>. W<small>ESTON</small> W<small>ILSON</small>, E. <u>J.</u> Sr",
                "<small>VON</small> <small>D</small>. <b>S<small>MITH</small></b> <small>A</small>. W<small>ESTON</small> W<small>ILSON</small>, E. <u>J.</u> Sr",
                "<small>V</small>. <small>D</small>. <b>S<small>MITH</small></b> <small>A</small>. W<small>ESTON</small> W<small>ILSON</small>, E. <u>J.</u> Sr",
                "<small>V</small>. <small>D</small>. <b>S<small>MITH</small></b> <small>A</small>. W<small>ESTON</small> W., E. <u>J.</u> Sr",
                "<small>V</small>. <small>D</small>. <b>S<small>MITH</small></b> <small>A</small>. W. W., E. <u>J.</u> Sr",
                "<small>V</small>. <small>D</small>. <b>S<small>MITH</small></b> <small>A</small>. W. W., <u>J.</u> Sr",
                "<small>V</small>. <small>D</small>. <b>S<small>MITH</small></b> <small>A</small>. W. W., <u>J.</u>",
                "<small>V</small>. <small>D</small>. <b>S<small>MITH</small></b> W. W., <u>J.</u>",
                "<small>V</small>. <b>S<small>MITH</small></b> W. W., <u>J.</u>",
                "<b>S<small>MITH</small></b> W. W., <u>J.</u>",
                "<b>S<small>MITH</small></b> W., <u>J.</u>",
                "<b>S<small>MITH</small></b>, <u>J.</u>",
                "<b>S.</b>, <u>J.</u>",
                "<b>S.</b>",
            ],
            all_caps_style="small_caps",
            call_name_style="underline",
            primary_surname_style="bold",
        )

    def test_example_name_with_num_1_combined_2(self):
        """small caps (primary surname) in bold (all caps)"""
        self._add_custom_name_format("SURNAME, Given Suffix")
        self._test_example_name_with_num(
            -1,
            [
                "<b>von</b> <b>der</b> <b>S<small>MITH</small></b> <b>and</b> <b>Weston</b> <b>Wilson</b>, Edwin <i>Jose</i> Sr",
                "<b>von</b> <b>der</b> <b>S<small>MITH</small></b> <b>and</b> <b>Weston</b> <b>Wilson</b>, E. <i>Jose</i> Sr",
                "<b>von</b> <b>der</b> <b>S<small>MITH</small></b> <b>and</b> <b>Weston</b> <b>Wilson</b>, E. <i>J.</i> Sr",
                "<b>von</b> <b>der</b> <b>S<small>MITH</small></b> <b>a.</b> <b>Weston</b> <b>Wilson</b>, E. <i>J.</i> Sr",
                "<b>von</b> <b>d.</b> <b>S<small>MITH</small></b> <b>a.</b> <b>Weston</b> <b>Wilson</b>, E. <i>J.</i> Sr",
                "<b>v.</b> <b>d.</b> <b>S<small>MITH</small></b> <b>a.</b> <b>Weston</b> <b>Wilson</b>, E. <i>J.</i> Sr",
                "<b>v.</b> <b>d.</b> <b>S<small>MITH</small></b> <b>a.</b> <b>Weston</b> <b>W.</b>, E. <i>J.</i> Sr",
                "<b>v.</b> <b>d.</b> <b>S<small>MITH</small></b> <b>a.</b> <b>W.</b> <b>W.</b>, E. <i>J.</i> Sr",
                "<b>v.</b> <b>d.</b> <b>S<small>MITH</small></b> <b>a.</b> <b>W.</b> <b>W.</b>, <i>J.</i> Sr",
                "<b>v.</b> <b>d.</b> <b>S<small>MITH</small></b> <b>a.</b> <b>W.</b> <b>W.</b>, <i>J.</i>",
                "<b>v.</b> <b>d.</b> <b>S<small>MITH</small></b> <b>W.</b> <b>W.</b>, <i>J.</i>",
                "<b>v.</b> <b>S<small>MITH</small></b> <b>W.</b> <b>W.</b>, <i>J.</i>",
                "<b>S<small>MITH</small></b> <b>W.</b> <b>W.</b>, <i>J.</i>",
                "<b>S<small>MITH</small></b> <b>W.</b>, <i>J.</i>",
                "<b>S<small>MITH</small></b>, <i>J.</i>",
                "<b>S.</b>, <i>J.</i>",
                "<b>S.</b>",
            ],
            all_caps_style="bold",
            call_name_style="italic",
            primary_surname_style="small_caps",
        )

    def test_example_name_with_num_1_combined_3(self):
        """small caps (primary surname) in bold (all caps)"""
        self._add_custom_name_format("SURNAME, Given Suffix")
        self._test_example_name_with_num(
            -1,
            [
                "<small><small>VON</small></small> <small><small>DER</small></small> S<small>MITH</small> <small><small>AND</small></small> W<small><small>ESTON</small></small> W<small><small>ILSON</small></small>, Edwin <b>Jose</b> Sr",
                "<small><small>VON</small></small> <small><small>DER</small></small> S<small>MITH</small> <small><small>AND</small></small> W<small><small>ESTON</small></small> W<small><small>ILSON</small></small>, E. <b>Jose</b> Sr",
                "<small><small>VON</small></small> <small><small>DER</small></small> S<small>MITH</small> <small><small>AND</small></small> W<small><small>ESTON</small></small> W<small><small>ILSON</small></small>, E. <b>J.</b> Sr",
                "<small><small>VON</small></small> <small><small>DER</small></small> S<small>MITH</small> <small><small>A</small></small>. W<small><small>ESTON</small></small> W<small><small>ILSON</small></small>, E. <b>J.</b> Sr",
                "<small><small>VON</small></small> <small><small>D</small></small>. S<small>MITH</small> <small><small>A</small></small>. W<small><small>ESTON</small></small> W<small><small>ILSON</small></small>, E. <b>J.</b> Sr",
                "<small><small>V</small></small>. <small><small>D</small></small>. S<small>MITH</small> <small><small>A</small></small>. W<small><small>ESTON</small></small> W<small><small>ILSON</small></small>, E. <b>J.</b> Sr",
                "<small><small>V</small></small>. <small><small>D</small></small>. S<small>MITH</small> <small><small>A</small></small>. W<small><small>ESTON</small></small> W., E. <b>J.</b> Sr",
                "<small><small>V</small></small>. <small><small>D</small></small>. S<small>MITH</small> <small><small>A</small></small>. W. W., E. <b>J.</b> Sr",
                "<small><small>V</small></small>. <small><small>D</small></small>. S<small>MITH</small> <small><small>A</small></small>. W. W., <b>J.</b> Sr",
                "<small><small>V</small></small>. <small><small>D</small></small>. S<small>MITH</small> <small><small>A</small></small>. W. W., <b>J.</b>",
                "<small><small>V</small></small>. <small><small>D</small></small>. S<small>MITH</small> W. W., <b>J.</b>",
                "<small><small>V</small></small>. S<small>MITH</small> W. W., <b>J.</b>",
                "S<small>MITH</small> W. W., <b>J.</b>",
                "S<small>MITH</small> W., <b>J.</b>",
                "S<small>MITH</small>, <b>J.</b>",
                "S., <b>J.</b>",
                "S.",
            ],
            all_caps_style="petite_caps",
            call_name_style="bold",
            primary_surname_style="small_caps",
        )

if __name__ == "__main__":
    unittest.main()
