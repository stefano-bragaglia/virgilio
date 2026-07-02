from virgilio.events import EventType


def test_has_exactly_five_members():
    assert len(EventType) == 5


def test_has_expected_member_names():
    assert {member.name for member in EventType} == {
        "CREATED",
        "MODIFIED",
        "DELETED",
        "FOUND",
        "ERROR",
    }


def test_members_have_distinct_values():
    values = [member.value for member in EventType]
    assert len(values) == len(set(values))
