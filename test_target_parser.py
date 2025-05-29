import pytest
from target_parser import parse_targets

def test_valid_single_target():
    """Test parsing a single valid target"""
    result = parse_targets("peterxcli@apache/ozone")
    assert result == [("peterxcli", "apache", "ozone")]

def test_valid_multiple_targets_space():
    """Test parsing multiple valid targets separated by spaces"""
    result = parse_targets("peterxcli@apache/ozone peterxcli@apache/hadoop")
    assert result == [
        ("peterxcli", "apache", "ozone"),
        ("peterxcli", "apache", "hadoop")
    ]

def test_valid_multiple_targets_comma():
    """Test parsing multiple valid targets separated by commas"""
    result = parse_targets("peterxcli@apache/ozone,peterxcli@apache/hadoop")
    assert result == [
        ("peterxcli", "apache", "ozone"),
        ("peterxcli", "apache", "hadoop")
    ]

def test_valid_multiple_targets_mixed():
    """Test parsing multiple valid targets with mixed separators"""
    result = parse_targets("peterxcli@apache/ozone, peterxcli@apache/hadoop")
    assert result == [
        ("peterxcli", "apache", "ozone"),
        ("peterxcli", "apache", "hadoop")
    ]

def test_empty_input():
    """Test parsing empty input"""
    with pytest.raises(ValueError, match="Empty targets string"):
        parse_targets("")

def test_whitespace_only():
    """Test parsing input with only whitespace"""
    with pytest.raises(ValueError, match="Empty targets string"):
        parse_targets("   ")

def test_missing_at_symbol():
    """Test parsing target without @ symbol"""
    with pytest.raises(ValueError, match="Invalid repository format"):
        parse_targets("peterxcli/apache/ozone")

def test_missing_slash():
    """Test parsing target without / in repository"""
    with pytest.raises(ValueError, match="Invalid repository format"):
        parse_targets("peterxcli@apacheozone")

def test_empty_username():
    """Test parsing target with empty username"""
    with pytest.raises(ValueError, match="Invalid target format"):
        parse_targets("@apache/ozone")

def test_empty_repo_owner():
    """Test parsing target with empty repo owner"""
    with pytest.raises(ValueError, match="Invalid repository format"):
        parse_targets("peterxcli@/ozone")

def test_empty_repo_name():
    """Test parsing target with empty repo name"""
    with pytest.raises(ValueError, match="Invalid repository format"):
        parse_targets("peterxcli@apache/")

def test_multiple_at_symbols():
    """Test parsing target with multiple @ symbols"""
    with pytest.raises(ValueError, match="Invalid repository format"):
        parse_targets("peterxcli@apache@ozone")

def test_multiple_slashes():
    """Test parsing target with multiple slashes"""
    with pytest.raises(ValueError, match="Invalid repository format"):
        parse_targets("peterxcli@apache/ozone/extra")

def test_special_characters():
    """Test parsing target with special characters"""
    result = parse_targets("user.name@org-name/repo_name")
    assert result == [("user.name", "org-name", "repo_name")]

def test_case_sensitivity():
    """Test parsing target with different cases"""
    result = parse_targets("User@Org/Repo")
    assert result == [("User", "Org", "Repo")] 