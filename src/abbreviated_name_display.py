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


import re

from gramps.gen.const import GRAMPS_LOCALE
from gramps.gen.display.name import (
    _CONNECTOR_IN_LIST, _F_FMT, _ORIGINMATRO, _ORIGINPATRO, _PREFIX_IN_LIST,
    _PRIMARY_IN_LIST, _SURNAME_IN_LIST, _TYPE_IN_LIST, PAT_AS_SURN,
    displayer as name_displayer, _make_cmp_key, cleanup_name
)


_ = GRAMPS_LOCALE.translation.gettext

def _raw_full_surname(raw_surn_data_list):
    """method for the 'l' symbol: full surnames"""
    result = []
    global PAT_AS_SURN
    nrsur = len(raw_surn_data_list)
    for raw_surn_data in raw_surn_data_list:
        if raw_surn_data[_PRIMARY_IN_LIST]:
            #if there are multiple surnames, return the primary. If there
            #is only one surname, then primary has little meaning, and we
            #assume a pa/matronymic should not be given as primary as it
            #normally is defined independently
            if not PAT_AS_SURN and nrsur == 1 and \
                    (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO
                    or raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
                pass # add surname without "primary-"
            else:
                if len(result) > 0:
                    result += [" "]
                result += [
                    ("primary-prefix", raw_surn_data[_PREFIX_IN_LIST]),
                    " " if raw_surn_data[_PREFIX_IN_LIST] and raw_surn_data[_SURNAME_IN_LIST] else "",
                    ("primary-surname", raw_surn_data[_SURNAME_IN_LIST]),
                    " " if raw_surn_data[_SURNAME_IN_LIST] and raw_surn_data[_CONNECTOR_IN_LIST] else "",
                    ("primary-connector", raw_surn_data[_CONNECTOR_IN_LIST])
                ]
                continue # add surname only once
        if len(result) > 0:
            result += [" "]
        result += [
            ("prefix", raw_surn_data[_PREFIX_IN_LIST]),
            " " if raw_surn_data[_PREFIX_IN_LIST] and raw_surn_data[_SURNAME_IN_LIST] else "",
            ("surname", raw_surn_data[_SURNAME_IN_LIST]),
            " " if raw_surn_data[_SURNAME_IN_LIST] and raw_surn_data[_CONNECTOR_IN_LIST] else "",
            ("connector", raw_surn_data[_CONNECTOR_IN_LIST])
        ]
    return result

def _raw_primary_surname(raw_surn_data_list):
    """method for the 'm' symbol: primary surname"""
    global PAT_AS_SURN
    nrsur = len(raw_surn_data_list)
    for raw_surn_data in raw_surn_data_list:
        if raw_surn_data[_PRIMARY_IN_LIST]:
            #if there are multiple surnames, return the primary. If there
            #is only one surname, then primary has little meaning, and we
            #assume a pa/matronymic should not be given as primary as it
            #normally is defined independently
            if not PAT_AS_SURN and nrsur == 1 and \
                    (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO
                    or raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
                return []
            else:
                result = [
                    ("prefix", raw_surn_data[_PREFIX_IN_LIST]),
                    " " if raw_surn_data[_PREFIX_IN_LIST] and raw_surn_data[_SURNAME_IN_LIST] else "",
                    ("surname", raw_surn_data[_SURNAME_IN_LIST]),
                    " " if raw_surn_data[_SURNAME_IN_LIST] and raw_surn_data[_CONNECTOR_IN_LIST] else "",
                    ("connector", raw_surn_data[_CONNECTOR_IN_LIST])
                ]
                return result
    return []

def _raw_primary_surname_only(raw_surn_data_list):
    """method to obtain the raw primary surname data, so this returns a string
    """
    global PAT_AS_SURN
    nrsur = len(raw_surn_data_list)
    for raw_surn_data in raw_surn_data_list:
        if raw_surn_data[_PRIMARY_IN_LIST]:
            if not PAT_AS_SURN and nrsur == 1 and \
                    (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO
                    or raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
                return []
            else:
                return [("primary-surname", raw_surn_data[_SURNAME_IN_LIST])]
    return []

def _raw_primary_prefix_only(raw_surn_data_list):
    """method to obtain the raw primary surname data"""
    global PAT_AS_SURN
    nrsur = len(raw_surn_data_list)
    for raw_surn_data in raw_surn_data_list:
        if raw_surn_data[_PRIMARY_IN_LIST]:
            if not PAT_AS_SURN and nrsur == 1 and \
                    (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO
                    or raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
                return []
            else:
                return [("primary-prefix", raw_surn_data[_PREFIX_IN_LIST])]
    return []

def _raw_primary_conn_only(raw_surn_data_list):
    """method to obtain the raw primary surname data"""
    global PAT_AS_SURN
    nrsur = len(raw_surn_data_list)
    for raw_surn_data in raw_surn_data_list:
        if raw_surn_data[_PRIMARY_IN_LIST]:
            if not PAT_AS_SURN and nrsur == 1 and \
                    (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO
                    or raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
                return []
            else:
                return [("primary-connector", raw_surn_data[_CONNECTOR_IN_LIST])]
    return []

def _raw_patro_surname(raw_surn_data_list):
    """method for the 'y' symbol: patronymic surname"""
    for raw_surn_data in raw_surn_data_list:
        if (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO or
            raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
            result = [
                    ("prefix", raw_surn_data[_PREFIX_IN_LIST]),
                    " " if raw_surn_data[_PREFIX_IN_LIST] and raw_surn_data[_SURNAME_IN_LIST] else "",
                    ("surname", raw_surn_data[_SURNAME_IN_LIST]),
                    " " if raw_surn_data[_SURNAME_IN_LIST] and raw_surn_data[_CONNECTOR_IN_LIST] else "",
                    ("connector", raw_surn_data[_CONNECTOR_IN_LIST])
                ]
            return result
    return []

def _raw_patro_surname_only(raw_surn_data_list):
    """method for the '1y' symbol: patronymic surname only"""
    for raw_surn_data in raw_surn_data_list:
        if (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO or
            raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
            result = [("surname", raw_surn_data[_SURNAME_IN_LIST])]
            return result
    return []

def _raw_patro_prefix_only(raw_surn_data_list):
    """method for the '0y' symbol: patronymic prefix only"""
    for raw_surn_data in raw_surn_data_list:
        if (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO or
            raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
            result = [("prefix", raw_surn_data[_PREFIX_IN_LIST])]
            return result
    return []

def _raw_patro_conn_only(raw_surn_data_list):
    """method for the '2y' symbol: patronymic conn only"""
    for raw_surn_data in raw_surn_data_list:
        if (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO or
            raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
            result = [("connector", raw_surn_data[_CONNECTOR_IN_LIST])]
            return result
    return []

def _raw_nonpatro_surname(raw_surn_data_list):
    """method for the 'o' symbol: full surnames without pa/matronymic or
       primary
    """
    result = []
    for raw_surn_data in raw_surn_data_list:
        if ((not raw_surn_data[_PRIMARY_IN_LIST]) and
            raw_surn_data[_TYPE_IN_LIST][0] != _ORIGINPATRO and
            raw_surn_data[_TYPE_IN_LIST][0] != _ORIGINMATRO):
            if len(result) > 0:
                result += [" "]
            result += [
                ("prefix", raw_surn_data[_PREFIX_IN_LIST]),
                " " if raw_surn_data[_PREFIX_IN_LIST] and raw_surn_data[_SURNAME_IN_LIST] else "",
                ("surname", raw_surn_data[_SURNAME_IN_LIST]),
                " " if raw_surn_data[_SURNAME_IN_LIST] and raw_surn_data[_CONNECTOR_IN_LIST] else "",
                ("connector", raw_surn_data[_CONNECTOR_IN_LIST])
            ]
    return result

def _raw_nonprimary_surname(raw_surn_data_list):
    """method for the 'r' symbol: nonprimary surnames"""
    result = []
    for raw_surn_data in raw_surn_data_list:
        if not raw_surn_data[_PRIMARY_IN_LIST]:
            if len(result) > 0:
                result += [" "]
            result += [
                ("prefix", raw_surn_data[_PREFIX_IN_LIST]),
                " " if raw_surn_data[_PREFIX_IN_LIST] and raw_surn_data[_SURNAME_IN_LIST] else "",
                ("surname", raw_surn_data[_SURNAME_IN_LIST]),
                " " if raw_surn_data[_SURNAME_IN_LIST] and raw_surn_data[_CONNECTOR_IN_LIST] else "",
                ("connector", raw_surn_data[_CONNECTOR_IN_LIST])
            ]
    return result

def _raw_prefix_surname(raw_surn_data_list):
    """method for the 'p' symbol: all prefixes"""
    result = []
    global PAT_AS_SURN
    nrsur = len(raw_surn_data_list)
    for raw_surn_data in raw_surn_data_list:
        if raw_surn_data[_PRIMARY_IN_LIST]:
            if not PAT_AS_SURN and nrsur == 1 and \
                    (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO
                    or raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
                pass
            else:
                if len(result) > 0:
                    result.append(" ")
                result.append(("primary-prefix", raw_surn_data[_PREFIX_IN_LIST]))
                continue
        if len(result) > 0:
            result.append(" ")
        result.append(("prefix", raw_surn_data[_PREFIX_IN_LIST]))
    return result

def _raw_single_surname(raw_surn_data_list):
    """method for the 'q' symbol: surnames without prefix and connectors"""
    result = []
    global PAT_AS_SURN
    nrsur = len(raw_surn_data_list)
    for raw_surn_data in raw_surn_data_list:
        if raw_surn_data[_PRIMARY_IN_LIST]:
            if not PAT_AS_SURN and nrsur == 1 and \
                    (raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINPATRO
                    or raw_surn_data[_TYPE_IN_LIST][0] == _ORIGINMATRO):
                pass
            else:
                if len(result) > 0:
                    result.append(" ")
                result.append(("primary-surname", raw_surn_data[_SURNAME_IN_LIST]))
                continue
        if len(result) > 0:
            result.append(" ")
        result.append(("surname", raw_surn_data[_SURNAME_IN_LIST]))
    return result


class AbbreviatedNameDisplay():
    def __init__(self):
        self.step_description = None

    def get_abbreviated_names(self, name, return_step_description=False):
        """
        Returns a list of strings with abbreviations of the given name object.
        The returned list is ordered by decreasing name length.

        Basic rules:
        1. Non-call given names are abbreviated (one by one starting with last)
        2. Call given name is abbreviated after other given names
        3. Prefixes are abbreviated (one by one starting with last, non-primary first)
        4. Non-primary family names are abbreviated
        5. Non-call given name abbreviations are removed

        Example:
        - Garner von Zieliński, Lewis Anderson Sr
        - Garner von Zieliński, L. Anderson Sr
        - Garner von Zieliński, L. A. Sr
        - Garner v. Zieliński, L. A. Sr
        - G. v. Zieliński, L. A. Sr
        - G. v. Zieliński, A. Sr

        Prefixes which are part of a surname are not abbreviated (e.g. MacCarthy -> MacC., O'Brien -> O'B.)
        """

        self.step_description = []

        name_parts = self._get_name_parts(name)

        abbrev_name_list = []

        # full name
        full_name = self._name_from_parts(name_parts)
        abbrev_name_list.append(full_name)
        self.step_description.append("full name\n")

        # abbreviate given names
        while True:
            if not self._abbrev_one_given(name_parts):
                break
            abbrev_name_list.append(self._name_from_parts(name_parts))

        # abbreviate prefixes and connectors
        while True:
            if not self._abbrev_one_prefix_or_connector(name_parts):
                break
            abbrev_name_list.append(self._name_from_parts(name_parts))

        # abbreviate surnames
        while True:
            if not self._abbrev_one_surname(name_parts):
                break
            abbrev_name_list.append(self._name_from_parts(name_parts))

        # remove given names
        while True:
            if not self._remove_one_given(name_parts):
                break
            abbrev_name_list.append(self._name_from_parts(name_parts))

        step_description = self.step_description
        self.step_description = None
        if return_step_description:
            return abbrev_name_list, step_description
        return abbrev_name_list

    def _get_name_parts(self, name):
        format_str = self._get_format_str(name)
        d = {
            "t": ("('title', title)","title", _("Person|title")),
            "f": ("('given', first, first, call)","given", _("given")), # first two times so one can be abbreviated and second can be checked for call afterwards
            "l": ("_raw_full_surname(raw_surname_list)", "surname", _("surname")),
            "s": ("('suffix', suffix)", "suffix", _("suffix")),
            "c": ("('call', call)", "call", _("Name|call")),
            "x": ("((('nick', nick) if nick else False) or (('call', call) if call else False) or ('given0', first.split(' ')[0]))", "common", _("Name|common")),
            "i": ("('initials', ''.join([word[0] +'.' for word in ('. ' + first).split()][1:]))", "initials", _("initials")),
            "m": ("_raw_primary_surname(raw_surname_list)", "primary", _("Name|primary")),
            "0m":("_raw_primary_prefix_only(raw_surname_list)", "primary[pre]", _("primary[pre]")),
            "1m":("_raw_primary_surname_only(raw_surname_list)", "primary[sur]",_("primary[sur]")),
            "2m":("_raw_primary_conn_only(raw_surname_list)", "primary[con]", _("primary[con]")),
            "y": ("_raw_patro_surname(raw_surname_list)", "patronymic", _("patronymic")),
            "0y":("_raw_patro_prefix_only(raw_surname_list)", "patronymic[pre]", _("patronymic[pre]")),
            "1y":("_raw_patro_surname_only(raw_surname_list)", "patronymic[sur]", _("patronymic[sur]")),
            "2y":("_raw_patro_conn_only(raw_surname_list)", "patronymic[con]", _("patronymic[con]")),
            "o": ("_raw_nonpatro_surname(raw_surname_list)", "notpatronymic", _("notpatronymic")),
            "r": ("_raw_nonprimary_surname(raw_surname_list)", "rest", _("Remaining names|rest")),
            "p": ("_raw_prefix_surname(raw_surname_list)", "prefix", _("prefix")),
            "q": ("_raw_single_surname(raw_surname_list)", "rawsurnames", _("rawsurnames")),
            "n": ("('nick', nick)", "nickname", _("nickname")),
            "g": ("('famnick', famnick)", "familynick", _("familynick")),
        }
        first = name.first_name
        surname_list = name.surname_list
        raw_surname_list = [surn.serialize() for surn in surname_list]
        suffix = name.suffix
        title = name.title
        call = name.call
        nick = name.nick
        famnick = name.famnick

        raw_display_name_parts = self._make_name_parts(format_str, d)
        # raw_display_name_parts item examples:
        #   ('nickname', '"', "('nick', nick)", '"')
        #   ('surname', '', '_raw_full_surname(raw_surname_list)', '')

        display_name_parts = []
        for i in range(len(raw_display_name_parts)):
            if isinstance(raw_display_name_parts[i], str):
                if len(raw_display_name_parts[i]) > 0:
                    display_name_parts.append(raw_display_name_parts[i])
            else:
                raw_res = eval(raw_display_name_parts[i][2])
                if isinstance(raw_res, tuple):
                    raw_res = [raw_res]
                res = []
                for res_part in raw_res:
                    if isinstance(res_part, str):
                        if len(res_part) > 0:
                            res.append(res_part)
                    else:
                        if len(res_part[1]) > 0:
                            res.append(res_part)
                display_name_parts.append([raw_display_name_parts[i][0], raw_display_name_parts[i][1], res, raw_display_name_parts[i][3]])
        # display_name_parts item example:
        #   ('nickname', '"', [('nick', 'Big Louie')], '"')
        #   ('surname', '', [('surname', 'Garner'), ' ', ('primary-prefix', 'von'), ' ', ('primary-surname', 'Zieliński')], '')

        return display_name_parts

    def _get_format_str(self, name):
        num = name.display_as
        if num == 0:
            num = name_displayer.get_default_format()
        format_str = name_displayer.name_formats[num][_F_FMT]
        return format_str

    def _make_name_parts(self, format_str, d):
        """adapted from _make_fn"""

        if (len(format_str) > 2 and
            format_str[0] == format_str[-1] == '"'):
            pass
        else:
            d_keys = [(code, _tuple[2]) for code, _tuple in d.items()]
            d_keys.sort(key=_make_cmp_key, reverse=True) # reverse on length and by ikeyword
            for (code, ikeyword) in d_keys:
                exp, keyword, ikeyword = d[code]
                format_str = format_str.replace(ikeyword, "%"+ code)
                format_str = format_str.replace(ikeyword.title(), "%"+ code)
                format_str = format_str.replace(ikeyword.upper(), "%"+ code.upper())

        if (len(format_str) > 2 and
            format_str[0] == format_str[-1] == '"'):
            pass
        else:
            d_keys = [(code, _tuple[1]) for code, _tuple in d.items()]
            d_keys.sort(key=_make_cmp_key, reverse=True)
            for (code, keyword) in d_keys:
                exp, keyword, ikeyword = d[code]
                format_str = format_str.replace(keyword, "%"+ code)
                format_str = format_str.replace(keyword.title(), "%"+ code)
                format_str = format_str.replace(keyword.upper(), "%"+ code.upper())
        codes = list(d.keys()) + [c.upper() for c in d]
        if len(format_str) > 0 and format_str[0] == "!":
            patterns = ["%(" + ("|".join(codes)) + ")",]
            format_str = format_str[1:]
        else:
            patterns = [
                ",\\W*\"%(" + ("|".join(codes)) + ")\"",    # ,\W*"%s"
                ",\\W*\\(%(" + ("|".join(codes)) + ")\\)",  # ,\W*(%s)
                ",\\W*%(" + ("|".join(codes)) + ")",        # ,\W*%s
                "\"%(" + ("|".join(codes)) + ")\"",         # "%s"
                "_%(" + ("|".join(codes)) + ")_",           # _%s_
                "\\(%(" + ("|".join(codes)) + ")\\)",       # (%s)
                "%(" + ("|".join(codes)) + ")",             # %s
                ]

        pat = re.compile("|".join(patterns))
        res = []
        last_mat_end = 0
        mat = pat.search(format_str)
        while mat:
            if mat.start() > last_mat_end:
                res.append(format_str[last_mat_end:mat.start()])
            match_pattern = mat.group(0)
            p, code, s = re.split("%(.)", match_pattern)
            if code in '0123456789':
                code = code + s[0]
                s = s[1:]
            field = d[code.lower()][0]
            field_name = d[code.lower()][1]
            if code.isupper():
                field = ("["
                    "("
                        "part[0], "
                        "'-'.join(''.join(_split_name_prefix(p, True)) for p in part[1].split('-'))"
                    ") if isinstance(part, tuple) "
                    "else part.upper() "
                    f"for part in {field}"
                "]")
            res.append((field_name, p, field, s))
            last_mat_end = mat.end()
            mat = pat.search(format_str, mat.end())
        return res

    def _name_from_parts(self, display_name_parts):
        name_str = ""
        for name_part in display_name_parts:
            if isinstance(name_part, str):
                name_str += name_part
            else:
                part_str = ""
                for sub_part in name_part[2]:
                    if isinstance(sub_part, str):
                        part_str += sub_part
                    else:
                        part_str += sub_part[1]
                if part_str.strip() != "":
                    # This is equivalent to ifNotEmpty in NameDisplay.
                    part_str = name_part[1] + part_str + name_part[3]
                name_str += part_str

        clean_name_str = cleanup_name(name_str)

        return clean_name_str

    def _abbrev_one_given(self, name_parts):
        for i, ii in self._iter_name_parts(name_parts):
            if name_parts[i][2][ii][0] not in ["given", "nick", "given0", "call"]:
                continue
            is_given = name_parts[i][2][ii][0] == "given"
            for abbrev_call in [False, True] if is_given else [None]:
                given_names = name_parts[i][2][ii][1].split()
                if is_given:
                    call = name_parts[i][2][ii][3]
                for j in range(len(given_names)-1, -1, -1): # loop backwards
                    given = given_names[j]
                    if is_given and not abbrev_call and given == call:
                        # abbreviate call after others
                        continue
                    # hyphenated given names: one at a time (e.g. Bengt-Arne, Bengt-A., B.-A.)
                    given_parts = given.split("-")
                    for k in range(len(given_parts)-1, -1, -1): # loop backwards
                        given_part = given_parts[k]
                        if not (given_part[:-1] if given_part[-1] == "." else given_part).isalpha():
                            # ignore everything that's not a name or abbreviated name
                            continue
                        if len(given_part) == 1 or (len(given_part) == 2 and given_part[1] == "."):
                            # can't abbreviate a one-letter name or an abbreviated name
                            continue
                        given_parts[k] = given_part[0] + "."
                        given = "-".join(given_parts)
                        given_names[j] = given
                        if is_given:
                            name_parts[i][2][ii] = (name_parts[i][2][ii][0], " ".join(given_names), name_parts[i][2][ii][2], name_parts[i][2][ii][3])
                        else:
                            name_parts[i][2][ii] = (name_parts[i][2][ii][0], " ".join(given_names))
                        if abbrev_call is not None:
                            call_str = " (call)" if abbrev_call else " (non-call)"
                        else:
                            call_str = ""
                        self.step_description.append(
                            f"abbreviate last non-abbreviated 'given'{call_str}, 'nick', 'given0' or 'call'\n"
                            f"  ({i}, {repr(name_parts[i][0])}, {ii}, {repr(name_parts[i][2][ii][0])}, given {j+1}, part {k+1})"
                        )
                        return True
        return False

    def _abbrev_one_prefix_or_connector(self, name_parts):
        # 'prefix', 'connector' and 'primary-connector' have the same "hierarchy level".
        # 'primary-prefix' is the last to be abbreviated.
        for name_part_types in [["prefix", "connector", "primary-connector"], ["primary-prefix"]]:
            for i, ii in self._iter_name_parts(name_parts):
                if name_parts[i][2][ii][0] not in name_part_types:
                    continue
                prefixes = name_parts[i][2][ii][1].split() # multiple prefixes: e.g. "van den"
                for j in range(len(prefixes)-1, -1, -1): # loop backwards
                    prefix = prefixes[j]
                    if not (prefix[:-1] if prefix[-1] == "." else prefix).isalpha():
                        # ignore everything that's not a name or abbreviated name
                        continue
                    if len(prefix) == 1 or (len(prefix) == 2 and prefix[1] == "."):
                        # can't abbreviate one-letter prefix or an abbreviated prefix
                        continue
                    prefix = prefix[0] + "."
                    prefixes[j] = prefix
                    name_parts[i][2][ii] = (name_parts[i][2][ii][0], " ".join(prefixes))
                    if len(name_part_types) == 1:
                        name_part_types_str = repr(name_part_types[0])
                    else:
                        name_part_types_str = ", ".join(repr(p) for p in name_part_types[:-1]) + " or " + repr(name_part_types[-1])
                    self.step_description.append(
                        f"abbreviate last non-abbreviated {name_part_types_str}\n"
                        f"  ({i}, {repr(name_parts[i][0])}, {ii}, {repr(name_parts[i][2][ii][0])}, prefix {j+1})"
                    )
                    return True
        return False

    def _abbrev_one_surname(self, name_parts):
        for i, ii in self._iter_name_parts(name_parts):
            if name_parts[i][2][ii][0] not in ["surname", "famnick"]: # NOT primary-surname
                continue
            surname = name_parts[i][2][ii][1]
            surname_parts = surname.split("-")
            for j in range(len(surname_parts)-1, -1, -1):
                surname_part = surname_parts[j]
                if surname_part[-1] == ".":
                    surname_part_without_dot = surname_part[:-1]
                else:
                    surname_part_without_dot = surname_part
                prefix, surname_part_without_prefix_and_dot = _split_name_prefix(surname_part_without_dot)
                if not surname_part_without_prefix_and_dot.isalpha():
                    # ignore everything that's not a name or an abbreviated name
                    continue
                if len(surname_part) == 1 or (surname_part[-1] == "." and (len(surname_part) == 2 or surname_part[:-2] == prefix)):
                    # one-letter name or abbreviated name (one letter or prefix with one letter of abbreviated main part)
                    continue
                abbrev_surname_part = prefix + surname_part_without_prefix_and_dot[0] + "."
                surname_parts[j] = abbrev_surname_part
                abbrev_surname = "-".join(surname_parts)
                name_parts[i][2][ii] = (name_parts[i][2][ii][0], abbrev_surname)
                self.step_description.append(
                    f"abbreviate last non-abbreviated 'surname' (non-primary) or 'famnick'\n"
                    f"  ({i}, {repr(name_parts[i][0])}, {ii}, {repr(name_parts[i][2][ii][0])}, part {j+1})"
                )
                return True
        return False

    def _remove_one_given(self, name_parts):
        for i, ii in self._iter_name_parts(name_parts):
            if name_parts[i][2][ii][0] == "given":
                given_names = name_parts[i][2][ii][1].split()
                given_names_full = name_parts[i][2][ii][2].split()
                call_or_first_given = name_parts[i][2][ii][3] or given_names_full[0]
                for j in range(len(given_names)-1, -1, -1): # loop backwards
                    given_orig = given_names_full[j]
                    if given_orig == call_or_first_given:
                        # don't remove abbreviated call or first given
                        continue
                    given_names[j] = ""
                    given_names_full[j] = ""
                    name_parts[i][2][ii] = (name_parts[i][2][ii][0], " ".join(given_names).strip(), " ".join(given_names_full).strip(), name_parts[i][2][ii][3])
                    self.step_description.append(
                        f"remove last 'given' (non-call or non-first)\n"
                        f"  ({i}, {repr(name_parts[i][0])}, {ii}, {repr(name_parts[i][2][ii][0])}, given {j+1})"
                    )
                    return True
        return False

    def _iter_name_parts(self, name_parts):
        """Loop backwards ofer non-str items of name_parts.
        Yields i, ii for all useful name_parts[i][2][ii]
        """
        for i in range(len(name_parts)-1, -1, -1):
            if isinstance(name_parts[i], str):
                continue
            for ii in range(len(name_parts[i][2])-1, -1, -1):
                if isinstance(name_parts[i][2][ii], str):
                    continue
                yield i, ii

def _split_name_prefix(name, upper_main=False):
    if len(name) == 0:
        return ("", "")
    if (name.isupper() and name.isalpha()) or name.islower():
        # All upper and all lower should cannot be separated.
        # isupper() is also true for O'BRIEN which can be separated
        return ("", name.upper() if upper_main else name)
    upper_indices = [idx for idx in range(len(name)) if name[idx].isupper()]
    if upper_indices[0] == 0:
        if len(upper_indices) == 1:
            # no prefix
            return ("", name.upper() if upper_main else name)
        idx = upper_indices[1]
    else:
        if len(upper_indices) == 0:
            # this should not be reachable
            return ("", name.upper() if upper_main else name)
        idx = upper_indices[0]
    prefix = name[:idx]
    name = name[idx:]
    return (prefix, name.upper() if upper_main else name)
