﻿# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import glob
import os
import sgtk

import BlackmagicFusion as bmd
fusion = bmd.scriptapp("Fusion")


HookBaseClass = sgtk.get_hook_baseclass()


class FusionSessionCollector(HookBaseClass):
    """
    Collector that operates on the fusion session. Should inherit from the basic
    collector hook.
    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """

        # grab any base class settings
        collector_settings = super(FusionSessionCollector, self).settings or {}

        # settings specific to this collector
        fusion_session_settings = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for artist work files. Should "
                               "correspond to a template defined in "
                               "templates.yml. If configured, is made available"
                               "to publish plugins via the collected item's "
                               "properties. ",
            },
        }

        # update the base settings with these settings
        collector_settings.update(fusion_session_settings)

        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session open in Fusion and parents a subtree of
        items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance

        """

        # create an item representing the current fusion session
        item = self.collect_current_fusion_session(settings, parent_item)

        #self.collect_sg_savernodes(item)

    def collect_current_fusion_session(self, settings, parent_item):
        """
        Creates an item that represents the current fusion session.

        :param parent_item: Parent Item instance

        :returns: Item of type fusion.session
        """

        publisher = self.parent

        # get the path to the current file
        path = _session_path()

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Fusion Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "fusion.session",
            "Fusion Session",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "fusion.png"
        )
        session_item.set_icon_from_path(icon_path)

        # if a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins
        work_template_setting = settings.get("Work Template")
        if work_template_setting:

            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value)

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            session_item.properties["work_template"] = work_template
            session_item.properties["publish_type"] = "Fusion Composition"
            self.logger.debug("Work template defined for Fusion collection.")

        self.logger.info("Collected current Fusion scene")

        return session_item

    def collect_sg_savernodes(self, parent_item):

        comp = fusion.GetCurrentComp()

        publisher = self.parent
        engine = publisher.engine

        path = comp.GetAttrs()['COMPS_FileName']
        work_template = engine.sgtk.template_from_path(path)
        work_version = work_template.get_fields(path).get('version')

        savers = comp.GetToolList(False, "Saver").values()
        for saver in savers:
            path = saver.GetAttrs()['TOOLST_Clip_Name'].values()[0]

            template = engine.sgtk.template_from_path(path)
            if template:
                fields = template.get_fields(path)
                template_version = fields.get('version')
                if template_version is work_version:
                    frames = template.apply_fields(fields)
                    base, ext = os.path.splitext(frames)
                    if '.mov' not in ext:
                        rendered_paths = glob.glob("%s*%s" % (base, ext))
                        if rendered_paths:
                            super(FusionSessionCollector, self)._collect_file(
                                parent_item,
                                rendered_paths[0],
                                frame_sequence=True
                            )
                    else:
                        if os.path.exists(frames):
                            super(FusionSessionCollector, self)._collect_file(
                                parent_item,
                                frames
                            )

def _session_path():
    """
    Return the path to the current session
    :return:
    """
    comp = fusion.GetCurrentComp()

    path = comp.GetAttrs()['COMPS_FileName']

    # if isinstance(path, unicode):
    #     path = path.encode("utf-8")

    return path


