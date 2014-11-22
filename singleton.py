#! /usr/bin/env python

# Software License:
# Python Software Foundation License Version 2
# See: PSF-LICENSE.txt for the full license.

# Python Imports
import sys
import os
import time
import tempfile
import unittest
import logging
import signal
from multiprocessing import Process

# Our Imports
import lockfile

class SingleInstance(object):

    """
    If you want to prevent your script from running in parallel just instantiate
    SingleInstance() class. If is there another instance already running it will
    exit the application with the message "Another instance is already running,
    quitting.", returning -1 error code.

    >>> import tendo
    ... me = SingleInstance()

    This option is very useful if you have scripts executed by crontab at small
    amounts of time.

    Remember that this works by creating a lock file with a filename based on
    the full path to the script file.
    """

    def __init__(self, flavor_id=""):
        self.lockfile = self.lockfile_path(flavor_id)
        self.lock = lockfile.Lock(self.lockfile)
        self.fobj = None

        logger.debug("SingleInstance lockfile: " + self.lockfile)

        self.fobj = self.lock.acquire(trylock=True)

        if self.fobj is None:
            logger.error("Another instance is already running, quitting.")
            sys.exit(-1)
        else:
            # Make sure our pid is in the file
            self.fobj.write('%d\n' % os.getpid())
            self.fobj.flush()

        self.initialized = True

    @staticmethod
    def lockfile_path(flavor_id="", program_path=None):
        """
        Generates a lock file path based on the location of the executable,
        and flavor_id.
        """

        if program_path is None:
            program_path = sys.argv[0]

        program_noext, _ = os.path.splitext(os.path.abspath(program_path))
        basename = program_noext. \
            replace("/", "-"). \
            replace(":", ""). \
            replace("\\", "-") + '-%s' % flavor_id + '.lock'

        return os.path.normpath(tempfile.gettempdir() + '/' + basename)

    @staticmethod
    def get_pid(program_path, flavor_id=""):
        """
        Gets the pid of the given program if it's running, None otherwise.
        """

        lockpath = SingleInstance.lockfile_path(flavor_id=flavor_id,
                                                program_path=program_path)

        pid = None

        if os.path.exists(lockpath):
            c = open(lockpath).read()
            if c.endswith('\n'):
                pid = int(c)

        return pid


    def __del__(self):
        try:
            self.lock.release()
        except Exception as e:
            if logger:
                logger.warning(e)
            else:
                print("Unloggable error: %s" % e)
            sys.exit(-1)

def f(name, func=lambda:1+1):
    tmp = logger.level
    logger.setLevel(logging.CRITICAL)  # we do not want to see the warning
    me2 = SingleInstance(flavor_id=name)
    logger.setLevel(tmp)
    func()
    pass


def crash():
    """
    Crash the Python interpreter so we test what happens in cashes.
    """
    import ctypes
    i = ctypes.c_char('a')
    j = ctypes.pointer(i)
    c = 0
    while True:
        j[c] = 'a'
        c += 1
    j


def loop_until_signal():
    """
    Runs until a SIGTERM is received
    """

    global run_loop
    run_loop = True

    def stop_loop(signum, frame):
        global run_loop
        run_loop = False

    signal.signal(signal.SIGTERM, stop_loop)

    start = time.time()

    while True:
        time.sleep(0.1)

        duration = time.time() - start
        if not run_loop or duration > 5:
            break


class testSingleton(unittest.TestCase):

    def test_1(self):
        me = SingleInstance(flavor_id="test-1")
        del me  # now the lock should be removed
        assert True

    def test_2(self):
        p = Process(target=f, args=("test-2",))
        p.start()
        p.join()
        # the called function should succeed
        assert p.exitcode == 0, "%s != 0" % p.exitcode

    def test_3(self):
        me = SingleInstance(flavor_id="test-3")
        p = Process(target=f, args=("test-3",))
        p.start()
        p.join()
        # the called function should fail because we already have another
        # instance running
        assert p.exitcode != 0, "%s != 0 (2nd execution)" % p.exitcode

        # note, we return -1 but this translates to 255 meanwhile we'll consider
        # that anything different from 0 is good
        p = Process(target=f, args=("test-3",))
        p.start()
        p.join()
        # the called function should fail because we already have another
        # instance running
        assert p.exitcode != 0, "%s != 0 (3rd execution)" % p.exitcode

    def test_crash(self):
        """
        Make sure that when the program, the lock file doesn't stick properly.
        """
        p = Process(target=f, args=("test-crash",crash))
        p.start()
        p.join()

        # Make sure the test fails
        self.assertNotEquals(0, p.exitcode)

        # Make sure the lock file still exists, to prove we didn't clean up
        # properly
        lockpath = SingleInstance.lockfile_path('test-crash')
        self.assertTrue(os.path.exists(lockpath))

        # Make sure we can acquire the lock after the program opens
        p = Process(target=f, args=("test-crash",))
        p.start()
        p.join()

        self.assertEquals(0, p.exitcode)

    def test_get_pid(self):
        # Start up the process
        p = Process(target=f, args=("test-pid",loop_until_signal))
        p.start()

        # Try and find our PID
        start = time.time()

        while True:
            # Try and read the PID
            pid = SingleInstance.get_pid(sys.argv[0], 'test-pid')

            if pid:
                break

            # Make sure we don't spin for too long
            time.sleep(0.1)
            if time.time() - start > 5:
                print "Failure"
                self.fail("Error, timeout trying to read PID")
                p.terminate()

        # Stop the process
        os.kill(p.pid, signal.SIGTERM)

        p.join()

        # Check the pid is correct
        self.assertEquals(p.pid, pid)


logger = logging.getLogger("lockfile.singleton")
logger.addHandler(logging.StreamHandler())

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    unittest.main()
