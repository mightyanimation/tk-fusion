import os
import sgtk
import sys
import BlackmagicFusion as bmd
import time
import random


# lock file to avoid run engine creation twice!!
# Fusion issues...
lockfile = os.path.join(os.environ["APPDATA"],
                        "Mighty",
                        "FusionEngine",
                        "Lock")
container = os.path.dirname(lockfile)
mighty_folder = os.path.dirname(container)

# Creating Mighty folder in roaming
if not os.path.exists(mighty_folder):
    os.mkdir(mighty_folder)

# Check if folder exists
if not os.path.exists(container):
    os.mkdir(container)

# Getting time to create the lock file
time.sleep(random.uniform(0.0, 2.0))
if not os.path.exists(lockfile):
    with open(lockfile, 'w'): pass
    
    fusion = bmd.scriptapp("Fusion")
    comp = fusion.GetCurrentComp()

    logger = sgtk.LogManager.get_logger(__name__)
    logger.debug("Launching toolkit in classic mode.")

    env_engine = os.environ.get("SGTK_ENGINE")
    env_context = os.environ.get("SGTK_CONTEXT")
    context = sgtk.context.deserialize(env_context)

    try:
        path = comp.GetAttrs()['COMPS_FileName']
        tk = sgtk.sgtk_from_path(path)
        context = tk.context_from_path(path)
    except:
        pass

    logger.debug('Initializing engine')
    engine = sgtk.platform.start_engine(env_engine, context.sgtk, context)
    if os.path.exists(lockfile):
        os.remove(lockfile)

    from sgtk.platform.qt import QtGui, QtCore
    engine._qt_app.exec_()

