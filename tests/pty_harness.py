import fcntl, os, select, signal, struct, subprocess, sys, termios, time

def run(args, rows=30, cols=120, script=(), env=None, total=8.0, term="xterm-256color"):
    """script: list of (delay_seconds, action) where action is bytes to send, or ('resize', rows, cols)."""
    m, s = os.openpty()
    fcntl.ioctl(s, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    e = dict(os.environ, TERM=term, **(env or {}))
    if term is None: e.pop("TERM", None)
    p = subprocess.Popen([sys.executable, "-m", "gitlapse", *args], stdin=s, stdout=s, stderr=s, env=e,
                         start_new_session=True, close_fds=True)
    os.close(s)
    out = b""; t0 = time.time(); pending = sorted(script, key=lambda x: x[0]); timed_out = False
    while True:
        now = time.time() - t0
        while pending and pending[0][0] <= now:
            _, act = pending.pop(0)
            if isinstance(act, tuple) and act[0] == "resize":
                fcntl.ioctl(m, termios.TIOCSWINSZ, struct.pack("HHHH", act[1], act[2], 0, 0))
                os.killpg(p.pid, signal.SIGWINCH)
            elif act == "SIGINT":
                os.killpg(p.pid, signal.SIGINT)
            else:
                os.write(m, act)
        r, _, _ = select.select([m], [], [], 0.05)
        if r:
            try:
                chunk = os.read(m, 65536)
                if chunk: out += chunk
            except OSError: pass
        if p.poll() is not None:
            try:
                while select.select([m], [], [], 0.05)[0]:
                    c = os.read(m, 65536)
                    if not c: break
                    out += c
            except OSError: pass
            break
        if now > total:
            timed_out = True; os.killpg(p.pid, signal.SIGKILL); p.wait(); break
    os.close(m)
    return p.returncode, timed_out, out.decode("utf-8", "replace")

def verdict(name, rc, timed_out, out, expect_rc=0, must_have=None):
    bad = []
    if timed_out: bad.append("TIMEOUT (never exited)")
    elif rc != expect_rc: bad.append(f"exit={rc} expected {expect_rc}")
    if "Traceback" in out or "_curses.error" in out: bad.append("PYTHON ERROR: " + out.strip().splitlines()[-1][:80])
    if must_have and must_have not in out: bad.append(f"missing {must_have!r}")
    print(("FAIL " if bad else "PASS ") + name + (("  -> " + "; ".join(bad)) if bad else ""))
    return not bad
