# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that loads defines all the available actions, broken down by publish type.
"""

import os
import re
import glob
import fileseq
import sgtk
from sgtk.errors import TankError
import traceback


HookBaseClass = sgtk.get_hook_baseclass()


class FusionActions(HookBaseClass):
    # public interface - to be overridden by deriving classes

    def generate_actions(self, sg_publish_data, actions, ui_area):
        """
        Returns a list of action instances for a particular publish.
        This method is called each time a user clicks a publish somewhere in
        the UI.
        The data returned from this hook will be used to populate the actions
        menu for a publish.

        The mapping between Publish types and actions are kept in a different
        place (in the configuration) so at the point when this hook is called,
        the loader app has already established *which* actions are appropriate
        for this object.

        The hook should return at least one action for each item passed in via
        the actions parameter.

        This method needs to return detailed data for those actions, in the
        form of a list of dictionaries, each with name, params, caption and
        description keys.

        Because you are operating on a particular publish, you may tailor the
        output  (caption, tooltip etc) to contain custom information suitable
        for this publish.

        The ui_area parameter is a string and indicates where the publish is to
        be shown.
        - If it will be shown in the main browsing area, "main" is passed.
        - If it will be shown in the details area, "details" is passed.
        - If it will be shown in the history area, "history" is passed.

        Please note that it is perfectly possible to create more than one
        action "instance" for an action! You can for example do scene
        introspection - if the action passed in is "character_attachment"
        you may for example scan the scene, figure out all the nodes
        where this object can be attached and return a list of action
        instances:
        "attach to left hand", "attach to right hand" etc. In this case,
        when more than one object is returned for an action, use the params
        key to pass additional data into the run_action hook.

        :param sg_publish_data: Shotgun data dictionary with all the standard
                                publish fields.
        :param actions: List of action strings which have been defined in the
                        app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and
         description
        """
        app = self.parent
        engine = app.engine
        logger = engine.logger

        logger.info(
            (
                "Generate actions called for UI element {}. "
                "Actions: {}. Publish Data: {}"
            ).format(ui_area, actions, sg_publish_data)
        )

        action_instances = []

        if "loader_node" in actions:
            action_instances.append(
                {
                    "name": "loader_node",
                    "params": None,
                    "caption": "Create Loader Node",
                    "description": "This will add a loader node to the current scene.",
                }
            )

        if "ensure_local" in actions:
            action_instances.append(
                {
                    "name": "ensure_local",
                    "params": None,
                    "caption": "Download",
                    "description": (
                        "This will very if the file exists in the local file system, "
                        "if not, it will be downloaded."
                    ),
                }
            )

        if "copy_path" in actions:
            action_instances.append(
                {
                    "name": "copy_path",
                    "params": None,
                    "caption": "Copy path",
                    "description": "This will copy the publish path into the clipboard.",
                }
            )

        return action_instances

    def execute_multiple_actions(self, actions):
        """
        Executes the specified action on a list of items.

        The default implementation dispatches each item from ``actions`` to
        the ``execute_action`` method.

        The ``actions`` is a list of dictionaries holding all the actions to
        execute.
        Each entry will have the following values:

            name: Name of the action to execute
            sg_publish_data: Publish information coming from Shotgun
            params: Parameters passed down from the generate_actions hook.

        .. note::
            This is the default entry point for the hook. It reuses the
            ``execute_action`` method for backward compatibility with hooks
            written for the previous version of the loader.

        .. note::
            The hook will stop applying the actions on the selection if an
            error is raised midway through.

        :param list actions: Action dictionaries.
        """
        app = self.parent
        engine = app.engine
        logger = engine.logger

        for single_action in actions:
            logger.info("Single Action: %s" % single_action)
            name = single_action["name"]
            sg_publish_data = single_action["sg_publish_data"]
            params = single_action["params"]

            try:
                self.execute_action(name, params, sg_publish_data)
                # play sound from config hook 'play_sounds'
                logger.info("Playing sound, reached end of execute_action")
                engine.execute_hook_expression(
                    "{config}/notifications.py",
                    "success_sound",
                )
            except Exception as e:
                msg = "Error executing action {}: {}, full traceback:\n{}".format(
                    name, e, traceback.format_exc()
                )
                engine.logger.error(msg)
                # play sound from config hook 'play_sounds'
                logger.info("Playing sound, error raised in execute_action")
                engine.execute_hook_expression(
                    "{config}/notifications.py",
                    "error_sound",
                )

    def execute_action(self, name, params, sg_publish_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned
                     by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_publish_data: Shotgun data dictionary with all the standard
                                publish fields.
        :returns: No return value expected.
        """
        app = self.parent
        engine = app.engine
        logger = engine.logger

        logger.info(
            (
                "Execute action called for action {}. Parameters: {}. "
                "Publish Data: {}"
            ).format(name, params, sg_publish_data)
        )

        # resolve path
        path = self.get_publish_path(sg_publish_data)
        path = self.fix_path(path)

        if name == "loader_node":
            self.ensure_file_is_local(path, sg_publish_data)
            self._create_loader_node(path, sg_publish_data)

        if name == "ensure_local":
            self.ensure_file_is_local(path, sg_publish_data)

        if name == "copy_path":
            self._copy_publish_path(path)

    # helper methods which can be subclassed in custom hooks to fine tune the
    # behaviour of things

    def _create_loader_node(self, path, sg_publish_data):
        """
        Create a loader node representing the publish.

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard
                                publish fields.
        """
        app = self.parent
        engine = app.engine
        logger = engine.logger

        import BlackmagicFusion as bmd

        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()

        (_, ext) = os.path.splitext(path)

        valid_extensions = [
            ".png",
            ".jpg",
            ".jpeg",
            ".exr",
            ".cin",
            ".dpx",
            ".tiff",
            ".tif",
            ".mov",
            ".mp4",
            ".psd",
            ".tga",
            ".ari",
            ".gif",
            ".iff",
        ]

        if ext.lower() not in valid_extensions:
            msg = "Unsupported file extension for '{}'!".format(path)
            logger.error(msg)
            raise Exception(msg)

        # find the sequence range if it has one and if it's a sequence:
        if ext not in [".mov", ".mp4"]:
            seq_range = self._find_sequence_range(path)
        else:
            seq_range = None

        while not comp.GetAttrs()["COMPB_Locked"]:
            comp.Lock()

        # only get the first frame in the sequences range if it's actually a sequence
        if seq_range:
            path = path % seq_range[0]

        path = self.fix_path(path)
        node_name = os.path.basename(path).split(".")[0]
        load_data = {
            "TOOLS_Name": node_name,
            "TOOLB_NameSet": True,
        }

        x_pos, y_pos = self.get_good_position(comp)
        logger.info("good position, x: {}, y: {}".format(x_pos, y_pos))
        loader = comp.AddTool("Loader", x_pos, y_pos)
        loader.Clip = path
        loader.SetAttrs(load_data)

        if seq_range:
            # override the detected frame range.
            trim_out = int(seq_range[1]) - int(seq_range[0])
            globalStart = comp.GetAttrs("COMPN_GlobalStart")
            loader.GlobalIn = globalStart
            loader.GlobalOut = globalStart + trim_out
            loader.ClipTimeStart = 0
            loader.ClipTimeEnd = trim_out
            loader.TrimOut = trim_out

        fields = {}
        publish_template = self.parent.engine.sgtk.template_from_path(path)
        if publish_template:
            fields = publish_template.get_fields(path)

        buffer = fields.get("buffer", "")
        if buffer:
            loader.SetData("sg_buffer", buffer)
            metadata_ = {"buffer": buffer}
        else:
            metadata_ = {}

        meta_keys = ["version_number", "code", "name", "id", "entity"]
        if sg_publish_data is not None:
            for k, val in sg_publish_data.items():
                if k in meta_keys:
                    metadata_[k] = val

        loader.SetData("sg_metadata", metadata_)

        while comp.GetAttrs()["COMPB_Locked"]:
            comp.Unlock()

    def _find_sequence_range(self, path):
        """
        Find the sequence range of a given path using fileseq.

        :param path: Path to check
        :return: A tuple of two integers representing the start and end of the
                 sequence. If no sequence is detected, returns None.
        """
        app = self.parent
        engine = app.engine
        logger = engine.logger

        try:
            fileseq_obj = fileseq.findSequenceOnDisk(path)
        except Exception as e:
            logger.error(
                "Failed to find sequence on disk: {}, full traceback:\n{}".format(
                    e, traceback.format_exc()
                )
            )
            return None

        if not fileseq_obj:
            return None

        return (fileseq_obj.start(), fileseq_obj.end())

    def _copy_publish_path(self, path):
        """
        Copy the publish path to the clipboard.

        :param path: The path to copy to the clipboard
        :return: None
        """
        import pyperclip

        pyperclip.copy(path)

    def get_good_position(self, comp, x_offset=0, y_offset=3):
        """
        Finds a good position to create a new node in the flow view of the
        given comp. A good position is one that is not occupied by any other
        node. The position is calculated by finding the node with the highest
        x and y coordinates and then adding an offset to it. The offset is
        applied to both the x and y axes. The x axis offset is increased by
        half the width of a tool node to avoid overlapping.

        :param comp: The comp object to query
        :param x_offset: The offset to apply to the x axis
        :param y_offset: The offset to apply to the y axis
        :return: A tuple of two floats representing the x and y coordinates of
                 the good position
        """
        # when the position of a node is queried, it returns the coordinates of the
        # top left corner, but when a new node is created, the coordinates are applied
        # to the center of the node, thus we need to offset at least the x axis
        x_tool_width_offset = 0.5
        flow = comp.CurrentFrame.FlowView
        max_x = None
        max_y = None

        all_tools = comp.GetToolList(False).values()
        if not list(all_tools):
            return 0, 0

        for tool in all_tools:
            pos = flow.GetPosTable(tool)
            if not pos:
                continue
            x = pos.get(1)
            y = pos.get(2)

            # store higest values
            if max_x is None:
                max_x = x
            elif x > max_x:
                max_x = x

            if max_y is None:
                max_y = y
            elif y > max_y:
                max_y = y

        # apply the offsets
        max_x += x_tool_width_offset
        max_x += x_offset
        max_y += y_offset

        return max_x, max_y

    def fix_path(self, path):
        """Replace all backward slashes with forward slashes."""

        path = path.replace("\\\\", "/")
        path = path.replace("\\", "/")

        return path
