from app.report import status_line


def test_status_line_ok():
    assert status_line(True).endswith(": ok")
