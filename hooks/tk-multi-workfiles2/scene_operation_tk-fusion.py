# ------------------------------------------------------------------------------
# Copyright (C) 2018 Diego Garcia Huerta - All Rights Reserved
#
# CONFIDENTIAL AND PROPRIETARY
#
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential
# Written by Diego Garcia Huerta <diegogh2000@gmail.com>. October 2018
# ------------------------------------------------------------------------------
import os
import sgtk
import sys
from sgtk.platform.qt import QtGui
import imp
import logging

#sys.path.append("C:\\Program Files\\Blackmagic Design\\Fusion 16\\fusionscript.dll")

import BlackmagicFusion as bmd
fusion = bmd.scriptapp("Fusion")

__author__ = "Diego Garcia Huerta"
__email__ = "diegogh2000@gmail.com"


HookClass = sgtk.get_hook_baseclass()


class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(self, operation, file_path, context, parent_action,
                file_version, read_only, **kwargs):
        """
        Main hook entry point

        :param operation:       String
                                Scene operation to perform

        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)

        :param context:         Context
                                The context the file operation is being
                                performed in.

        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as
                                - version_up

        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.

        :param read_only:       Specifies if the file should be opened read-only or not

        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty
                                                 state, otherwise False
                                all others     - None
        """
        app = self.parent

        app.log_debug("-"*50)
        app.log_debug('operation: %s' % operation)
        app.log_debug('file_path: %s' % file_path)
        app.log_debug('context: %s' % context)
        app.log_debug('parent_action: %s' % parent_action)
        app.log_debug('file_version: %s' % file_version)
        app.log_debug('read_only: %s' % read_only)

        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()

        print 24 * '*'
        print fusion.GetAttrs()['FUSIONS_FileName']
        print 24 * '*'

        comp.Lock()
        if operation == "current_path":
            return comp.GetAttrs()['COMPS_FileName']
        elif operation == "open":
            if comp:
                comp.Close()
            comp = fusion.LoadComp(file_path)
        elif operation == "save":
            comp.Save(file_path)
        elif operation == "save_as":
            comp.Save(file_path)
        elif operation == "reset":
            print 'new context >>>', context
            return self.reset(comp, context)

    def reset(self, comp, context):
        if comp:
            comp.Close()
        fusion.NewComp()
        comp = fusion.GetCurrentComp()
        #comp = fusion._NewComp()
        self.fusion_setupScene(comp, context)
        return True


    def fusion_setupScene(self, comp, context):
        """ All operations to start working in fusion """
        print "Initializing "
        
        FIRST_FRAME = 1001
        LAST_FRAME = 1100
        FRAME_WIDTH = 1920
        FRAME_HEIGHT = 1080
        FPS = 25

        comp.SetAttrs({
            'COMPN_RenderStartTime': FIRST_FRAME, 
            'COMPN_GlobalStart': FIRST_FRAME,
            'COMPN_RenderStart': FIRST_FRAME,

            'COMPN_CurrentTime': FIRST_FRAME,

            'COMPN_RenderEndTime': LAST_FRAME,
            'COMPN_RenderEnd': LAST_FRAME,
            'COMPN_GlobalEnd': LAST_FRAME,
            })

        comp.SetPrefs({
            "Comp.FrameFormat.Name": "Test HDTV 1080",
            "Comp.FrameFormat.Width": FRAME_WIDTH,
            "Comp.FrameFormat.Height": FRAME_HEIGHT,
            "Comp.FrameFormat.AspectX": 1.0,
            "Comp.FrameFormat.AspectY": 1.0,
            "Comp.FrameFormat.GuideRatio": 1.77777777777778,
            "Comp.FrameFormat.Rate": FPS,
            "Comp.FrameFormat.DepthInteractive": 2,    #16 bits Float
            "Comp.FrameFormat.DepthFull": 2,          #16 bits Float
            "Comp.FrameFormat.DepthPreview": 2        #16 bits Float
            })

        """
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.Information)
        msg.setText(
            "Setup complete.\nRange: {0}-{1}\nResolution {2}x{3}\nFPS{4}".format(
                FIRST_FRAME, LAST_FRAME, FRAME_WIDTH, FRAME_HEIGHT, FPS))
        msg.setInformativeText("This is additional information")
        msg.setWindowTitle("MessageBox demo")
        msg.show()
        """
        #proj:SetSetting('timelineResolutionWidth', "2000")

