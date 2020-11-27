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
import traceback

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

        comp.Lock()
        if operation == "current_path":
            return comp.GetAttrs()['COMPS_FileName']
        elif operation == "open":
            if comp:
                comp.Close()
            comp = fusion.LoadComp(file_path)
            comp.Unlock()
        elif operation == "save":
            self.update_fusion_saver_nodes(comp, file_path)
            comp.Save(file_path)
        elif operation == "save_as":
            self.update_fusion_saver_nodes(comp, file_path)
            comp.Save(file_path)
        elif operation == "reset":
            print 'new context >>>', context
            return self.reset(comp, context)
        comp.Unlock()



    def reset(self, comp, context):
        if comp:
            comp.Close()
        fusion.NewComp()
        comp = fusion.GetCurrentComp()
        #comp = fusion._NewComp()
        self.fusion_setupScene(comp, context)
        comp.Unlock()
        return True


    def fusion_setupScene(self, comp, context):
        """ All operations to start working in fusion """
        print "Initializing "
        
        FIRST_FRAME = 1001
        LAST_FRAME = 1100
        FRAME_WIDTH = 1920
        FRAME_HEIGHT = 1080
        FPS = 25

        # TODO setup OCIO config project and active comp
        # TODO check current context first and last frame

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

    def update_fusion_saver_nodes (self, the_comp, file_path):
        try:
            only_selected_nodes = False
            list_of_tools = the_comp.GetToolList (only_selected_nodes, "Saver")
            self.parent.log_debug ("List of tools values are: %s" % list_of_tools)
            for index, tool in list_of_tools.iteritems ():
                is_saver_node = tool.GetData("Shotgun_Saver_Node")
                if not is_saver_node:
                    is_saver_node = tool.GetData("Shotgun_Saver_Node_Extra")
                if is_saver_node:
                    self.parent.log_debug ("Saver node was FOUND!: %s" % tool)
                    work_template_name = tool.GetData ("Work_Template")
                    self.parent.log_info("Detected Node work template: %s" % str(work_template_name))
                    self.parent.log_info(str(self.parent.sgtk.templates))
                    work_template_obj = self.parent.sgtk.templates[work_template_name]
                    fields = work_template_obj.get_fields (file_path)
                    render_template_name = tool.GetData ("Render_Template")
                    self.parent.log_info("Detected Node render template: %s" % str(render_template_name))
                    render_template_obj = self.parent.sgtk.templates[render_template_name]
                    new_render_path = render_template_obj.apply_fields (fields).replace ("%04d", "")
                    tool.Clip = new_render_path
        except:
            import traceback
            self.parent.log_error(traceback.format_exc())

    def publish_render_saver_nodes (self, item, output, work_template, comment, thumbnail_path, sg_task, primary_task, primary_publish_path, progress_cb):
        # TODO en lugar de escanear imagenes en imagen template
        # Verificar que solo exiat un saver node existente, 
        #  Verificar que el saver node tenga la metadata (Extradata, sg worktemplate, sg render template)
        #  
        # 
        # E.g. only_selected_nodes = False
        #    list_of_tools = the_comp.GetToolList (only_selected_nodes, "Saver")
        try:
            self.parent.log_info ("STARTING FUSION SECONDARY PUBLISH RENDER SAVER")
            progress_cb(05, "Gathering Data") 
            render_template_name = item['other_params']['render_template_name']
            render_template_path = item['other_params']['render_template_path'].replace("/", "\\\\")
            self.parent.log_debug ("SCANNING renders from: " + render_template_path)
            main_path = os.path.dirname (render_template_path)
            self.parent.log_debug ("main_path: %s" % main_path)
            images_names = os.listdir(main_path)
            self.parent.log_debug ("there are: %s images" % len (images_names))
            pre_images_list = []
            s_images_list = []
            for image in images_names:
                new_image = main_path + os.path.sep + image
                self.parent.log_debug ("image: %s" % new_image)
                pre_images_list.append (new_image)
                s_images_list.append (new_image)
            sequence = pyseq.Sequence(s_images_list)
            images_list = []
            for seq in sequence:
                for image in pre_images_list:
                    if seq in image:
                        images_list.append (image)
            images_list.sort ()
            self.parent.log_debug (str (images_list))
            #playable_file = os.path.dirname(images_path) + os.path.sep + sequence.format("%h%p%t")
            frames_length = sequence.length()
            progress_cb(15, "Preparing to Copy Files") 
            publish_template = output['publish_template']
            fields = work_template.get_fields (item['other_params']['work_file_path'])
            publish_version = fields["version"]
            tank_type = output["tank_type"]
            publish_path = publish_template.apply_fields (fields)
            publish_name = os.path.basename (publish_path)
            if not "name" in fields:
                ver = re.search(r'_v[0-9]+', publish_name, re.M|re.I)
                if ver:
                    ver = ver.group()
                    basename, ext = os.path.splitext(publish_name)
                    new_name = publish_name.replace(ver, "").replace(ext, '')
            else:
                new_name = fields['name']
            if not os.path.exists (os.path.dirname (publish_path)):
                os.makedirs (os.path.dirname (publish_path))
            increase_value = 70.0 / frames_length
            current_value = 15
            for image in images_list:
                progress_cb(current_value + increase_value, "Copying %s" % os.path.basename (image))
                self.parent.log_info ("copying: %s" % image)
                destination = os.path.dirname(publish_path) +os.path.sep + os.path.basename(image)
                self.parent.log_info ("to: %s" % destination)
                shutil.copy (image, destination)
                current_value += increase_value
            # register the publish:
            progress_cb(85, "Registering the publish")        
            args = {
                "tk": self.parent.tank,
                "context": self.parent.context,
                "comment": comment,
                "path": publish_path,
                "name": new_name,
                "version_number": publish_version,
                "thumbnail_path": thumbnail_path,
                "task": sg_task,
                "dependency_paths": [primary_publish_path],
                "published_file_type":tank_type
            }
            sg_publishes = tank.util.register_publish(**args)
            progress_cb(100, "Done") 
        except:
            error = traceback.format_exc()
            self.parent.log_error (error)
            raise TankError (error)