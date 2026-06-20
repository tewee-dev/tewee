from tewee.version import __version__, __version_tuple__


def test_version_is_str() -> None:
    assert isinstance(__version__, str)

def test_version_tuple_is_tuple() -> None:
    assert isinstance(__version_tuple__, tuple)

def test_version_tuple_type() -> None:
    assert isinstance(__version_tuple__[0], int)
    assert isinstance(__version_tuple__[1], int)
    assert isinstance(__version_tuple__[2], int)
# Collecting more tests...