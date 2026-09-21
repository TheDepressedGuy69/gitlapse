import pytest

from gitlapse.gitlog import GitLogError, parse_commits, unquote_path


@pytest.mark.parametrize("raw,expected", [
    ('"caf\\303\\251.txt"', "café.txt"), ('"quo\\"te.txt"', 'quo"te.txt'), ('"tab\\tname.txt"', "tab\tname.txt"),
    ('"back\\\\slash"', "back\\slash"), ("plain.txt", "plain.txt"), ('"', '"'), ('""', ""),
])
def test_unquote_path(raw, expected):
    assert unquote_path(raw) == expected


def test_odd_filenames_come_through_readable(nasty_repo):
    paths = {ch.path for c in parse_commits(nasty_repo) for ch in c.changes}
    assert {"café.txt", "日本語.md", 'quo"te.txt', "tab\tname.txt", "d e/ünï.py", "with space.py"} <= paths
    assert not any(p.startswith('"') for p in paths)


def test_empty_merge_and_binary_commits_do_not_break_parsing(nasty_repo):
    commits = parse_commits(nasty_repo)
    by_subject = {c.subject: c for c in commits}
    assert by_subject["empty commit"].changes == []
    assert by_subject["merge feat"].changes == []
    assert by_subject["binary"].changes[0].insertions == 0  # "-" for binary files


def test_deletion_and_readd_are_reported(nasty_repo):
    by_subject = {c.subject: c for c in parse_commits(nasty_repo)}
    assert [(ch.status, ch.path) for ch in by_subject["delete"].changes] == [("D", "with space.py")]
    assert [(ch.status, ch.path) for ch in by_subject["re-add"].changes] == [("A", "with space.py")]


def test_clear_errors(tmp_path, nasty_repo):
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(GitLogError, match="not a git repository"):
        parse_commits(str(plain))
    with pytest.raises(GitLogError, match="not a directory"):
        parse_commits(str(tmp_path / "missing"))
    with pytest.raises(GitLogError, match="no such branch or ref 'nope'"):
        parse_commits(nasty_repo, "nope")
