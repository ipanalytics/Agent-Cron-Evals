from __future__ import annotations

from agent_cron_evals.schedule import hours_in_window, weekday_allowed


def test_star_means_every_hour():
    assert hours_in_window("0 * * * *", 3) is True


def test_a_range_is_a_window():
    assert hours_in_window("*/5 6-22 * * *", 6) is True
    assert hours_in_window("*/5 6-22 * * *", 22) is True
    assert hours_in_window("*/5 6-22 * * *", 23) is False


def test_a_list_is_a_set_of_hours():
    assert hours_in_window("0 3,9,15 * * *", 9) is True
    assert hours_in_window("0 3,9,15 * * *", 10) is False


def test_a_plain_hour_matches_only_itself():
    assert hours_in_window("30 7 * * *", 7) is True
    assert hours_in_window("30 7 * * *", 8) is False


def test_a_step_counts_every_nth_hour():
    assert hours_in_window("0 */6 * * *", 12) is True
    assert hours_in_window("0 */6 * * *", 13) is False


def test_an_unreadable_expression_counts_as_in_window():
    # a false alarm trains the human to ignore the alarm, so junk must fail open
    assert hours_in_window("nonsense", 3) is True
    assert hours_in_window("0 abc-def * * *", 3) is True
    assert hours_in_window("", 3) is True


def test_weekdays_by_number():
    assert weekday_allowed([0, 1, 2, 3, 4], 2) is True
    assert weekday_allowed([0, 1, 2, 3, 4], 5) is False
    assert weekday_allowed([7], 6) is True  # 7 is Sunday spelled as a number


def test_weekdays_by_name():
    assert weekday_allowed(["mon", "tue", "wed", "thu", "fri"], 0) is True
    assert weekday_allowed(["mon", "tue", "wed", "thu", "fri"], 6) is False


def test_no_days_means_every_day():
    assert weekday_allowed([], 6) is True
    assert weekday_allowed(None, 3) is True


def test_unknown_day_names_do_not_narrow_the_window():
    assert weekday_allowed(["nonsense"], 3) is True
