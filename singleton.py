# Software License:
# Python Software Foundation License Version 2
# See: PSF-LICENSE.txt for the full license.

# Python Imports
import sys
import os
import tempfile
import logging

# Our Imports
import lockfile

class SingleInstance(object):

    """
    If you want to prevent your script from running in parallel just instantiate
    SingleInstance() class. If is there another instance already running it will
    exit the application with the message "Another instance is already running,
    quitting.", returning -1 error code.

    >>> import singleton
    ... me = singleton.SingleInstance()

    This option is very useful if you have scripts executed by crontab at small
    amounts of time.

    Remember that this works by creating a lock file with a filename based on
    the full path to the script file.
    """

    def __init__(self, flavor_id=""):
        self.lockfile = self.lockfile_path(flavor_id)
        self.lock = lockfile.FileLock(self.lockfile)
        self.fd = None

        logger.debug("SingleInstance lockfile: " + self.lockfile)

        try:
            self.lock.acquire(timeout=0)
        except lockfile.Timeout:
            pass

        if self.lock.is_locked():
            self.fd = self.lock._lock_file_fd

        if self.fd is None:
            logger.error("Another instance is already running, quitting.")
            sys.exit(-1)
        else:
            # Make sure our pid is in the file
            os.write(self.fd, '%d\n' % os.getpid())

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

logger = logging.getLogger("lockfile.singleton")
logger.addHandler(logging.StreamHandler())
