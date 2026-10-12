"""Run a command detached from the caller's session, and record its pid.

usage: detach.py PIDFILE CMD [ARG...]

app.sh start uses this so the server outlives the shell call (or agent tool call) that
started it: some agent shells tear down the call's process group or session when the
call ends, and macOS has no setsid(1).

Double fork. The first child calls setsid() (a new session and process group, no
controlling terminal), forks the grandchild, writes the grandchild's pid to PIDFILE
(atomically) and exits. The grandchild ignores SIGHUP and execs CMD, so that pid is the
command's pid. This process waits for the first child, so PIDFILE exists when it exits 0.
"""

import os
import signal
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: detach.py PIDFILE CMD [ARG...]", file=sys.stderr)
        return 2
    pidfile, argv = sys.argv[1], sys.argv[2:]
    child = os.fork()
    if child:
        _, status = os.waitpid(child, 0)
        return os.waitstatus_to_exitcode(status)
    try:
        os.setsid()
        grandchild = os.fork()
        if grandchild:
            try:
                tmp = pidfile + ".tmp"
                with open(tmp, "w") as f:
                    f.write(f"{grandchild}\n")
                os.replace(tmp, pidfile)
            except BaseException as exc:
                # Never leave an unrecorded process behind.
                os.kill(grandchild, signal.SIGKILL)
                print(f"detach.py: cannot record pid {grandchild}: {exc}", file=sys.stderr)
                os._exit(1)
            os._exit(0)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        os.execvp(argv[0], argv)
    except BaseException as exc:
        print(f"detach.py: {exc}", file=sys.stderr)
        os._exit(127)
    return 0  # not reached


if __name__ == "__main__":
    sys.exit(main())
