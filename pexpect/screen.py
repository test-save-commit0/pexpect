"""This implements a virtual screen. This is used to support ANSI terminal
emulation. The screen representation and state is implemented in this class.
Most of the methods are inspired by ANSI screen control codes. The
:class:`~pexpect.ANSI.ANSI` class extends this class to add parsing of ANSI
escape codes.

PEXPECT LICENSE

    This license is approved by the OSI and FSF as GPL-compatible.
        http://opensource.org/licenses/isc-license.txt

    Copyright (c) 2012, Noah Spurrier <noah@noah.org>
    PERMISSION TO USE, COPY, MODIFY, AND/OR DISTRIBUTE THIS SOFTWARE FOR ANY
    PURPOSE WITH OR WITHOUT FEE IS HEREBY GRANTED, PROVIDED THAT THE ABOVE
    COPYRIGHT NOTICE AND THIS PERMISSION NOTICE APPEAR IN ALL COPIES.
    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
    OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
import codecs
import copy
import sys
import warnings
warnings.warn(
    'pexpect.screen and pexpect.ANSI are deprecated. We recommend using pyte to emulate a terminal screen: https://pypi.python.org/pypi/pyte'
    , stacklevel=2)
NUL = 0
ENQ = 5
BEL = 7
BS = 8
HT = 9
LF = 10
VT = 11
FF = 12
CR = 13
SO = 14
SI = 15
XON = 17
XOFF = 19
CAN = 24
SUB = 26
ESC = 27
DEL = 127
SPACE = u' '
PY3 = sys.version_info[0] >= 3
if PY3:
    unicode = str


def constrain(n, min, max):
    """This returns a number, n constrained to the min and max bounds. """
    pass


class screen:
    """This object maintains the state of a virtual text screen as a
    rectangular array. This maintains a virtual cursor position and handles
    scrolling as characters are added. This supports most of the methods needed
    by an ANSI text screen. Row and column indexes are 1-based (not zero-based,
    like arrays).

    Characters are represented internally using unicode. Methods that accept
    input characters, when passed 'bytes' (which in Python 2 is equivalent to
    'str'), convert them from the encoding specified in the 'encoding'
    parameter to the constructor. Methods that return screen contents return
    unicode strings, with the exception of __str__() under Python 2. Passing
    ``encoding=None`` limits the API to only accept unicode input, so passing
    bytes in will raise :exc:`TypeError`.
    """

    def __init__(self, r=24, c=80, encoding='latin-1', encoding_errors=
        'replace'):
        """This initializes a blank screen of the given dimensions."""
        self.rows = r
        self.cols = c
        self.encoding = encoding
        self.encoding_errors = encoding_errors
        if encoding is not None:
            self.decoder = codecs.getincrementaldecoder(encoding)(
                encoding_errors)
        else:
            self.decoder = None
        self.cur_r = 1
        self.cur_c = 1
        self.cur_saved_r = 1
        self.cur_saved_c = 1
        self.scroll_row_start = 1
        self.scroll_row_end = self.rows
        self.w = [([SPACE] * self.cols) for _ in range(self.rows)]

    def _decode(self, s):
        """This converts from the external coding system (as passed to
        the constructor) to the internal one (unicode). """
        pass

    def _unicode(self):
        """This returns a printable representation of the screen as a unicode
        string (which, under Python 3.x, is the same as 'str'). The end of each
        screen line is terminated by a newline."""
        pass
    if PY3:
        __str__ = _unicode
    else:
        __unicode__ = _unicode

        def __str__(self):
            """This returns a printable representation of the screen. The end of
            each screen line is terminated by a newline. """
            encoding = self.encoding or 'ascii'
            return self._unicode().encode(encoding, 'replace')

    def dump(self):
        """This returns a copy of the screen as a unicode string. This is similar to
        __str__/__unicode__ except that lines are not terminated with line
        feeds."""
        pass

    def pretty(self):
        """This returns a copy of the screen as a unicode string with an ASCII
        text box around the screen border. This is similar to
        __str__/__unicode__ except that it adds a box."""
        pass

    def cr(self):
        """This moves the cursor to the beginning (col 1) of the current row.
        """
        pass

    def lf(self):
        """This moves the cursor down with scrolling.
        """
        pass

    def crlf(self):
        """This advances the cursor with CRLF properties.
        The cursor will line wrap and the screen may scroll.
        """
        pass

    def newline(self):
        """This is an alias for crlf().
        """
        pass

    def put_abs(self, r, c, ch):
        """Screen array starts at 1 index."""
        pass

    def put(self, ch):
        """This puts a characters at the current cursor position.
        """
        pass

    def insert_abs(self, r, c, ch):
        """This inserts a character at (r,c). Everything under
        and to the right is shifted right one character.
        The last character of the line is lost.
        """
        pass

    def get_region(self, rs, cs, re, ce):
        """This returns a list of lines representing the region.
        """
        pass

    def cursor_constrain(self):
        """This keeps the cursor within the screen area.
        """
        pass

    def cursor_force_position(self, r, c):
        """Identical to Cursor Home."""
        pass

    def cursor_save(self):
        """Save current cursor position."""
        pass

    def cursor_unsave(self):
        """Restores cursor position after a Save Cursor."""
        pass

    def cursor_save_attrs(self):
        """Save current cursor position."""
        pass

    def cursor_restore_attrs(self):
        """Restores cursor position after a Save Cursor."""
        pass

    def scroll_constrain(self):
        """This keeps the scroll region within the screen region."""
        pass

    def scroll_screen(self):
        """Enable scrolling for entire display."""
        pass

    def scroll_screen_rows(self, rs, re):
        """Enable scrolling from row {start} to row {end}."""
        pass

    def scroll_down(self):
        """Scroll display down one line."""
        pass

    def scroll_up(self):
        """Scroll display up one line."""
        pass

    def erase_end_of_line(self):
        """Erases from the current cursor position to the end of the current
        line."""
        pass

    def erase_start_of_line(self):
        """Erases from the current cursor position to the start of the current
        line."""
        pass

    def erase_line(self):
        """Erases the entire current line."""
        pass

    def erase_down(self):
        """Erases the screen from the current line down to the bottom of the
        screen."""
        pass

    def erase_up(self):
        """Erases the screen from the current line up to the top of the
        screen."""
        pass

    def erase_screen(self):
        """Erases the screen with the background color."""
        pass

    def set_tab(self):
        """Sets a tab at the current position."""
        pass

    def clear_tab(self):
        """Clears tab at the current position."""
        pass

    def clear_all_tabs(self):
        """Clears all tabs."""
        pass
