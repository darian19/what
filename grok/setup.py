import logging
import os
import sys
import marshal

try:
    import paver.tasks
except ImportError:
    from os.path import exists
    if exists("paver-minilib.zip"):
        import sys
        sys.path.insert(0, "paver-minilib.zip")
    import paver.tasks

import psutil



g_log = logging.getLogger("YOMP.setup")



def logEntry():
    """ Log command line and ancestor processes to help debug when something
    unintended gets called
    """
    proc = psutil.Process(os.getpid())
    parent = proc.parent
    parentPid = parent.pid
    try:
        parentCmdline = parent.cmdline
    except Exception as e:
        # Typically AccessDenied
        parentCmdline = "ERROR: " + repr(e)
    grandparent = parent.parent
    if grandparent is not None:
        grandparentPid = grandparent.pid
        try:
            grandparentCmdline = grandparent.cmdline
        except Exception as e:
            # Typically AccessDenied
            grandparentCmdline = "N/A: " + repr(e)
    else:
        grandparentPid = None
        grandparentCmdline = None

    g_log.info("%s called: pid=%s, cmdline=%r; "
             "parentPid=%s, parentCmdline=%r; "
             "grandparentPid=%s, grandparentCmdline=%r",
             sys.argv[0], proc.pid, proc.cmdline,
             parentPid, parentCmdline,
             grandparentPid, grandparentCmdline)



logEntry()

try:
    paver.tasks.main()
except:
    g_log.exception("paver.tasks.main() failed")
    raise
