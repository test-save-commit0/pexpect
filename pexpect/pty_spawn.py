import os
import sys
import time
import pty
import tty
import errno
import signal
from contextlib import contextmanager
import ptyprocess
from ptyprocess.ptyprocess import use_native_pty_fork
from .exceptions import ExceptionPexpect, EOF, TIMEOUT
from .spawnbase import SpawnBase
from .utils import which, split_command_line, select_ignore_interrupts, poll_ignore_interrupts


@contextmanager
def _wrap_ptyprocess_err():
    """Turn ptyprocess errors into our own ExceptionPexpect errors"""
    pass


PY3 = sys.version_info[0] >= 3


class spawn(SpawnBase):
    """This is the main class interface for Pexpect. Use this class to start
    and control child applications. """
    use_native_pty_fork = use_native_pty_fork

    def __init__(self, command, args=[], timeout=30, maxread=2000,
        searchwindowsize=None, logfile=None, cwd=None, env=None,
        ignore_sighup=False, echo=True, preexec_fn=None, encoding=None,
        codec_errors='strict', dimensions=None, use_poll=False):
        """This is the constructor. The command parameter may be a string that
        includes a command and any arguments to the command. For example::

            child = pexpect.spawn('/usr/bin/ftp')
            child = pexpect.spawn('/usr/bin/ssh user@example.com')
            child = pexpect.spawn('ls -latr /tmp')

        You may also construct it with a list of arguments like so::

            child = pexpect.spawn('/usr/bin/ftp', [])
            child = pexpect.spawn('/usr/bin/ssh', ['user@example.com'])
            child = pexpect.spawn('ls', ['-latr', '/tmp'])

        After this the child application will be created and will be ready to
        talk to. For normal use, see expect() and send() and sendline().

        Remember that Pexpect does NOT interpret shell meta characters such as
        redirect, pipe, or wild cards (``>``, ``|``, or ``*``). This is a
        common mistake.  If you want to run a command and pipe it through
        another command then you must also start a shell. For example::

            child = pexpect.spawn('/bin/bash -c "ls -l | grep LOG > logs.txt"')
            child.expect(pexpect.EOF)

        The second form of spawn (where you pass a list of arguments) is useful
        in situations where you wish to spawn a command and pass it its own
        argument list. This can make syntax more clear. For example, the
        following is equivalent to the previous example::

            shell_cmd = 'ls -l | grep LOG > logs.txt'
            child = pexpect.spawn('/bin/bash', ['-c', shell_cmd])
            child.expect(pexpect.EOF)

        The maxread attribute sets the read buffer size. This is maximum number
        of bytes that Pexpect will try to read from a TTY at one time. Setting
        the maxread size to 1 will turn off buffering. Setting the maxread
        value higher may help performance in cases where large amounts of
        output are read back from the child. This feature is useful in
        conjunction with searchwindowsize.

        When the keyword argument *searchwindowsize* is None (default), the
        full buffer is searched at each iteration of receiving incoming data.
        The default number of bytes scanned at each iteration is very large
        and may be reduced to collaterally reduce search cost.  After
        :meth:`~.expect` returns, the full buffer attribute remains up to
        size *maxread* irrespective of *searchwindowsize* value.

        When the keyword argument ``timeout`` is specified as a number,
        (default: *30*), then :class:`TIMEOUT` will be raised after the value
        specified has elapsed, in seconds, for any of the :meth:`~.expect`
        family of method calls.  When None, TIMEOUT will not be raised, and
        :meth:`~.expect` may block indefinitely until match.


        The logfile member turns on or off logging. All input and output will
        be copied to the given file object. Set logfile to None to stop
        logging. This is the default. Set logfile to sys.stdout to echo
        everything to standard output. The logfile is flushed after each write.

        Example log input and output to a file::

            child = pexpect.spawn('some_command')
            fout = open('mylog.txt','wb')
            child.logfile = fout

        Example log to stdout::

            # In Python 2:
            child = pexpect.spawn('some_command')
            child.logfile = sys.stdout

            # In Python 3, we'll use the ``encoding`` argument to decode data
            # from the subprocess and handle it as unicode:
            child = pexpect.spawn('some_command', encoding='utf-8')
            child.logfile = sys.stdout

        The logfile_read and logfile_send members can be used to separately log
        the input from the child and output sent to the child. Sometimes you
        don't want to see everything you write to the child. You only want to
        log what the child sends back. For example::

            child = pexpect.spawn('some_command')
            child.logfile_read = sys.stdout

        You will need to pass an encoding to spawn in the above code if you are
        using Python 3.

        To separately log output sent to the child use logfile_send::

            child.logfile_send = fout

        If ``ignore_sighup`` is True, the child process will ignore SIGHUP
        signals. The default is False from Pexpect 4.0, meaning that SIGHUP
        will be handled normally by the child.

        The delaybeforesend helps overcome a weird behavior that many users
        were experiencing. The typical problem was that a user would expect() a
        "Password:" prompt and then immediately call sendline() to send the
        password. The user would then see that their password was echoed back
        to them. Passwords don't normally echo. The problem is caused by the
        fact that most applications print out the "Password" prompt and then
        turn off stdin echo, but if you send your password before the
        application turned off echo, then you get your password echoed.
        Normally this wouldn't be a problem when interacting with a human at a
        real keyboard. If you introduce a slight delay just before writing then
        this seems to clear up the problem. This was such a common problem for
        many users that I decided that the default pexpect behavior should be
        to sleep just before writing to the child application. 1/20th of a
        second (50 ms) seems to be enough to clear up the problem. You can set
        delaybeforesend to None to return to the old behavior.

        Note that spawn is clever about finding commands on your path.
        It uses the same logic that "which" uses to find executables.

        If you wish to get the exit status of the child you must call the
        close() method. The exit or signal status of the child will be stored
        in self.exitstatus or self.signalstatus. If the child exited normally
        then exitstatus will store the exit return code and signalstatus will
        be None. If the child was terminated abnormally with a signal then
        signalstatus will store the signal value and exitstatus will be None::

            child = pexpect.spawn('some_command')
            child.close()
            print(child.exitstatus, child.signalstatus)

        If you need more detail you can also read the self.status member which
        stores the status returned by os.waitpid. You can interpret this using
        os.WIFEXITED/os.WEXITSTATUS or os.WIFSIGNALED/os.TERMSIG.

        The echo attribute may be set to False to disable echoing of input.
        As a pseudo-terminal, all input echoed by the "keyboard" (send()
        or sendline()) will be repeated to output.  For many cases, it is
        not desirable to have echo enabled, and it may be later disabled
        using setecho(False) followed by waitnoecho().  However, for some
        platforms such as Solaris, this is not possible, and should be
        disabled immediately on spawn.

        If preexec_fn is given, it will be called in the child process before
        launching the given command. This is useful to e.g. reset inherited
        signal handlers.

        The dimensions attribute specifies the size of the pseudo-terminal as
        seen by the subprocess, and is specified as a two-entry tuple (rows,
        columns). If this is unspecified, the defaults in ptyprocess will apply.

        The use_poll attribute enables using select.poll() over select.select()
        for socket handling. This is handy if your system could have > 1024 fds
        """
        super(spawn, self).__init__(timeout=timeout, maxread=maxread,
            searchwindowsize=searchwindowsize, logfile=logfile, encoding=
            encoding, codec_errors=codec_errors)
        self.STDIN_FILENO = pty.STDIN_FILENO
        self.STDOUT_FILENO = pty.STDOUT_FILENO
        self.STDERR_FILENO = pty.STDERR_FILENO
        self.str_last_chars = 100
        self.cwd = cwd
        self.env = env
        self.echo = echo
        self.ignore_sighup = ignore_sighup
        self.__irix_hack = sys.platform.lower().startswith('irix')
        if command is None:
            self.command = None
            self.args = None
            self.name = '<pexpect factory incomplete>'
        else:
            self._spawn(command, args, preexec_fn, dimensions)
        self.use_poll = use_poll

    def __str__(self):
        """This returns a human-readable string that represents the state of
        the object. """
        s = []
        s.append(repr(self))
        s.append('command: ' + str(self.command))
        s.append('args: %r' % (self.args,))
        s.append('buffer (last %s chars): %r' % (self.str_last_chars, self.
            buffer[-self.str_last_chars:]))
        s.append('before (last %s chars): %r' % (self.str_last_chars, self.
            before[-self.str_last_chars:] if self.before else ''))
        s.append('after: %r' % (self.after,))
        s.append('match: %r' % (self.match,))
        s.append('match_index: ' + str(self.match_index))
        s.append('exitstatus: ' + str(self.exitstatus))
        if hasattr(self, 'ptyproc'):
            s.append('flag_eof: ' + str(self.flag_eof))
        s.append('pid: ' + str(self.pid))
        s.append('child_fd: ' + str(self.child_fd))
        s.append('closed: ' + str(self.closed))
        s.append('timeout: ' + str(self.timeout))
        s.append('delimiter: ' + str(self.delimiter))
        s.append('logfile: ' + str(self.logfile))
        s.append('logfile_read: ' + str(self.logfile_read))
        s.append('logfile_send: ' + str(self.logfile_send))
        s.append('maxread: ' + str(self.maxread))
        s.append('ignorecase: ' + str(self.ignorecase))
        s.append('searchwindowsize: ' + str(self.searchwindowsize))
        s.append('delaybeforesend: ' + str(self.delaybeforesend))
        s.append('delayafterclose: ' + str(self.delayafterclose))
        s.append('delayafterterminate: ' + str(self.delayafterterminate))
        return '\n'.join(s)

    def _spawn(self, command, args=[], preexec_fn=None, dimensions=None):
        """This starts the given command in a child process. This does all the
        fork/exec type of stuff for a pty. This is called by __init__. If args
        is empty then command will be parsed (split on spaces) and args will be
        set to parsed arguments. """
        if not isinstance(args, list):
            args = [args]

        if not args:
            self.args = split_command_line(command)
            self.command = self.args[0]
        else:
            self.args = [command] + args
            self.command = command

        command_with_path = which(self.command)
        if command_with_path is None:
            raise ExceptionPexpect('The command was not found or was not executable: %s.' % self.command)

        self.command = command_with_path
        self.args[0] = self.command

        self.name = '<' + ' '.join(self.args) + '>'

        assert self.pid is None, 'The pid member should be None.'
        assert self.command is not None, 'The command member should not be None.'

        kwargs = {'echo': self.echo, 'preexec_fn': preexec_fn}
        if dimensions is not None:
            kwargs['dimensions'] = dimensions

        self.ptyproc = self._spawnpty(self.args, env=self.env, cwd=self.cwd, **kwargs)

        self.pid = self.ptyproc.pid
        self.child_fd = self.ptyproc.fd

        self.terminated = False
        self.closed = False

    def _spawnpty(self, args, **kwargs):
        """Spawn a pty and return an instance of PtyProcess."""
        return ptyprocess.PtyProcess.spawn(args, **kwargs)

    def close(self, force=True):
        """This closes the connection with the child application. Note that
        calling close() more than once is valid. This emulates standard Python
        behavior with files. Set force to True if you want to make sure that
        the child is terminated (SIGKILL is sent if the child ignores SIGHUP
        and SIGINT). """
        if not self.closed:
            self.flush()
            self.ptyproc.close(force=force)
            self.isalive()  # Update exit status
            self.child_fd = -1
            self.closed = True

    def isatty(self):
        """This returns True if the file descriptor is open and connected to a
        tty(-like) device, else False.

        On SVR4-style platforms implementing streams, such as SunOS and HP-UX,
        the child pty may not appear as a terminal device.  This means
        methods such as setecho(), setwinsize(), getwinsize() may raise an
        IOError. """
        return os.isatty(self.child_fd)

    def waitnoecho(self, timeout=-1):
        """This waits until the terminal ECHO flag is set False. This returns
        True if the echo mode is off. This returns False if the ECHO flag was
        not set False before the timeout. This can be used to detect when the
        child is waiting for a password. Usually a child application will turn
        off echo mode when it is waiting for the user to enter a password. For
        example, instead of expecting the "password:" prompt you can wait for
        the child to set ECHO off::

            p = pexpect.spawn('ssh user@example.com')
            p.waitnoecho()
            p.sendline(mypassword)

        If timeout==-1 then this method will use the value in self.timeout.
        If timeout==None then this method to block until ECHO flag is False.
        """
        if timeout == -1:
            timeout = self.timeout
        if timeout is not None:
            end_time = time.time() + timeout
        while True:
            if not self.getecho():
                return True
            if timeout is not None and time.time() > end_time:
                return False
            time.sleep(0.1)

    def getecho(self):
        """This returns the terminal echo mode. This returns True if echo is
        on or False if echo is off. Child applications that are expecting you
        to enter a password often set ECHO False. See waitnoecho().

        Not supported on platforms where ``isatty()`` returns False.  """
        if not self.isatty():
            raise IOError('getecho() failed: device is not a tty')
        return self.ptyproc.getecho()

    def setecho(self, state):
        """This sets the terminal echo mode on or off. Note that anything the
        child sent before the echo will be lost, so you should be sure that
        your input buffer is empty before you call setecho(). For example, the
        following will work as expected::

            p = pexpect.spawn('cat') # Echo is on by default.
            p.sendline('1234') # We expect see this twice from the child...
            p.expect(['1234']) # ... once from the tty echo...
            p.expect(['1234']) # ... and again from cat itself.
            p.setecho(False) # Turn off tty echo
            p.sendline('abcd') # We will set this only once (echoed by cat).
            p.sendline('wxyz') # We will set this only once (echoed by cat)
            p.expect(['abcd'])
            p.expect(['wxyz'])

        The following WILL NOT WORK because the lines sent before the setecho
        will be lost::

            p = pexpect.spawn('cat')
            p.sendline('1234')
            p.setecho(False) # Turn off tty echo
            p.sendline('abcd') # We will set this only once (echoed by cat).
            p.sendline('wxyz') # We will set this only once (echoed by cat)
            p.expect(['1234'])
            p.expect(['1234'])
            p.expect(['abcd'])
            p.expect(['wxyz'])


        Not supported on platforms where ``isatty()`` returns False.
        """
        if not self.isatty():
            raise IOError('setecho() failed: device is not a tty')
        self.ptyproc.setecho(state)

    def read_nonblocking(self, size=1, timeout=-1):
        """This reads at most size characters from the child application. It
        includes a timeout. If the read does not complete within the timeout
        period then a TIMEOUT exception is raised. If the end of file is read
        then an EOF exception will be raised.  If a logfile is specified, a
        copy is written to that log.

        If timeout is None then the read may block indefinitely.
        If timeout is -1 then the self.timeout value is used. If timeout is 0
        then the child is polled and if there is no data immediately ready
        then this will raise a TIMEOUT exception.

        The timeout refers only to the amount of time to read at least one
        character. This is not affected by the 'size' parameter, so if you call
        read_nonblocking(size=100, timeout=30) and only one character is
        available right away then one character will be returned immediately.
        It will not wait for 30 seconds for another 99 characters to come in.

        On the other hand, if there are bytes available to read immediately,
        all those bytes will be read (up to the buffer size). So, if the
        buffer size is 1 megabyte and there is 1 megabyte of data available
        to read, the buffer will be filled, regardless of timeout.

        This is a wrapper around os.read(). It uses select.select() or
        select.poll() to implement the timeout. """
        if timeout == -1:
            timeout = self.timeout
        
        if not self.isalive():
            raise EOF('End Of File (EOF). Child process has exited.')

        if self.use_poll:
            poller = poll_ignore_interrupts()
            poller.register(self.child_fd, POLLIN)
        else:
            poller = None

        try:
            s, _ = self._read_nonblocking_impl(size, timeout, poller)
        except TIMEOUT:
            self.flag_eof = True
            raise

        self._log(s, 'read')
        return s

    def write(self, s):
        """This is similar to send() except that there is no return value.
        """
        pass

    def writelines(self, sequence):
        """This calls write() for each element in the sequence. The sequence
        can be any iterable object producing strings, typically a list of
        strings. This does not add line separators. There is no return value.
        """
        pass

    def send(self, s):
        """Sends string ``s`` to the child process, returning the number of
        bytes written. If a logfile is specified, a copy is written to that
        log.

        The default terminal input mode is canonical processing unless set
        otherwise by the child process. This allows backspace and other line
        processing to be performed prior to transmitting to the receiving
        program. As this is buffered, there is a limited size of such buffer.

        On Linux systems, this is 4096 (defined by N_TTY_BUF_SIZE). All
        other systems honor the POSIX.1 definition PC_MAX_CANON -- 1024
        on OSX, 256 on OpenSolaris, and 1920 on FreeBSD.

        This value may be discovered using fpathconf(3)::

            >>> from os import fpathconf
            >>> print(fpathconf(0, 'PC_MAX_CANON'))
            256

        On such a system, only 256 bytes may be received per line. Any
        subsequent bytes received will be discarded. BEL (``''``) is then
        sent to output if IMAXBEL (termios.h) is set by the tty driver.
        This is usually enabled by default.  Linux does not honor this as
        an option -- it behaves as though it is always set on.

        Canonical input processing may be disabled altogether by executing
        a shell, then stty(1), before executing the final program::

            >>> bash = pexpect.spawn('/bin/bash', echo=False)
            >>> bash.sendline('stty -icanon')
            >>> bash.sendline('base64')
            >>> bash.sendline('x' * 5000)
        """
        pass

    def sendline(self, s=''):
        """Wraps send(), sending string ``s`` to child process, with
        ``os.linesep`` automatically appended. Returns number of bytes
        written.  Only a limited number of bytes may be sent for each
        line in the default terminal mode, see docstring of :meth:`send`.
        """
        pass

    def _log_control(self, s):
        """Write control characters to the appropriate log files"""
        pass

    def sendcontrol(self, char):
        """Helper method that wraps send() with mnemonic access for sending control
        character to the child (such as Ctrl-C or Ctrl-D).  For example, to send
        Ctrl-G (ASCII 7, bell, '')::

            child.sendcontrol('g')

        See also, sendintr() and sendeof().
        """
        pass

    def sendeof(self):
        """This sends an EOF to the child. This sends a character which causes
        the pending parent output buffer to be sent to the waiting child
        program without waiting for end-of-line. If it is the first character
        of the line, the read() in the user program returns 0, which signifies
        end-of-file. This means to work as expected a sendeof() has to be
        called at the beginning of a line. This method does not send a newline.
        It is the responsibility of the caller to ensure the eof is sent at the
        beginning of a line. """
        pass

    def sendintr(self):
        """This sends a SIGINT to the child. It does not require
        the SIGINT to be the first character on a line. """
        pass

    def eof(self):
        """This returns True if the EOF exception was ever raised.
        """
        pass

    def terminate(self, force=False):
        """This forces a child process to terminate. It starts nicely with
        SIGHUP and SIGINT. If "force" is True then moves onto SIGKILL. This
        returns True if the child was terminated. This returns False if the
        child could not be terminated. """
        pass

    def wait(self):
        """This waits until the child exits. This is a blocking call. This will
        not read any data from the child, so this will block forever if the
        child has unread output and has terminated. In other words, the child
        may have printed output then called exit(), but, the child is
        technically still alive until its output is read by the parent.

        This method is non-blocking if :meth:`wait` has already been called
        previously or :meth:`isalive` method returns False.  It simply returns
        the previously determined exit status.
        """
        pass

    def isalive(self):
        """This tests if the child process is running or not. This is
        non-blocking. If the child was terminated then this will read the
        exitstatus or signalstatus of the child. This returns True if the child
        process appears to be running or False if not. It can take literally
        SECONDS for Solaris to return the right status. """
        pass

    def kill(self, sig):
        """This sends the given signal to the child application. In keeping
        with UNIX tradition it has a misleading name. It does not necessarily
        kill the child unless you send the right signal. """
        pass

    def getwinsize(self):
        """This returns the terminal window size of the child tty. The return
        value is a tuple of (rows, cols). """
        pass

    def setwinsize(self, rows, cols):
        """This sets the terminal window size of the child tty. This will cause
        a SIGWINCH signal to be sent to the child. This does not change the
        physical window size. It changes the size reported to TTY-aware
        applications like vi or curses -- applications that respond to the
        SIGWINCH signal. """
        pass

    def interact(self, escape_character=chr(29), input_filter=None,
        output_filter=None):
        """This gives control of the child process to the interactive user (the
        human at the keyboard). Keystrokes are sent to the child process, and
        the stdout and stderr output of the child process is printed. This
        simply echos the child stdout and child stderr to the real stdout and
        it echos the real stdin to the child stdin. When the user types the
        escape_character this method will return None. The escape_character
        will not be transmitted.  The default for escape_character is
        entered as ``Ctrl - ]``, the very same as BSD telnet. To prevent
        escaping, escape_character may be set to None.

        If a logfile is specified, then the data sent and received from the
        child process in interact mode is duplicated to the given log.

        You may pass in optional input and output filter functions. These
        functions should take bytes array and return bytes array too. Even
        with ``encoding='utf-8'`` support, meth:`interact` will always pass
        input_filter and output_filter bytes. You may need to wrap your
        function to decode and encode back to UTF-8.

        The output_filter will be passed all the output from the child process.
        The input_filter will be passed all the keyboard input from the user.
        The input_filter is run BEFORE the check for the escape_character.

        Note that if you change the window size of the parent the SIGWINCH
        signal will not be passed through to the child. If you want the child
        window size to change when the parent's window size changes then do
        something like the following example::

            import pexpect, struct, fcntl, termios, signal, sys
            def sigwinch_passthrough (sig, data):
                s = struct.pack("HHHH", 0, 0, 0, 0)
                a = struct.unpack('hhhh', fcntl.ioctl(sys.stdout.fileno(),
                    termios.TIOCGWINSZ , s))
                if not p.closed:
                    p.setwinsize(a[0],a[1])

            # Note this 'p' is global and used in sigwinch_passthrough.
            p = pexpect.spawn('/bin/bash')
            signal.signal(signal.SIGWINCH, sigwinch_passthrough)
            p.interact()
        """
        pass

    def __interact_writen(self, fd, data):
        """This is used by the interact() method.
        """
        pass

    def __interact_read(self, fd):
        """This is used by the interact() method.
        """
        pass

    def __interact_copy(self, escape_character=None, input_filter=None,
        output_filter=None):
        """This is used by the interact() method.
        """
        pass


def spawnu(*args, **kwargs):
    """Deprecated: pass encoding to spawn() instead."""
    pass
