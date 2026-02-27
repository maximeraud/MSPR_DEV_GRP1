from ntl_systoolbox.cli.module2_backup import _mysql_client_path

def test_mysql_client_path_returns_valid_type():
    result = _mysql_client_path()
    assert result is None or isinstance(result, str)