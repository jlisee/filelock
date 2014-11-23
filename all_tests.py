#! /usr/bin/env python

# Software License:
# Python Software Foundation License Version 2
# See: PSF-LICENSE.txt for the full license.

import logging
import os
import signal
import sys
import time
import unittest
from multiprocessing import Process

from singleton import SingleInstance, logger
from lockfile import FileLock



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

    # Create a pointer with value of 42
    INTP = ctypes.POINTER(ctypes.c_int)
    ptr = INTP.from_address(42)

    # Now try to de-reference it, causing a segfault
    print ptr.contents


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


class TestSingleton(unittest.TestCase):

    def test_1(self):
        me = SingleInstance(flavor_id="test-1")

        # Make sure the lock is present
        lockpath = SingleInstance.lockfile_path('test-1')
        self.assertTrue(os.path.exists(lockpath))

        # now the lock should be removed
        del me

        # Make sure the file is not their
        self.assertFalse(os.path.exists(lockpath))

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

    def _get_pid(self, program_path, flavor_id):
        # Try and find our PID
        start = time.time()

        while True:
            # Try and read the PID
            pid = SingleInstance.get_pid(program_path, flavor_id)

            if pid:
                break

            # Make sure we don't spin for too long
            time.sleep(0.1)
            if time.time() - start > 5:
                print "Failure"
                self.fail("Error, timeout trying to read PID")
                p.terminate()

        return pid

    def test_get_pid(self):
        # Start up the process
        p = Process(target=f, args=("test-pid",loop_until_signal))
        p.start()

        pid = self._get_pid(sys.argv[0], 'test-pid')

        pid_path = SingleInstance.pidfile_path('test-pid')
        self.assertTrue(os.path.exists(pid_path))

        # Stop the process
        os.kill(p.pid, signal.SIGTERM)

        p.join()

        # Check the pid is correct
        self.assertEquals(p.pid, pid)

        # Make sure the file is cleaned up
        self.assertFalse(os.path.exists(pid_path))


    def test_get_pid_2(self):
        """Make sure another run attempt doesn't kill our pid file"""
        p = Process(target=f, args=("test-pid",loop_until_signal))
        p.start()

        pid = self._get_pid(sys.argv[0], 'test-pid')
        self.assertEquals(p.pid, pid)

        # Now try starting it again
        p2 = Process(target=f, args=("test-pid",loop_until_signal))
        p2.start()
        p2.join()

        pid = self._get_pid(sys.argv[0], 'test-pid')
        self.assertEquals(p.pid, pid)

        # Stop the process
        os.kill(p.pid, signal.SIGTERM)


class TestLock(unittest.TestCase):

    def test_context(self):
        """
        Make sure the context manager interface works
        """
        path = '/tmp/my-lock-%d' % os.getpid()

        with FileLock(path):
            pass

        lock = FileLock(path)
        with lock:
            pass


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    unittest.main()
