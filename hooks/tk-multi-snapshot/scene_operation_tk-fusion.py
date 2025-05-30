# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import time
import pprint
import traceback

import sgtk
from sgtk import Hook
from sgtk import TankError

import BlackmagicFusion as bmd

pf = pprint.pformat
fusion = bmd.scriptapp("Fusion")


__author__ = "Diego Garcia Huerta"
__email__ = "diegogh2000@gmail.com"


class SceneOperation(Hook):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(self, operation, file_path, **kwargs):
        """
        Main hook entry point

        :operation: String
                    Scene operation to perform

        :file_path: String
                    File path to use if the operation
                    requires it (e.g. open)

        :returns:   Depends on operation:
                    'current_path' - Return the current scene
                                     file path as a String
                    all others     - None
        """
        logger = self.parent.engine.logger

        logger.info("Starting snapshots operations... ".ljust(80, "-"))
        logger.info(f"operation: {operation}")
        logger.info(f"file_path: {file_path}")

        comp = fusion.GetCurrentComp()

        if operation == "current_path":
            return comp.GetAttrs()['COMPS_FileName']

        elif operation == "open":
            if not file_path:
                logger.error("No file path provided")
                return
            if comp:
                while not comp.GetAttrs()['COMPB_Locked']:
                    comp.Lock()

                comp.Close()

            comp = None
            max_tries = 5
            counter = 0
            while not comp and counter < max_tries:
                comp = fusion.LoadComp(file_path)
                logger.info(f"try {counter + 1}, comp: {comp}")
                try:
                    if comp and comp.GetToolList():
                        break
                except Exception as e:
                    logger.error(
                        f"Error loading comp: {e}, full traceback:\n{traceback.format_exc()}"
                    )
                    comp = None
                    counter += 1
                    time.sleep(2)

            logger.info(f"comp after loop: {comp}")
            if comp:
                while comp.GetAttrs()['COMPB_Locked']:
                    comp.Unlock()

        elif operation == "save":
            if not file_path:
                logger.error("No file path provided")
                return

            while not comp.GetAttrs()['COMPB_Locked']:
                comp.Lock()
            comp.Save(file_path)
            while comp.GetAttrs()['COMPB_Locked']:
                comp.Unlock()
