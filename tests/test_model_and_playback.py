from gitlapse.gitlog import parse_commits
from gitlapse.app import Playback
from gitlapse.model import FileTree


def _paths(tree):
    return {n.full_path() for _, n in tree.flatten() if not n.is_dir}


def test_file_re_added_during_its_death_animation_survives():
    t = FileTree()
    t.touch("a/x.py", "Al", 10)
    t.remove("a/x.py")
    t.touch("a/x.py", "Al", 5)
    for _ in range(8):
        t.tick()
    assert "a/x.py" in _paths(t)


def test_deleted_file_disappears_and_empty_dirs_are_pruned():
    t = FileTree()
    t.touch("a/b/x.py", "Al", 3)
    t.remove("a/b/x.py")
    for _ in range(8):
        t.tick()
    assert _paths(t) == set() and t.flatten() == []


def test_replay_matches_the_real_final_tree(nasty_repo):
    pb = Playback(parse_commits(nasty_repo), 5.0)
    pb.advance(len(pb.commits))
    for _ in range(8):
        pb.tree.tick()
    assert _paths(pb.tree) == {"café.txt", "日本語.md", 'quo"te.txt', "tab\tname.txt", "d e/ünï.py",
                               "with space.py", "blob.bin", "feat.txt", "main.txt"}
    assert pb.finished and not pb.playing


def test_seek_backwards_and_forwards_is_consistent(nasty_repo):
    pb = Playback(parse_commits(nasty_repo), 5.0)
    pb.advance(len(pb.commits))
    n_full = pb.tree.file_count()
    pb.seek(0)
    assert pb.tree.file_count() == 0 and pb.idx == 0 and not pb.finished
    pb.seek(len(pb.commits))
    assert pb.tree.file_count() == n_full


def _simulated_seconds(n_commits, duration, frame=0.035):
    from gitlapse.gitlog import Commit
    pb = Playback([Commit(str(i), "Al", i, "s", []) for i in range(n_commits)], target_duration=duration)
    clock = 0.0
    while not pb.finished and clock < 1000:
        pb.play(frame)
        clock += frame
    return clock


def test_duration_is_honoured_whatever_the_history_length_or_frame_rate():
    for n in (100, 480, 20000):
        for frame in (0.02, 0.035, 0.08):
            assert abs(_simulated_seconds(n, 45.0, frame) - 45.0) < 1.5, (n, frame)


def test_speed_and_pause_scale_playback_time():
    from gitlapse.gitlog import Commit
    pb = Playback([Commit(str(i), "Al", i, "s", []) for i in range(1000)], target_duration=20.0)
    pb.speed = 2.0
    for _ in range(300):
        pb.play(0.035)
    assert 500 * 0.9 < pb.idx < 500 * 1.1 or pb.finished  # ~10.5s at 2x of a 20s history
    pb.playing = False
    at = pb.idx
    pb.play(5.0)
    assert pb.idx == at
