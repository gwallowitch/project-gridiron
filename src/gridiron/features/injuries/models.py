"""Constants for injury availability features."""

BASE_RAW_INJURY_COLUMNS = frozenset(
    {
        "season",
        "game_type",
        "team",
        "week",
        "gsis_id",
        "position",
        "full_name",
        "first_name",
        "last_name",
        "report_primary_injury",
        "report_secondary_injury",
        "report_status",
        "practice_primary_injury",
        "practice_secondary_injury",
        "practice_status",
    }
)

REPORT_SEVERITY = {
    "Out": 1.00,
    "Doubtful": 0.75,
    "Questionable": 0.40,
    "Note": 0.00,
}

PRACTICE_SEVERITY = {
    "Did Not Participate In Practice": 0.50,
    "Limited Participation in Practice": 0.25,
    "Full Participation in Practice": 0.00,
    "Note": 0.00,
}
