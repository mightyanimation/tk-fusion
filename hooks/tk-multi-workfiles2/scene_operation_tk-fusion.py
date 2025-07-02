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
import re
import sys
import imp
import pyseq
import shutil
import pprint
import logging
import traceback

import sgtk
from sgtk.platform.qt import QtGui

import BlackmagicFusion as bmd
fusion = bmd.scriptapp("Fusion")

pp = pprint.pprint
pf = pprint.pformat


fusion = bmd.scriptapp("Fusion")

__author__ = "Diego Garcia Huerta"
__email__ = "diegogh2000@gmail.com"


HookClass = sgtk.get_hook_baseclass()


class SceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(
        self,
        operation,
        file_path,
        context,
        parent_action,
        file_version,
        read_only,
        **kwargs
    ):
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
        engine = app.engine
        logger = engine.logger

        logger.debug("-" * 50)
        logger.debug("operation: {}".format(operation))
        logger.debug("file_path: {}".format(file_path))
        logger.debug("context: {}".format(context))
        logger.debug("parent_action: {}".format(parent_action))
        logger.debug("file_version: {}".format(file_version))
        logger.debug("read_only: {}".format(read_only))

        # fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()

        if operation == "current_path":
            return comp.GetAttrs()["COMPS_FileName"]

        elif operation == "open":
            if comp:
                while not comp.GetAttrs()["COMPB_Locked"]:
                    comp.Lock()
                    comp.Close()
            comp = fusion.LoadComp(file_path)
            comp = fusion.GetCurrentComp()
            while comp.GetAttrs()["COMPB_Locked"]:
                comp.Unlock()

            engine.change_context(context)

        elif operation == "save":
            if file_path is not None:
                # self.update_fusion_saver_nodes(comp, work_fields)
                self.update_fusion_saver_nodes(file_path)
                comp.Save(file_path)
                engine.change_context(context)

        elif operation == "save_as":
            if file_path is not None:
                self.save_as(file_path, context)

        elif operation == "reset":
            successfully_reset = self.reset(context)

            # if successfully_reset:
            #     engine.change_context(context)

            return successfully_reset

    def save_as(self, file_path, context):
        engine = self.parent.engine
        if not context:
            context = engine.context
        logger = engine.logger

        logger.info("About to run save_as from hook...")
        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()

        engine.change_context(context)
        comp.Save(file_path)

        self.update_fusion_saver_nodes(file_path)


    def reset(self, context):
        engine = self.parent.engine
        logger = engine.logger

        logger.info("About to run reset from hook...")
        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()

        try:
            if comp:
                while not comp.GetAttrs()["COMPB_Locked"]:
                    comp.Lock()

                comp.Close()
                fusion.NewComp()
            else:
                fusion.NewComp()

            comp = fusion.GetCurrentComp()
            while comp.GetAttrs()["COMPB_Locked"]:
                comp.Unlock()

            engine.change_context(context)

        except Exception as e:
            logger.error("Error creating a new scene: {}".format(e))
            return False

        return True

    # def fusion_setupScene(self, comp, context):
    #     """All operations to start working in fusion"""
    #     if comp is None:
    #         return

    #     # Default value
    #     FIRST_FRAME = 1001
    #     LAST_FRAME = 1100
    #     FRAME_WIDTH = 1920
    #     FRAME_HEIGHT = 1080
    #     FPS = 24
    #     WORKING_COLOR_SPACE = "sRGB"
    #     OUTPUT_COLOR_SPACE = "ACEScg"

    #     sg = self.parent.engine.shotgun

    #     entity_type = context.entity.get("type")
    #     entity_name = context.entity.get("name")

    #     if entity_type == "Shot":
    #         sg_proj = self.parent.engine.context.project
    #         shot_filter = [["project", "is", sg_proj], ["code", "is", entity_name]]
    #         shot_fields = [
    #             "sg_cut_in",
    #             "sg_cut_out",
    #             "project.Project.sg_fps",
    #             "project.Project.sg_working_color_space",
    #             "project.Project.sg_output_color_space",
    #         ]
    #         sg_shot = sg.find_one("Shot", shot_filter, shot_fields)

    #         if sg_shot is not None:
    #             if sg_shot.get("sg_cut_in"):
    #                 FIRST_FRAME = sg_shot["sg_cut_in"]

    #             if sg_shot.get("sg_cut_out"):
    #                 LAST_FRAME = sg_shot["sg_cut_out"]

    #             if sg_shot.get("project.Project.sg_fps"):
    #                 FPS = sg_shot["project.Project.sg_fps"]

    #             if sg_shot.get("project.Project.sg_working_color_space"):
    #                 WORKING_COLOR_SPACE = sg_shot.get(
    #                     "project.Project.sg_working_color_space"
    #                 )

    #             if sg_shot.get("project.Project.sg_output_color_space"):
    #                 OUTPUT_COLOR_SPACE = sg_shot.get(
    #                     "project.Project.sg_output_color_space"
    #                 )

    #     # TODO setup OCIO config project and active comp
    #     # TODO check current context first and last frame

    #     while not comp.GetAttrs()["COMPB_Locked"]:
    #         comp.Lock()
    #     comp.SetAttrs(
    #         {
    #             "COMPN_RenderStartTime": FIRST_FRAME,
    #             "COMPN_GlobalStart": FIRST_FRAME,
    #             "COMPN_RenderStart": FIRST_FRAME,
    #             "COMPN_CurrentTime": FIRST_FRAME,
    #             "COMPN_RenderEndTime": LAST_FRAME,
    #             "COMPN_RenderEnd": LAST_FRAME,
    #             "COMPN_GlobalEnd": LAST_FRAME,
    #         }
    #     )

    #     comp.SetPrefs(
    #         {
    #             # "Comp.FrameFormat.Name":       "Test HDTV 1080",
    #             "Comp.FrameFormat.Width": FRAME_WIDTH,
    #             "Comp.FrameFormat.Height": FRAME_HEIGHT,
    #             "Comp.FrameFormat.AspectX": 1.0,
    #             "Comp.FrameFormat.AspectY": 1.0,
    #             # "Comp.FrameFormat.GuideRatio": 1.77777777777778,
    #             "Comp.FrameFormat.Rate": FPS,
    #             "Comp.FrameFormat.DepthInteractive": 2,  # 16 bits Float
    #             "Comp.FrameFormat.DepthFull": 2,  # 16 bits Float
    #             "Comp.FrameFormat.DepthPreview": 2,  # 16 bits Float
    #         }
    #     )
    #     while comp.GetAttrs()["COMPB_Locked"]:
    #         comp.Unlock()

    # # def update_fusion_saver_nodes (self, the_comp, work_fields):
    #     try:
    #         only_selected_nodes = False
    #         list_of_tools       = the_comp.GetToolList (only_selected_nodes, "Saver")
    #         self.parent.logger.debug("List of tools values are: %s" % list_of_tools)

    #         for index, tool in iter(list_of_tools.items()):
    #             clip_path = tool.GetAttrs()['TOOLST_Clip_Name'].values()[0]
    #             if clip_path in [None, "", " "]:
    #                 continue
    #             is_saver_node    = tool.GetData("Shotgrid_Saver_Node")
    #             fields           = None
    #             current_template = None
    #             new_render_path  = None

    #             if is_saver_node:
    #                 self.parent.logger.debug("Saver node was FOUND!: %s" % tool)
    #                 template_name    = tool.GetData ("Current_template")
    #                 current_template = self.parent.sgtk.templates[template_name]
    #                 self.parent.logger.info("Detected Node template: %s" % str(template_name))
    #                 if not 'version' in fields.keys():
    #                     continue
    #             else:
    #                 current_template = self.parent.sgtk.template_from_path(clip_path)
    #                 if current_template is None:
    #                     continue

    #             fields = current_template.get_fields(clip_path)
    #             for tool_field in fields.keys():
    #                 # Update the fields
    #                 if tool_field in work_fields.keys():
    #                     fields[tool_field]=work_fields[tool_field]

    #             new_render_path  = current_template.apply_fields(fields)
    #             tool.Clip        = new_render_path

    #     except:
    #         import traceback
    #         self.parent.logger.error(traceback.format_exc())

    def update_fusion_saver_nodes(self, file_path):
        self.parent.logger.info("Updating saver nodes...".ljust(100, "-"))

        self.parent.engine._FusionEngine__update_nodes_version(file_path)

        # comp = fusion.GetCurrentComp()
        # try:
        #     only_selected_nodes = False
        #     savers_dict = comp.GetToolList(only_selected_nodes, "Saver")
        #     self.parent.logger.info(f"savers_dict:\n{(pf(savers_dict))}")

        #     # Ensure savers use the newer metadata key "Shotgrid_Saver_Node" instead of
        #     # the old one "Shotgun_Saver_Node".
        #     savers_dict = self.parent.engine._FusionEngine__update_saver_metadata(savers_dict)

        #     for index, tool in savers_dict.items():
        #         is_saver_node = tool.GetData("Shotgrid_Saver_Node")
        #         if not is_saver_node:
        #             is_saver_node = tool.GetData("Shotgrid_Saver_Node_Extra")
        #         if is_saver_node:
        #             self.parent.logger.debug("Saver node was FOUND!: %s" % tool)
        #             work_template_name = tool.GetData("Work_Template")
        #             self.parent.logger.info(
        #                 "Detected Node work template: %s" % str(work_template_name)
        #             )
        #             self.parent.logger.info(str(self.parent.sgtk.templates))
        #             work_template_obj = self.parent.sgtk.templates[work_template_name]
        #             fields = work_template_obj.get_fields(file_path)
        #             render_template_name = tool.GetData("Render_Template")
        #             self.parent.logger.info(
        #                 "Detected Node render template: %s" % str(render_template_name)
        #             )
        #             render_template_obj = self.parent.sgtk.templates[
        #                 render_template_name
        #             ]
        #             new_render_path = render_template_obj.apply_fields(fields).replace(
        #                 "%04d", ""
        #             )
        #             tool.Clip = new_render_path
        # except Exception as e:
        #     self.parent.logger.error(
        #         "Error updating fusion saver nodes: {}, full traceback:\n{}".format(
        #             e, traceback.format_exc()
        #         )
        #     )

    # def publish_render_saver_nodes(
    #     self,
    #     item,
    #     output,
    #     work_template,
    #     comment,
    #     thumbnail_path,
    #     sg_task,
    #     primary_task,
    #     primary_publish_path,
    #     progress_cb,
    # ):
    #     # TODO en lugar de escanear imagenes en imagen template
    #     # Verificar que solo exiat un saver node existente,
    #     #  Verificar que el saver node tenga la metadata (Extradata, sg worktemplate, sg render template)
    #     #
    #     #
    #     # E.g. only_selected_nodes = False
    #     #    list_of_tools = the_comp.GetToolList (only_selected_nodes, "Saver")
    #     try:
    #         self.parent.logger.info("STARTING FUSION SECONDARY PUBLISH RENDER SAVER")
    #         progress_cb(5, "Gathering Data")
    #         render_template_name = item["other_params"]["render_template_name"]
    #         render_template_path = item["other_params"]["render_template_path"].replace(
    #             "/", os.sep
    #         )
    #         self.parent.logger.debug("SCANNING renders from: " + render_template_path)
    #         main_path = os.path.dirname(render_template_path)
    #         self.parent.logger.debug("main_path: %s" % main_path)
    #         images_names = os.listdir(main_path)
    #         self.parent.logger.debug("there are: %s images" % len(images_names))
    #         pre_images_list = []
    #         s_images_list = []
    #         for image in images_names:
    #             new_image = main_path + os.path.sep + image
    #             self.parent.logger.debug("image: %s" % new_image)
    #             pre_images_list.append(new_image)
    #             s_images_list.append(new_image)
    #         sequence = pyseq.Sequence(s_images_list)
    #         images_list = []
    #         for seq in sequence:
    #             for image in pre_images_list:
    #                 if seq in image:
    #                     images_list.append(image)
    #         images_list.sort()
    #         self.parent.logger.debug(str(images_list))
    #         # playable_file = os.path.dirname(images_path) + os.path.sep + sequence.format("%h%p%t")
    #         frames_length = sequence.length()
    #         progress_cb(15, "Preparing to Copy Files")
    #         publish_template = output["publish_template"]
    #         fields = work_template.get_fields(item["other_params"]["work_file_path"])
    #         publish_version = fields["version"]
    #         tank_type = output["tank_type"]
    #         publish_path = publish_template.apply_fields(fields)
    #         publish_name = os.path.basename(publish_path)
    #         if not "name" in fields:
    #             ver = re.search(r"_v[0-9]+", publish_name, re.M | re.I)
    #             if ver:
    #                 ver = ver.group()
    #                 basename, ext = os.path.splitext(publish_name)
    #                 new_name = publish_name.replace(ver, "").replace(ext, "")
    #         else:
    #             new_name = fields["name"]
    #         if not os.path.exists(os.path.dirname(publish_path)):
    #             os.makedirs(os.path.dirname(publish_path))
    #         increase_value = 70.0 / frames_length
    #         current_value = 15
    #         for image in images_list:
    #             progress_cb(
    #                 current_value + increase_value,
    #                 "Copying %s" % os.path.basename(image),
    #             )
    #             self.parent.logger.info("copying: %s" % image)
    #             destination = (
    #                 os.path.dirname(publish_path)
    #                 + os.path.sep
    #                 + os.path.basename(image)
    #             )
    #             self.parent.logger.info("to: %s" % destination)
    #             shutil.copy(image, destination)
    #             current_value += increase_value
    #         # register the publish:
    #         progress_cb(85, "Registering the publish")
    #         args = {
    #             "tk": self.parent.tank,
    #             "context": self.parent.context,
    #             "comment": comment,
    #             "path": publish_path,
    #             "name": new_name,
    #             "version_number": publish_version,
    #             "thumbnail_path": thumbnail_path,
    #             "task": sg_task,
    #             "dependency_paths": [primary_publish_path],
    #             "published_file_type": tank_type,
    #         }
    #         sg_publishes = sgtk.util.register_publish(**args)
    #         progress_cb(100, "Done")
    #     except:
    #         error = traceback.format_exc()
    #         self.parent.logger.error(error)
    #         raise sgtk.TankError(error)
