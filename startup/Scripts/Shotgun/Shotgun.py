import os
import sgtk
import sys
import BlackmagicFusion as bmd
import time
import pprint
import random
import importlib
import traceback
from datetime import datetime

pp = pprint.pprint
pf = pprint.pformat


# lock file to avoid run engine creation twice!!
# Fusion issues...
lockfile = os.path.join(os.environ["APPDATA"], "Mighty", "FusionEngine", "Lock")
container = os.path.dirname(lockfile)
mighty_folder = os.path.dirname(container)

# Check if folder exists
if not os.path.exists(container):
    os.makedirs(container, exist_ok=True)

# Validate old lock files
if os.path.exists(lockfile):
    print("Old lock file found")
    created_time = time.ctime(os.path.getctime(lockfile))
    created_time2 = datetime.strptime(created_time, "%a %b %d %H:%M:%S %Y")
    current_time = datetime.now()
    time_difference = current_time - created_time2
    dif_seconds = time_difference.total_seconds()
    # If the lock file is older than 12 seconds,
    # then we will erase it
    if dif_seconds > 12:
        # delete file
        try:
            os.remove(lockfile)
        except:
            print(
                "Old lock file can not be removed, delete manually\n{}".format(lockfile)
            )

# Getting time to create the lock file
time.sleep(random.uniform(0.0, 2.0))
if not os.path.exists(lockfile):
    print("Creating new lock file")
    with open(lockfile, "w"):
        pass

    fusion = bmd.scriptapp("Fusion")
    comp = fusion.GetCurrentComp()
    if comp is None:
        importlib.reload(bmd)
        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()

    print("fusion: {}".format(fusion))
    print("comp: {}".format(comp))

    print("Launching toolkit in classic mode.")

    env_engine = os.environ.get("SGTK_ENGINE")
    env_context = os.environ.get("SGTK_CONTEXT")
    context = sgtk.context.deserialize(env_context)

    # if comp is not None:
    try:
        path = comp.GetAttrs()["COMPS_FileName"]
        print("comp path: {}".format(path))
        tk = sgtk.sgtk_from_path(path)
        print("tk from path: {}".format(tk))
        context = tk.context_from_path(path)
        print("context from path: {}".format(context))
    except Exception as e:
        # print(traceback.format_exc())
        # pass
        msg = (
            "Couldn't get context from path: {}, error: {}, "
            "full traceback:\n{}"
        ).format(path, e, traceback.format_exc())
        print("Couldn't get context from path: {}".format(path))

    print("Initializing Fusion engine")
    # try:
    engine = sgtk.platform.start_engine(env_engine, context.sgtk, context)
    if os.path.exists(lockfile):
        os.remove(lockfile)

    engine.logger.info("Before calling _qt_app.exec()")

    try:
        engine._qt_app.exec()
        engine.logger.info("After calling _qt_app.exec()")
    except Exception as e:
        msg = "Error starting engine: {}, full traceback:\n{}".format(
            e, traceback.format_exc()
        )
        print(msg)
        engine.logger.error(msg)
        raise Exception(msg)
    # except Exception as e:
    #     if os.path.exists(lockfile):
    #         os.remove(lockfile)
    #     engine.logger.error(
    #         "Error starting engine: {},\nfull traceback:\n{}".format(
    #             e, traceback.format_exc()
    #         )
    #     )
