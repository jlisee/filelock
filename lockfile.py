# Software License:
# Python Software Foundation License Version 2
# See: PSF-LICENSE.txt for the full license.

import errno
import os
import sys


class FileLock(object):
    """
    A cross platform system wide file based lock object.
    """

    def __init__(self, path):
        self.lockfile = path
        self.initialized = False
        self.fobj = None

    def acquire(self, trylock=False):
        """
        Returns the resulting file locking object, None if trylock=False and the
        lock is not acquired.
        """
        self.initialized = True
        self.fobj = self.acquire_lockfile(self.lockfile, block=not trylock)
        return self.fobj

    def release(self):
        """
        This may throw if their is an issue.
        """
        import sys
        import os
        if not self.initialized or self.fobj is None:
            return

        if sys.platform == 'win32':
            os.close(self.fobj)
            os.unlink(self.lockfile)
        else:
            import fcntl
            fcntl.lockf(self.fobj, fcntl.LOCK_UN)
            # os.close(self.fobj)
            if os.path.isfile(self.lockfile):
                os.unlink(self.lockfile)

        self.initialized = False
        self.fobj = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, type, value, traceback):
        self.release()

    def __del__(self):
        if not self.initialized:
            return

        self.release()

    @staticmethod
    def acquire_lockfile(lockpath, block=True):
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
                flags = fcntl.LOCK_EX
                if not block:
                    flags |= fcntl.LOCK_NB
                fcntl.lockf(fobj, flags)
            except IOError:
                return None

        return fobj
