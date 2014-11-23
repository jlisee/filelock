FileLock
=========

This is a pair of modules that help with coordinating the actions of
multiple programs on a single computer. This is derived from the
tendo.singleton code found here:

    https://github.com/pycontribs/tendo

And the py-lockfile code from here:

    https://github.com/benediktschmitt/py-filelock

lockfile
---------

This allows for two different processes to have an exclusive lock based on
a path on the file system. It uses os.O_EXCL on windows and fcntl API
otherwise.

This contains a file based lock class, example usage:

```python
from lockfile import LockFile

with LockFile('/tmp/lock_name.tmp'):
    # Do important stuff that needs to be synchronized
```

Or using the direct interface:

```python
try:
    lock = FileLock('/tmp/lock_name.tmp'):
    lock.acquire()
    # Do important stuff that needs to be synchronized
    ...
finally:
    lock.release()
```


singleton
----------

This limits you to a single version of a program.  If you are not the first
instance of your program you will automatically exit.

```python
import singleton
me = singleton.SingleInstance()
# Only one instance based this point
```


Other LockFile Implementions
-----------------------------

 - [lockfile] - popular link and mkdir based implementation
 - [Py-FileLock] - cross platform locking library
 - [FileLock] - os.O_EXCL class
 - [fcntl example] - how to use fnctl to create a lock


[lockfile]: https://pypi.python.org/pypi/lockfile
[Py-FileLock]: https://pypi.python.org/pypi/filelock/
[FileLock]: http://www.evanfosmark.com/2009/01/cross-platform-file-locking-support-in-python/
[fcntl example]: http://blog.vmfarms.com/2011/03/cross-process-locking-and.html