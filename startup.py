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
import sys

import sgtk
from sgtk.util.filesystem  import copy_folder
from sgtk.platform import SoftwareLauncher, SoftwareVersion, LaunchInformation


class FusionLauncher(SoftwareLauncher):
    """
    Handles launching Fusion executables. Automatically starts up
    a tk-fusion engine with the current context in the new session
    of Fusion.
    """

    # Named regex strings to insert into the executable template paths when
    # matching against supplied versions and products. Similar to the glob
    # strings, these allow us to alter the regex matching for any of the
    # variable components of the path in one place
    COMPONENT_REGEX_LOOKUP = {
        "version": r"\d+",
    }

    # This dictionary defines a list of executable template strings for each
    # of the supported operating systems. The templates are used for both
    # globbing and regex matches by replacing the named format placeholders
    # with an appropriate glob or regex string.

    EXECUTABLE_TEMPLATES = {
        "darwin": [
            "/Applications/Blackmagic Design/Fusion-{version}/Fusion.app",
        ],
        "win32": [
            "C:/Program Files/Blackmagic Design/Fusion {version}/Fusion.exe",
        ],
        "linux2": [
            "/usr/Blackmagic Design/Fusion-{version}/Fusion",
        ]
    }

    @property
    def minimum_supported_version(self):
        """
        The minimum software version that is supported by the launcher.
        """
        return "9"

    def prepare_launch(self, exec_path, args, file_to_open=None):
        """
        Prepares an environment to launch Fusion in that will automatically
        load Toolkit and the tk-fusion engine when Fusion starts.

        :param str exec_path: Path to Fusion executable to launch.
        :param str args: Command line arguments as strings.
        :param str file_to_open: (optional) Full path name of a file to open on
                                            launch.
        :returns: :class:`LaunchInformation` instance
        """
        required_env = {}

        current_os = sys.platform.lower()

        if current_os == "darwin":
            python_path = os.environ.get("SHOTGUN_DESKTOP_INSTALL_PATH",
                                          "/Applications/Shotgun.app/Python")
            fusion_home = "/Library/Application Support/Blackmagic Design/Fusion"

        elif current_os == "win32":
            python_path = os.environ.get("SHOTGUN_DESKTOP_INSTALL_PATH",
                                          "C:/Program Files/Shotgun/Python")
            fusion_home = "C:/ProgramData/Blackmagic Design/Fusion"

        elif current_os == "linux":
            python_path = os.environ.get("SHOTGUN_DESKTOP_INSTALL_PATH",
                                          "/opt/Shotgun/Shotgun/Python")
            fusion_home = "/opt/BlackmagicDesign/Fusion"

        # Copy Fusion Startup modules to right folder
        copy_folder(os.path.join(self.disk_location, "startup"), fusion_home)

        sgtk.util.append_path_to_env_var(
             "FUSION_PYTHON27_HOME", python_path)

        # Prepare the launch environment with variables required by the
        # classic bootstrap approach.
        self.logger.debug(
            "Preparing Fusion Launch via Toolkit Classic methodology ...")
        required_env["SGTK_ENGINE"] = self.engine_name
        required_env["SGTK_CONTEXT"] = sgtk.context.serialize(self.context)

        if file_to_open:
            # Add the file name to open to the launch environment
            required_env["SGTK_FILE_TO_OPEN"] = file_to_open

        args = ""
        return LaunchInformation(exec_path, args, required_env)

    def _icon_from_engine(self):
        """
        Use the default engine icon as fusion does not supply
        an icon in their software directory structure.

        :returns: Full path to application icon as a string or None.
        """

        # the engine icon
        engine_icon = os.path.join(self.disk_location, "icon_256.png")
        return engine_icon

    def scan_software(self):
        """
        Scan the filesystem for Fusion executables.

        :return: A list of :class:`SoftwareVersion` objects.
        """
        self.logger.debug("Scanning for Fusion executables...")

        supported_sw_versions = []

        for sw_version in self._find_software():
            (supported, reason) = self._is_supported(sw_version)
            if supported:
                supported_sw_versions.append(sw_version)
            else:
                self.logger.debug(
                    "SoftwareVersion %s is not supported: %s" %
                    (sw_version, reason)
                )

        return supported_sw_versions

    def _find_software(self):
        """
        Find executables in the default install locations.
        """

        # all the executable templates for the current OS
        executable_templates = self.EXECUTABLE_TEMPLATES.get(sys.platform, [])

        # all the discovered executables
        sw_versions = []

        for executable_template in executable_templates:
            executable_template = os.path.expanduser(executable_template)
            executable_template = os.path.expandvars(executable_template)

            self.logger.debug("Processing template %s", executable_template)

            executable_matches = self._glob_and_match(
                executable_template, self.COMPONENT_REGEX_LOOKUP
            )

            # Extract all products from that executable.
            for (executable_path, key_dict) in executable_matches:

                # extract the matched keys form the key_dict (default to None
                # if not included)
                executable_version = key_dict.get("version")

                sw_versions.append(
                    SoftwareVersion(
                        executable_version,
                        "Fusion",
                        executable_path,
                        self._icon_from_engine()
                    )
                )

        self.logger.info(sw_versions)

        return sw_versions
