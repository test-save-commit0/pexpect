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
    return min if n < min else max if n > max else n


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
        if self.decoder is None:
            return s
        return self.decoder.decode(s)

    def _unicode(self):
        """This returns a printable representation of the screen as a unicode
        string (which, under Python 3.x, is the same as 'str'). The end of each
        screen line is terminated by a newline."""
        return '\n'.join([''.join(row) for row in self.w])
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
        return ''.join([''.join(row) for row in self.w])

    def pretty(self):
        """This returns a copy of the screen as a unicode string with an ASCII
        text box around the screen border. This is similar to
        __str__/__unicode__ except that it adds a box."""
        top_border = '+' + '-' * self.cols + '+\n'
        bottom_border = '\n+' + '-' * self.cols + '+'
        screen_content = '\n'.join(['|' + ''.join(row) + '|' for row in self.w])
        return top_border + screen_content + bottom_border

    def cr(self):
        """This moves the cursor to the beginning (col 1) of the current row.
        """
        self.cur_c = 1

    def lf(self):
        """This moves the cursor down with scrolling.
        """
        if self.cur_r == self.scroll_row_end:
            self.scroll_up()
        else:
            self.cur_r = constrain(self.cur_r + 1, 1, self.rows)

    def crlf(self):
        """This advances the cursor with CRLF properties.
        The cursor will line wrap and the screen may scroll.
        """
        self.cr()
        self.lf()

    def newline(self):
        """This is an alias for crlf().
        """
        self.crlf()

    def put_abs(self, r, c, ch):
        """Screen array starts at 1 index."""
        r = constrain(r, 1, self.rows)
        c = constrain(c, 1, self.cols)
        self.w[r-1][c-1] = ch

    def put(self, ch):
        """This puts a characters at the current cursor position.
        """
        self.put_abs(self.cur_r, self.cur_c, ch)
        self.cur_c = constrain(self.cur_c + 1, 1, self.cols)
        if self.cur_c == 1:
            self.lf()

    def insert_abs(self, r, c, ch):
        """This inserts a character at (r,c). Everything under
        and to the right is shifted right one character.
        The last character of the line is lost.
        """
        r = constrain(r, 1, self.rows)
        c = constrain(c, 1, self.cols)
        self.w[r-1] = self.w[r-1][:c-1] + [ch] + self.w[r-1][c-1:-1]

    def get_region(self, rs, cs, re, ce):
        """This returns a list of lines representing the region.
        """
        rs = constrain(rs, 1, self.rows)
        re = constrain(re, 1, self.rows)
        cs = constrain(cs, 1, self.cols)
        ce = constrain(ce, 1, self.cols)
        return [''.join(row[cs-1:ce]) for row in self.w[rs-1:re]]

    def cursor_constrain(self):
        """This keeps the cursor within the screen area.
        """
        self.cur_r = constrain(self.cur_r, 1, self.rows)
        self.cur_c = constrain(self.cur_c, 1, self.cols)

    def cursor_force_position(self, r, c):
        """Identical to Cursor Home."""
        self.cur_r = constrain(r, 1, self.rows)
        self.cur_c = constrain(c, 1, self.cols)

    def cursor_save(self):
        """Save current cursor position."""
        self.cur_saved_r = self.cur_r
        self.cur_saved_c = self.cur_c

    def cursor_unsave(self):
        """Restores cursor position after a Save Cursor."""
        self.cur_r = self.cur_saved_r
        self.cur_c = self.cur_saved_c

    def cursor_save_attrs(self):
        """Save current cursor position."""
        self.cursor_save()

    def cursor_restore_attrs(self):
        """Restores cursor position after a Save Cursor."""
        self.cursor_unsave()

    def scroll_constrain(self):
        """This keeps the scroll region within the screen region."""
        self.scroll_row_start = constrain(self.scroll_row_start, 1, self.rows)
        self.scroll_row_end = constrain(self.scroll_row_end, 1, self.rows)
        if self.scroll_row_start > self.scroll_row_end:
            self.scroll_row_start, self.scroll_row_end = self.scroll_row_end, self.scroll_row_start

    def scroll_screen(self):
        """Enable scrolling for entire display."""
        self.scroll_row_start = 1
        self.scroll_row_end = self.rows

    def scroll_screen_rows(self, rs, re):
        """Enable scrolling from row {start} to row {end}."""
        self.scroll_row_start = constrain(rs, 1, self.rows)
        self.scroll_row_end = constrain(re, 1, self.rows)
        self.scroll_constrain()

    def scroll_down(self):
        """Scroll display down one line."""
        s = self.scroll_row_start - 1
        e = self.scroll_row_end
        self.w[s+1:e] = self.w[s:e-1]
        self.w[s] = [SPACE] * self.cols

    def scroll_up(self):
        """Scroll display up one line."""
        s = self.scroll_row_start - 1
        e = self.scroll_row_end
        self.w[s:e-1] = self.w[s+1:e]
        self.w[e-1] = [SPACE] * self.cols

    def erase_end_of_line(self):
        """Erases from the current cursor position to the end of the current
        line."""
        self.w[self.cur_r-1][self.cur_c-1:] = [SPACE] * (self.cols - self.cur_c + 1)

    def erase_start_of_line(self):
        """Erases from the current cursor position to the start of the current
        line."""
        self.w[self.cur_r-1][:self.cur_c] = [SPACE] * self.cur_c

    def erase_line(self):
        """Erases the entire current line."""
        self.w[self.cur_r-1] = [SPACE] * self.cols

    def erase_down(self):
        """Erases the screen from the current line down to the bottom of the
        screen."""
        self.erase_end_of_line()
        for r in range(self.cur_r, self.rows):
            self.w[r] = [SPACE] * self.cols

    def erase_up(self):
        """Erases the screen from the current line up to the top of the
        screen."""
        self.erase_start_of_line()
        for r in range(self.cur_r-1):
            self.w[r] = [SPACE] * self.cols

    def erase_screen(self):
        """Erases the screen with the background color."""
        self.w = [[SPACE] * self.cols for _ in range(self.rows)]

    def set_tab(self):
        """Sets a tab at the current position."""
        # This method is not implemented in the original code
        # and would require additional state to track tab positions
        pass

    def clear_tab(self):
        """Clears tab at the current position."""
        # This method is not implemented in the original code
        # and would require additional state to track tab positions
        pass

    def clear_all_tabs(self):
        """Clears all tabs."""
        # This method is not implemented in the original code
        # and would require additional state to track tab positions
        pass
