#! /usr/bin/env python

# Software License:
# Python Software Foundation License Version 2
# See: PSF-LICENSE.txt for the full license.

import sys
import os
import errno
import tempfile
import unittest
import logging
from multiprocessing import Process


class SingleInstance:

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
        import sys
        self.initialized = False
        self.lockfile = self.lockfile_path(flavor_id)

        logger.debug("SingleInstance lockfile: " + self.lockfile)

        self.fobj = self.acquire_lockfile(self.lockfile)

        if self.fobj is None:
            logger.error("Another instance is already running, quitting.")
            sys.exit(-1)

        self.initialized = True

    @staticmethod
    def lockfile_path(flavor_id=""):
        """
        Generates a lock file path based on the location of the executable,
        and flavor_id.
        """

        program_dir, _ = os.path.splitext(os.path.abspath(sys.argv[0]))
        basename = program_dir. \
            replace("/", "-"). \
            replace(":", ""). \
            replace("\\", "-") + '-%s' % flavor_id + '.lock'

        return os.path.normpath(tempfile.gettempdir() + '/' + basename)

    @staticmethod
    def acquire_lockfile(lockpath):
        """
        If successful returns the lock file object, otherwise None.
        """
        fobj = None

        if sys.platform == 'win32':
            try:
                # file already exists, we try to remove (in case previous
                # execution was interrupted)
                if os.path.exists(lockpath):
                    os.unlink(lockpath)
                fobj = os.open(lockpath, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except OSError:
                type, e, tb = sys.exc_info()
                if e.errno == 13:
                    return None
                print(e.errno)
                raise
        else:  # non Windows
            import fcntl
            fobj = open(lockpath, 'w')
            try:
                fcntl.lockf(fobj, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                return None

        return fobj

    def __del__(self):
        import sys
        import os
        if not self.initialized:
            return
        try:
            if sys.platform == 'win32':
                if hasattr(self, 'fobj'):
                    os.close(self.fobj)
                    os.unlink(self.lockfile)
            else:
                import fcntl
                fcntl.lockf(self.fobj, fcntl.LOCK_UN)
                # os.close(self.fobj)
                if os.path.isfile(self.lockfile):
                    os.unlink(self.lockfile)
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


logger = logging.getLogger("tendo.singleton")
logger.addHandler(logging.StreamHandler())

if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    unittest.main()
