# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import sgtk
from sgtk import TankError
import BlackmagicFusion as bmd


__author__ = "Diego Garcia Huerta"
__email__ = "diegogh2000@gmail.com"


HookBaseClass = sgtk.get_hook_baseclass()


class FrameOperation(HookBaseClass):
    """
    Hook called to perform a frame operation with the
    current scene
    """

    def execute(self, operation, head_in_frame=None, in_frame=None, out_frame=None, tail_out_frame=None, **kwargs):
        """
        Main hook entry point

        :operation: String
                    Frame operation to perform

        :in_frame: int
                    in_frame for the current context (e.g. the current shot,
                                                      current asset etc)

        :out_frame: int
                    out_frame for the current context (e.g. the current shot,
                                                      current asset etc)

        :returns:   Depends on operation:
                    'set_frame_range' - Returns if the operation was succesfull
                    'get_frame_range' - Returns the frame range in the form
                                        (in_frame, out_frame)
        """
        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()
        #comp = fusion.GetAttrs()["FUSIONH_CurrentComp"]

        #if comp is None:
        #    bmd2 = imp.load_dynamic('fusionscript', 'C:\\Program Files\\Blackmagic Design\\Fusion 16\\fusionscript.dll')
        #    fusion2 =  bmd2.scriptapp('Fusion')
        #    comp = fusion2.GetCurrentComp()


        if comp is None:
            # print(fusion.GetCompList())
            for key, c in fusion.GetCompList().items():
                if not 'SetAttrs' in dir(c):
                    # print('Ignoring {}, {}'.format(key, c))
                    comp = c.Composition()
                    cur_comp = str(c.GetAttrs()["COMPS_Name"])
                    comp_path = str(c.GetAttrs()["COMPS_FileName"])
                    print("current comp: {}, path: {}".format(cur_comp, comp_path))
                comp = c
                self.fusion_setupScene(comp, in_frame, head_in_frame,
                    out_frame, tail_out_frame)

        print(15*'*/')
        print(15*'*/')
        comp.SetAttrs({'COMPN_GlobalEnd' : 10})
        comp.SetAttrs({'COMPN_RenderEnd': 10})

        if operation == "get_frame_range":
            current_in = int(comp.GetAttrs()["COMPN_GlobalStart"])
            current_out = int(comp.GetAttrs()["COMPN_GlobalEnd"])
            return (current_in, current_out)

        elif operation == "set_frame_range":
            # set frame ranges for plackback
            comp.SetAttrs({'COMPN_GlobalEnd' : out_frame})
            comp.SetAttrs({'COMPN_RenderEnd': tail_out_frame})
            comp.SetAttrs({'COMPN_GlobalStart' : in_frame})
            comp.SetAttrs({'COMPN_RenderStart': head_in_frame})
            return True


    def fusion_setupScene(self, comp, in_frame, head_in_frame, out_frame, tail_out_frame):
        """ All operations to start working in fusion """
        print(30 * "*")
        print("Initializing ")

        FIRST_FRAME = 1001
        LAST_FRAME = 1100
        FRAME_WIDTH = 1920
        FRAME_HEIGHT = 1080
        FPS = 25

        comp.SetAttrs({
            'COMPN_RenderStartTime': head_in_frame,
            'COMPN_RenderStart': head_in_frame,
            'COMPN_GlobalStart': in_frame,

            'COMPN_CurrentTime': head_in_frame,

            'COMPN_RenderEndTime': tail_out_frame,
            'COMPN_RenderEnd': tail_out_frame,
            'COMPN_GlobalEnd': out_frame,
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
        print(30 * "*")
        print(15 * "-*")
