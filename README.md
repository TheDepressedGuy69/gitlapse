# gitlapse

Watch any git repository's history replay live, right in your terminal — every file
appearing, growing, and disappearing over time, color-coded by author.

Think [Gource](https://gource.io/), but **zero dependencies, one `pip install`, and it
runs over SSH** — no GUI, no SDL, no X11. Just Python's standard library and `git`.

![demo](docs/demo.gif)

## Install

```bash
pip install gitlapse
```

(Requires Python 3.9+ and `git` on your `PATH`. No other dependencies —
`gitlapse` is built entirely on the standard library's `curses` module.)

## Usage

```bash
# replay the repo in the current directory
gitlapse

# replay a specific repo
gitlapse ~/code/some-project

# replay a specific branch
gitlapse ~/code/some-project --branch main

# stretch/compress the full playback to N seconds (default: 45)
gitlapse --duration 90

# start already sped up
gitlapse --speed 3
```

### Controls

| Key       | Action                        |
|-----------|--------------------------------|
| `space`   | play / pause                  |
| `+` / `-` | speed up / slow down           |
| `→`       | step forward one commit (pauses) |
| `←`       | step back one commit (pauses)  |
| `r`       | restart from the beginning     |
| `q`       | quit                            |

## How it works

`gitlapse` runs `git log --raw --numstat` once, parses the full history into an
in-memory list of commits (added/modified/deleted files with line counts), then
replays that list against a virtual file tree, one commit at a time, drawn with
Python's built-in `curses` module. Each author gets a deterministic color; files
flash when touched and fade out (in red) when deleted; the tree auto-scrolls to
keep the action in view.

No network calls, no telemetry, no third-party packages — it works entirely
offline and works fine piped over SSH to a plain terminal.

## Capturing a demo GIF

The GIF above was captured with [asciinema](https://asciinema.org/) +
[agg](https://github.com/asciinema/agg):

```bash
asciinema rec demo.cast -c "gitlapse ~/code/some-active-project --duration 18 --auto-quit-after 2"
agg demo.cast docs/demo.gif
```

`--auto-quit-after SECONDS` exits automatically once playback finishes, which
is handy for scripted recordings (no need to press `q` yourself).

## Roadmap ideas

- `--since` / `--until` date filtering
- collapse directories that haven't been touched recently, for huge monorepos
- export mode (render frames straight to a GIF/MP4 without a terminal recorder)
- highlight the single largest file changed per commit

Contributions and issues welcome.

## License

MIT — see [LICENSE](LICENSE).
