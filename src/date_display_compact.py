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
            "<", # before
            ">", # after
            "~", # about
            "",
            "",
            "",
            " +",
            " −", # minus
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
                "{date_quality} {date_start} – {date_stop}"
                "{nonstd_calendar_and_ny}"
            )

        if msgid == (
            "{date_quality}from {date_start} to {date_stop}"
            "{nonstd_calendar_and_ny}"
        ): # span
            return (
                "{date_quality} {date_start} \u2026 {date_stop}"
                "{nonstd_calendar_and_ny}"
            ) # en dash

        return self.orig_gettext(msgid, context=context)

    display = DateDisplay.display_formatted

displayer = DateDisplayCompact()

def get_date(date_base):
    date_str = displayer.display(date_base.get_date_object())
    date_str = date_str.replace(" +", "+").replace(" −", "−")
    return date_str
