import os
import sgtk
import sys
import BlackmagicFusion as bmd
import time

engine = None

fusion = bmd.scriptapp("Fusion")
time.sleep(1) # Getting time to the code lock the current comp
comp = fusion.GetCurrentComp()
if not comp.IsLocked():
    # Running for the first time
    comp.Lock() # Lock comp to avoid to initializate the engine multiple times

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

    print 'Initializing engine'
    engine = sgtk.platform.start_engine(env_engine, context.sgtk, context)
    comp.Unlock()

    from sgtk.platform.qt import QtGui, QtCore
    app = QtGui.QApplication.instance()
    engine._qt_app.exec_()
