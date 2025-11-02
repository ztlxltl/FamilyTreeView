from gramps.gen.datehandler._datedisplay import DateDisplay

class DateDisplayCompact(DateDisplay):
    def __init__(self):
        super().__init__()

        # TODO Maybe decide which calendar to hide based on Gramps'
        # settings. Seems like in DateDisplay, gregorian is always set
        # to "".
        self.calendar = (
            "", # "g.", # Gregorian # no output
            "j.", # Julian
            "h.", # Hebrew
            "f.", # French Republican
            "p.", # Persian
            "i.", # Islamic
            "s.", # Swedish
        )

        self._mod_str = (
            "",
            "\u2264", # before # less-than or equal to
            "\u2265", # after # great-than or equal to
            "~", # about
            "",
            "",
            "",
            " +",
            " \u2212", # minus
        )

        self._qual_str = (
            "",
            "~", # estimated
            "~", # calculated
        )

        self.orig_gettext = self._
        self._ = self.gettext_wrapper

    def gettext_wrapper(self, msgid, context=""):
        # Hacky workaround to change format strings without
        # reimplementing whole functions.

        if msgid == (
            "{date_quality}between {date_start} and {date_stop}"
            "{nonstd_calendar_and_ny}"
        ): # range
            return (
                "{date_quality} {date_start} \u2013 {date_stop}" # en dash
                "{nonstd_calendar_and_ny}"
            )

        if msgid == (
            "{date_quality}from {date_start} to {date_stop}"
            "{nonstd_calendar_and_ny}"
        ): # span
            return (
                "{date_quality} {date_start} \u2026 {date_stop}" # ellipsis
                "{nonstd_calendar_and_ny}"
            )

        return self.orig_gettext(msgid, context=context)

    display = DateDisplay.display_formatted

displayer = DateDisplayCompact()

def get_date(date_base, only_year):
    date = date_base.get_date_object()
    if only_year:
        # Remove day and month, keep modifier, quality, calender etc.
        if date.is_compound():
            date.set_yr_mon_day(date.get_year(), 0, 0, False)
            date.set2_yr_mon_day(date.get_stop_year(), 0, 0)
        else:
            date.set_yr_mon_day(date.get_year(), 0, 0)
    date_str = displayer.display(date)
    date_str = date_str.replace(" +", "+").replace(" \u2212", "\u2212") # minus
    return date_str
