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

        abbrev_rules = [
            ("abbrev", ["given[ncnf]", "nick", "given0", "call"], True),
            ("abbrev", ["given"], True),
            ("abbrev", ["prefix", "connector", "primary-connector"], True),
            ("abbrev", ["primary-prefix"], True),
            ("abbrev", ["surname", "famnick"], True),
            ("remove", ["given[ncnf]"], True),
            ("remove", ["prefix", "connector"], True),
            ("remove", ["title", "suffix"], True),
            ("remove", ["primary-prefix", "primary-connector"], True),
            ("remove", ["surname", "famnick"], True),
            ("abbrev", ["primary-surname"], True),
            ("remove", ["given", "nick", "given0", "call"], True),
        ]
        for action, name_part_types, reverse in abbrev_rules:
            while True:
                if not self._apply_rule_once(name_parts, action, name_part_types, reverse):
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
            if code in "0123456789":
                code = code + s[0]
                s = s[1:]
            field = d[code.lower()][0]
            field_name = d[code.lower()][1]
            if code.isupper():
                field = ("["
                    "("
                        "part[0].upper(), "
                        "*part[1:]"
                    ") if isinstance(part, tuple) "
                    "else part.upper() " # This should only be a space or an empty string.
                    # There should only be strings (e.g. spaces) and list of tuples
                    # (list of tuples: 'surname', tuple which needs to be converted: 'given').
                    # A lambda is used so field doesn't have to be evaluated multiple times (e.g. if it's a function).
                    f"for part in (lambda x: [x] if isinstance(x, tuple) else x)({field})"
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
                        if sub_part[0].isupper():
                            prefix_possible = sub_part[0].lower() in ["surname", "primary-surname", "famnick"]
                            part_str += " ".join(
                                "-".join(
                                    "".join(_upper(
                                        _split_name_at_capital_letter(
                                            hysep_part,
                                            expect_prefix=prefix_possible
                                        ),
                                        all_but_first=prefix_possible
                                    ))
                                    for hysep_part in spsep_part.split("-")
                                )
                                for spsep_part in sub_part[1].split()
                            )
                        else:
                            part_str += sub_part[1]
                if part_str.strip() != "":
                    # This is equivalent to ifNotEmpty in NameDisplay.
                    part_str = name_part[1] + part_str + name_part[3]
                name_str += part_str

        clean_name_str = cleanup_name(name_str)

        return clean_name_str

    def _apply_rule_once(self, name_parts, action, name_part_types, reverse):
        if reverse:
            reversed_ = reversed
        else:
            reversed_ = lambda x: x

        for i, ii in self._iter_name_parts(name_parts, reverse):
            name_part_type = name_parts[i][2][ii][0].lower()
            if name_part_type not in name_part_types:
                if name_part_type == "given" and "given[ncnf]" in name_part_types:
                    name_part_type_opts = "ncnf"
                    call = name_parts[i][2][ii][3]
                else:
                    continue
            else:
                name_part_type_opts = ""
            is_given = name_part_type == "given" # special handling for 'given'
            spsep_parts = name_parts[i][2][ii][1].split()
            for j in reversed_(range(len(spsep_parts))):
                spsep_part = spsep_parts[j]
                if is_given:
                    # Check full (non-abbreviated) to check for actual call name.
                    spsep_parts_given_full = name_parts[i][2][ii][2].split()
                    if name_part_type_opts == "ncnf" and spsep_parts_given_full[j] == call:
                        # NOTE: Don't check for first since first can be hyphenated or a compound name without a separator.
                        # Skip call name.
                        continue
                hysep_parts = spsep_part.split("-")
                for k in reversed_(range(len(hysep_parts))):
                    hysep_part = hysep_parts[k]
                    if is_given:
                        # Check full (non-abbreviated) to check for actual call name.
                        hysep_parts_given_full = spsep_parts_given_full[j].split("-")
                        if name_part_type_opts == "ncnf" and hysep_parts_given_full[k] == call:
                            # NOTE: Don't check for first since first can be a compound name without a separator.
                            # Skip call name.
                            continue
                    if name_part_type in ["surname", "primary-surname", "famnick"]:
                        prefix, *upsep_parts_without_prefix = _split_name_at_capital_letter(hysep_part)
                    else:
                        # Only surnames have prefixes that need to be handled specially.
                        upsep_parts_without_prefix = _split_name_at_capital_letter(hysep_part, expect_prefix=False)
                        prefix = ""
                    for l in reversed_(range(len(upsep_parts_without_prefix))):
                        upsep_part_without_prefix = upsep_parts_without_prefix[l]
                        if is_given:
                            # Check full (non-abbreviated) to check for actual call name.
                            # Only surnames have prefixes that need to be handled specially.
                            upsep_parts_given_full = _split_name_at_capital_letter(hysep_parts_given_full[k], expect_prefix=False)
                            if name_part_type_opts == "ncnf" and (
                                upsep_parts_given_full[l] == call # call name
                                or (call == "" and j == 0 and k == 0 and l == 0) # no call and this is first
                            ):
                                # Skip call name and first name.
                                continue
                        if action == "abbrev":
                            if not upsep_part_without_prefix.isalpha():
                                # Ignore everything that's not a name or abbreviated name.
                                # TODO What about names with question marks etc.
                                continue
                            if (len(upsep_part_without_prefix) == 1):
                                # Can't abbreviate a one-letter name part or an abbreviated name.
                                continue
                            # Actual abbreviation:
                            upsep_parts_without_prefix[l] = upsep_part_without_prefix[0] + "."
                            hysep_parts[k] =  prefix + "".join(upsep_parts_without_prefix)
                            spsep_parts[j] = "-".join(hysep_parts)
                            if is_given:
                                name_parts[i][2][ii] = (name_parts[i][2][ii][0], " ".join(spsep_parts), name_parts[i][2][ii][2], name_parts[i][2][ii][3])
                            else:
                                name_parts[i][2][ii] = (name_parts[i][2][ii][0], " ".join(spsep_parts))
                        elif action == "remove":
                            upsep_parts_without_prefix.pop(l)
                            hysep_parts[k] = "".join(upsep_parts_without_prefix)
                            if len(hysep_parts[k]) == 0:
                                hysep_parts.pop(k)
                            spsep_parts[j] = "-".join(hysep_parts)
                            if len(spsep_parts[j]) == 0:
                                spsep_parts.pop(j)
                            if is_given:
                                upsep_parts_given_full.pop(l)
                                hysep_parts_given_full[k] = "".join(upsep_parts_given_full)
                                if len(hysep_parts_given_full[k]) == 0:
                                    hysep_parts_given_full.pop(k)
                                spsep_parts_given_full[j] = "-".join(hysep_parts_given_full)
                                if len(spsep_parts_given_full[j]) == 0:
                                    spsep_parts_given_full.pop(j)
                                name_parts[i][2][ii] = (name_parts[i][2][ii][0], " ".join(spsep_parts).strip(), " ".join(spsep_parts_given_full).strip(), name_parts[i][2][ii][3])
                            else:
                                name_parts[i][2][ii] = (name_parts[i][2][ii][0], " ".join(spsep_parts))

                        if action == "abbrev":
                            action_str = "abbreviate"
                            extra_str = "non-abbreviated "
                        elif action == "remove":
                            action_str = "remove"
                            extra_str = ""
                        if reverse:
                            last_or_first = "last"
                        else:
                            last_or_first = "first"
                        if len(name_part_types) == 1:
                            name_part_types_str = (
                                repr("given") + " (non-call or non-first)"
                                if name_part_types[0] == "given[ncnf]"
                                else repr(name_part_types[0])
                            )
                        else:
                            name_part_types_str = (
                                ", ".join(
                                    repr("given") + " (non-call or non-first)"
                                    if p == "given[ncnf]"
                                    else repr(p)
                                    for p in name_part_types[:-1]
                                )
                                + " or " + repr(name_part_types[-1]))
                        self.step_description.append(
                            f"{action_str} {last_or_first} {extra_str}{name_part_types_str}\n"
                            f"  ({i}, {repr(name_parts[i][0])}, {ii}, {repr(name_parts[i][2][ii][0])}, space-separated part {j+1}, hyphen-separated part {k+1}, uppercase-separated part {l+1})"
                        )
                        return True
        return False

    def _iter_name_parts(self, name_parts, reverse=True):
        """Loop backwards ofer non-str items of name_parts.
        Yields i, ii for all useful name_parts[i][2][ii]
        """
        if reverse:
            reversed_ = reversed
        else:
            reversed_ = lambda x: x
        for i in reversed_(range(len(name_parts))):
            if isinstance(name_parts[i], str):
                continue
            for ii in reversed_(range(len(name_parts[i][2]))):
                if isinstance(name_parts[i][2][ii], str):
                    continue
                yield i, ii

def _split_name_at_capital_letter(name, expect_prefix=True):
    """splits names at capital letter
    "Abc" -> ("", "Abc") if handle_prefix else ("Abc",)
    "AbcDef" -> ("Abc", "Def")
    "O'Def" -> ("O'", "Def")
    "AbcDefGhi" -> ("Abc", "Def", "Ghi")
    """
    if len(name) == 0:
        return ["", ""] if expect_prefix else [""]
    if name.isupper() or name.islower() or all(not ch.isalpha() for ch in name):
        # All upper, all lower and all special characters cannot be separated.
        return ["", name] if expect_prefix else [name]
    upper_indices = [idx for idx in range(len(name)) if name[idx].isupper()]
    if len(upper_indices) == 0:
        return ["", name] if expect_prefix else [name]
    if upper_indices[0] == 0:
        if len(upper_indices) == 1:
            # no prefix
            return ["", name] if expect_prefix else [name]
        idx = upper_indices[1]
    else:
        if len(upper_indices) == 0:
            # this should not be reachable
            return ["", name] if expect_prefix else [name]
        idx = upper_indices[0]
    prefix = name[:idx]
    names = _split_name_at_capital_letter(name[idx:], expect_prefix=False)
    if not expect_prefix and prefix == "":
        return names
    return [prefix, *names]

def _upper(names, all_but_first=True):
    if all_but_first:
        return [names[0], *(name.upper() for name in names[1:])]
    else:
        return [name.upper() for name in names]
