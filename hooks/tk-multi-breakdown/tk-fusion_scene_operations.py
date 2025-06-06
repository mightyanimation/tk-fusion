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
import re
import time
import pprint
import fileseq
import traceback

import sgtk
from sgtk import Hook
import BlackmagicFusion as bmd

pp = pprint.pprint
pf = pprint.pformat

fusion = bmd.scriptapp("Fusion")


class BreakdownSceneOperations(Hook):
    """
    Breakdown operations for Natron.

    This implementation handles detection of natron read and write nodes.
    """

    def scan_scene(self):
        """
        The scan scene method is executed once at startup and its purpose is
        to analyze the current scene and return a list of references that are
        to be potentially operated on.

        The return data structure is a list of dictionaries. Each scene
        reference that is returned should be represented by a dictionary with
        three keys:

        - "attr": The filename attribute of the 'node' that is to be operated
           on. Most DCCs have a concept of a node, attribute, path or some
           other way to address a particular object in the scene.
        - "type": The object type that this is. This is later passed to the
           update method so that it knows how to handle the object.
        - "path": Path on disk to the referenced object.

        Toolkit will scan the list of items, see if any of the objects matches
        any templates and try to determine if there is a more recent version
        available. Any such versions are then displayed in the UI as out of
        date.
        """
        engine = self.parent.engine
        logger = engine.logger

        logger.info("Starting breakdown scan...".ljust(80, "-"))

        # Introspect the fusion scene for loader and saver nodes
        # so we can gather the filenames available.
        refs = []

        logger.info("Scene operation: getting current comp")
        comp = fusion.GetCurrentComp()
        logger.info(f"comp: {comp}")

        logger.info("Scene operation: lock current comp")
        while not comp.GetAttrs()['COMPB_Locked']:
            comp.Lock()

        logger.info("Scene operation: getting all comp loaders")
        for tool in comp.GetToolList(False, "Loader").values():
            logger.info(
                "Working with tool: {}".format(tool.Name).ljust(80, "-")
            )
            ref_path = list(tool.GetAttrs("TOOLST_Clip_Name").values())
            logger.info(
                "ref_path as is: {}, type: {}".format(ref_path, type(ref_path))
            )
            if not ref_path:
                logger.info("Couldn't get clip path, skipping tool...")
                continue

            if isinstance(ref_path, list):
                ref_path = ref_path[0]
            logger.info(
                "Scanning node {}: {}".format(tool.Name, ref_path)
            )

            pattern = re.compile(
                r"(?P<head>.+)"
                r"(?P<version>[vV]\d{3})"
                r"[\._-]"
                r"(?P<seq>\d{4,6})"
                r"[\._-]"
                r"(?P<ext>.+)"
            )
            match = pattern.match(ref_path)
            if not match:
                logger.warning("Could not match path: {}".format(ref_path))
                continue

            seq_token = match.group("seq")

            path_basename = os.path.basename(ref_path)
            path_dirname = os.path.dirname(ref_path)

            new_path_basename = path_basename.replace(seq_token, "%04d")
            new_path = os.path.join(path_dirname, new_path_basename)
            new_path = self.fix_path(new_path)
            logger.info("new path: {}".format(new_path))

            # refs.append({"node": tool.GetAttrs("TOOLS_Name"), "type": "file", "path": ref_path[0]})
            # {"node": node_name, "type": "reference", "path": maya_path}
            refs.append({"node": tool.GetAttrs("TOOLS_Name"), "type": "Rendered Image", "path": new_path})

        logger.info("Scene operation: unlock current comp")
        comp.Unlock()

        logger.info("Found references:\n{}".format(pf(refs)))
        logger.info("Finished breakdown scan...".ljust(80, "-"))

        return refs

    def update(self, items):
        """
        Perform replacements given a number of scene items passed from the app.

        Once a selection has been performed in the main UI and the user clicks
        the update button, this method is called.

        The items parameter is a list of dictionaries on the same form as was
        generated by the scan_scene hook above. The path key now holds
        the that each attribute should be updated *to* rather than the current
        path.
        """

        comp = fusion.GetCurrentComp()
        engine = self.parent.engine
        logger = engine.logger

        logger.info("Updating breakdown references...".ljust(80, "-"))

        loaders = {}
        for loader in comp.GetToolList(False, "Loader").values():
            loaders[loader.Name] = loader
        logger.info(f"Found loaders:\n{pf(loaders)}")

        logger.info("Getting all item paths...")
        sg_publishes = self.get_item_paths_list(items)

        if not sg_publishes:
            return

        # sort publishes by name in a dict. The name of the publishes usually is the
        # path basename up to (but not including) the version token, but actually
        # including the extension
        sg_publishes_by_name = self.sort_publishes_by_name(sg_publishes)

        logger.info("Iterating through items...".ljust(80, "-"))
        for item in items:
            logger.debug(f"item:\n{pf(item)}")
            node = item.get("node")
            node_type = item.get("type")
            new_path = item.get("path")

            # get th publish name to find the publish dict in our sg_publishes_by_name
            # dictionary. This is needed to update the sg_metadata in the loader node
            pub_name = self.resolve_publish_name(new_path)
            if pub_name:
                sg_metadata = self.get_sg_metadata_dict(
                    sg_publishes_by_name.get(pub_name)
                )
            else:
                sg_metadata = None

            if node_type == "Rendered Image":
                logger.info(f"Updating item: {item}".ljust(60, "-"))
                loader = loaders.get(node)
                if not loader:
                    logger.warning(
                        "loader '{}' not found in loaders: {}".format(
                            node, list(loaders.keys())
                        )
                    )
                    continue

                logger.info(f"File {node}: Updating to version {new_path}")

                logger.info("Scene operation: lock current comp")
                max_tries = 5
                tries = 0
                while not comp.GetAttrs()['COMPB_Locked'] and tries < max_tries:
                    comp.Lock()
                    tries += 1
                    time.sleep(2)

                logger.info(f"Scene operation: locked current comp after {tries} tries")

                # try to get a fileseq obj from the provided path to be able to get
                # the sequence first and last frames.
                logger.info("Scene operation: find sequence on disk")
                fileseq_obj = None
                try:
                    fileseq_obj = fileseq.findSequenceOnDisk(new_path)
                    logger.info(f"Found sequence on disk: {fileseq_obj}")
                except Exception as e:
                    logger.error(
                        "Failed to find sequence on disk: {}, full traceback:\n{}".format(
                            e, traceback.format_exc()
                        )
                    )

                # this should be the default method for getting the sequence info
                if fileseq_obj:
                    try:
                        clip_start_frame = int(fileseq_obj.start())
                        clip_end_frame = int(fileseq_obj.end())
                        clip_length = clip_end_frame - clip_start_frame + 1
                        clip_trim_in = 0
                        clip_trim_out = int(clip_end_frame) - int(clip_start_frame)
                        logger.info("Got values from fileseq obj")
                    except Exception as e:
                        logger.error(
                            (
                                "Failed to get sequence data from fileseq obj: {}, "
                                "full traceback:\n{}"
                            ).format(e, traceback.format_exc())
                        )
                else:
                # this should be just a fallback but not the pimary method as the
                # sequence length might have changed from version to version
                    try:
                        clip_start_frame = loader.GetAttrs("TOOLIT_Clip_StartFrame").get(1)
                        clip_length = loader.GetAttrs("TOOLIT_Clip_Length").get(1)
                        clip_end_frame = clip_start_frame + clip_length - 1
                        clip_trim_in = loader.GetAttrs("TOOLIT_Clip_TrimIn").get(1)
                        clip_trim_out = loader.GetAttrs("TOOLIT_Clip_TrimOut").get(1)
                        logger.info(f"Got values from loader '{loader.Name}'")
                    except Exception as e:
                        logger.error(
                            (
                                "Failed to get globalIn, globalOut, trimIn, trimOut "
                                "from loader {}: {}, full traceback:\n{}"
                            ).format(loader.Name, e, traceback.format_exc())
                        )

                # these values are specific to the loader, so there's no other way
                # to get them
                clip_extend_first = loader.GetAttrs("TOOLIT_Clip_ExtendFirst").get(1)
                clip_extend_last = loader.GetAttrs("TOOLIT_Clip_ExtendLast").get(1)

                # search for a printf token %04d, %05d, etc and replace it with the
                # first sequence frame value
                if fileseq_obj:
                    new_path = list(fileseq_obj)[0]
                else:
                    new_path = re.sub(r"%(\d{2})d", str(clip_start_frame), new_path)

                new_node_name = self.resolve_node_name(new_path)

                load_data = {
                    "TOOLS_Name": new_node_name,
                    "TOOLB_NameSet": True,
                    }

                logger.info(f"new_node_name: {new_node_name}")
                logger.info(f"new_path: {new_path}")
                logger.info(f"clip_start_frame: {clip_start_frame}")
                logger.info(f"clip_end_frame: {clip_end_frame}")
                logger.info(f"clip_length: {clip_length}")
                logger.info(f"clip_trim_in: {clip_trim_in}")
                logger.info(f"clip_trim_out: {clip_trim_out}")
                logger.info(f"clip_extend_first: {clip_extend_first}")
                logger.info(f"clip_extend_last: {clip_extend_last}")
                logger.info(f"load_data:\n{pf(load_data)}")

                try:
                    logger.info(f"Setting new clip path: {new_path}")
                    loader.Clip[comp.CurrentTime] = new_path

                    # ------------------------------------------------------------------
                    logger.info(
                        (
                            f"Setting new clip trim in and out: "
                            f"{clip_trim_in}, {clip_trim_out}"
                        )
                    )
                    loader.ClipTimeStart[comp.CurrentTime] = clip_trim_in
                    loader.ClipTimeEnd[comp.CurrentTime] = clip_trim_out
                    logger.info(
                        "Clip start from loader after set: {}".format(
                            loader.GetAttrs("TOOLIT_Clip_TrimIn").get(1)
                        )
                    )
                    logger.info(
                        "Clip end from loader after set: {}".format(
                            loader.GetAttrs("TOOLIT_Clip_TrimOut").get(1)
                        )
                    )

                    # ------------------------------------------------------------------
                    logger.info(
                        (
                            f"Setting new clip global in and out: "
                            f"{clip_start_frame}, {clip_end_frame}"
                        )
                    )
                    loader.GlobalIn[comp.CurrentTime] = clip_start_frame
                    loader.GlobalOut[comp.CurrentTime] = clip_end_frame
                    logger.info(
                        "clip global in from loader after set: {}".format(
                            loader.GetAttrs("TOOLNT_Clip_Start").get(1)
                        )
                    )
                    logger.info(
                        "clip global out from loader after set: {}".format(
                            loader.GetAttrs("TOOLNT_Clip_End").get(1)
                        )
                    )

                    # ------------------------------------------------------------------
                    logger.info(
                        (
                            f"Setting new clip extend (hold) first and last frames: "
                            f"{clip_extend_first}, {clip_extend_last}"
                        )
                    )
                    loader.SetInput("HoldFirstFrame", clip_extend_first)
                    loader.SetInput("HoldLastFrame", clip_extend_last)

                    # ------------------------------------------------------------------
                    logger.info(f"Setting new clip extra attributes: {load_data}")
                    loader.SetAttrs(load_data)

                    # check if we have a proper sg_metadata dict with the publuish info
                    # so we can update the loader node sg_metadata
                    if sg_metadata:
                        loader.SetData("sg_metadata", sg_metadata)
                except Exception as e:
                    msg = (
                        "Couldn't update node {} to latest version: {}, "
                        "full traceback:\n{}"
                    ).format(node, e, traceback.format_exc())
                    logger.error(msg)
                else:
                    logger.info("Successfully updated item {}".format(node))
                finally:
                    while comp.GetAttrs()["COMPB_Locked"]:
                        comp.Unlock()

    def fix_path(self, path):
        """Replace all backward slashes with forward slashes."""

        path = path.replace("\\\\", "/")
        path = path.replace("\\", "/")

        return path

    def get_item_paths_list(self, items):
        engine = self.parent.engine
        logger = engine.logger

        item_paths = [item.get("path") for item in items]
        logger.info(f"Found item paths:\n{pf(item_paths)}")

        # get all publishes to be able to update the loader sg_metadata after updating
        # the file paths in the selected loaders
        try:
            fields = ["version_number", "code", "name", "id", "entity", "path"]
            sg_publishes = sgtk.util.find_publish(
                engine.sgtk, item_paths, fields=fields
            )
            logger.info(f"Found sg_publishes:\n{pf(sg_publishes)}")
            return sg_publishes
        except Exception as e:
            logger.error(
                "Failed to get sg_publishes: {}, full traceback:\n{}".format(
                    e, traceback.format_exc()
                )
            )
            return {}

    def resolve_publish_name(self, path):
        name_pattern = re.compile(
            r"(?P<name>.+)"
            r"(?P<version>_[vV]\d{3})"
            r"(?P<extra>.+)"
        )
        basename = os.path.basename(path)
        basename_no_ext, extension = os.path.splitext(basename)
        match = name_pattern.match(basename_no_ext)
        if not match:
            return basename

        name = match.group("name")
        return f"{name}{extension}"

    def resolve_node_name(self, path):
        name_pattern = re.compile(
            r"(?P<name>.+)"
            r"(?P<version>_[vV]\d{3})"
            r"(?P<extra>.+)"
        )
        basename = os.path.basename(path)
        basename_no_ext, extension = os.path.splitext(basename)
        match = name_pattern.match(basename_no_ext)
        if not match:
            return basename_no_ext.split(".")[0]

        name = match.group("name")
        version = match.group("version")
        return f"{name}{version}"

    def sort_publishes_by_name(self, sg_publishes):
        sg_publishes_by_name = {}

        if sg_publishes:
            for path, value in sg_publishes.items():
                name = self.resolve_publish_name(path)
                sg_publishes_by_name[name] = value

        return sg_publishes_by_name

    def get_sg_metadata_dict(self, publish_dict):
        sg_metadata = {}

        meta_keys = ["version_number", "code", "name", "id", "entity"]
        if publish_dict:
            for k, val in publish_dict.items():
                if k in meta_keys:
                    sg_metadata[k] = val

        return sg_metadata
