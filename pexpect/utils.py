import os
import sys
import stat
import select
import time
import errno
try:
    InterruptedError
except NameError:
    InterruptedError = select.error
if sys.version_info[0] >= 3:
    string_types = str,
else:
    string_types = unicode, str


def is_executable_file(path):
    """Checks that path is an executable regular file, or a symlink towards one.

    This is roughly ``os.path isfile(path) and os.access(path, os.X_OK)``.
    """
    pass


def which(filename, env=None):
    """This takes a given filename; tries to find it in the environment path;
    then checks if it is executable. This returns the full path to the filename
    if found and executable. Otherwise this returns None."""
    pass


def split_command_line(command_line):
    """This splits a command line into a list of arguments. It splits arguments
    on spaces, but handles embedded quotes, doublequotes, and escaped
    characters. It's impossible to do this with a regular expression, so I
    wrote a little state machine to parse the command line. """
    pass


def select_ignore_interrupts(iwtd, owtd, ewtd, timeout=None):
    """This is a wrapper around select.select() that ignores signals. If
    select.select raises a select.error exception and errno is an EINTR
    error then it is ignored. Mainly this is used to ignore sigwinch
    (terminal resize). """
    pass


def poll_ignore_interrupts(fds, timeout=None):
    """Simple wrapper around poll to register file descriptors and
    ignore signals."""
    pass
