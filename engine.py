# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""A Fusion engine for Tank.
https://en.wikipedia.org/wiki/Fusion_(software)
"""

import os
import sys
import time
import pprint
import inspect
import logging
import traceback

from functools import wraps

import tank
from tank.log import LogManager
from tank.platform import Engine
from tank.platform.constants import SHOTGUN_ENGINE_NAME

import BlackmagicFusion as bmd
fusion = bmd.scriptapp("Fusion")

__author__ = "Diego Garcia Huerta"
__email__ = "diegogh2000@gmail.com"


pp = pprint.pprint
pf = pprint.pformat

# env variable that control if to show the compatibility warning dialog
# when Fusion software version is above the tested one.
SHOW_COMP_DLG = "SGTK_COMPATIBILITY_DIALOG_SHOWN"


def show_error(msg):
    t = time.asctime(time.localtime())
    print("%s - Shotgrid Error | Fusion engine | %s " % (t, msg))


def show_warning(msg):
    t = time.asctime(time.localtime())
    print("%s - Shotgrid Error | Fusion engine | %s " % (t, msg))


def show_info(msg):
    t = time.asctime(time.localtime())
    print("%s - Shotgrid Error | Fusion engine | %s " % (t, msg))


def display_error(msg):
    t = time.asctime(time.localtime())
    print("%s - Shotgrid Error | Fusion engine | %s " % (t, msg))


def display_warning(msg):
    t = time.asctime(time.localtime())
    print("%s - Shotgrid Warning | Fusion engine | %s " % (t, msg))


def display_info(msg):
    t = time.asctime(time.localtime())
    print("%s - Shotgrid Info | Fusion engine | %s " % (t, msg))


def display_debug(msg):
    if os.environ.get("TK_DEBUG") == "1":
        t = time.asctime(time.localtime())
        print("%s - Shotgrid Debug | Fusion engine | %s " % (t, msg))



class FusionEngine(Engine):
    """
    Toolkit engine for Fusion.
    """

    def __get_platform_resource_path(self, filename):
        """
        Returns the full path to the given platform resource file or folder.
        Resources reside in the core/platform/qt folder.
        :return: full path
        """
        tank_platform_folder = os.path.abspath(inspect.getfile(tank.platform))
        return os.path.join(tank_platform_folder, "qt", filename)

    def __toggle_debug_logging(self):
        """
        Toggles global debug logging on and off in the log manager.
        This will affect all logging across all of toolkit.
        """
        # flip debug logging
        LogManager().global_debug = not LogManager().global_debug

    def __open_log_folder(self):
        """
        Opens the file system folder where log files are being stored.
        """
        self.log_info("Log folder is located in '%s'" %
                      LogManager().log_folder)

        if self.has_ui:
            # only import QT if we have a UI
            from sgtk.platform.qt import QtGui, QtCore
            url = QtCore.QUrl.fromLocalFile(
                LogManager().log_folder
            )
            status = QtGui.QDesktopServices.openUrl(url)
            if not status:
                self._engine.log_error("Failed to open folder!")

    def __register_open_log_folder_command(self):
        """
        # add a 'open log folder' command to the engine's context menu
        # note: we make an exception for the shotgun engine which is a
        # special case.
        """
        if self.name != SHOTGUN_ENGINE_NAME:
            icon_path = self.__get_platform_resource_path("folder_256.png")

            self.register_command(
                "Open Log Folder",
                self.__open_log_folder,
                {
                    "short_name": "open_log_folder",
                    "icon": icon_path,
                    "description": ("Opens the folder where log files are "
                                    "being stored."),
                    "type": "context_menu"
                }
            )

    def __register_reload_command(self):
        """
        Registers a "Reload and Restart" command with the engine if any
        running apps are registered via a dev descriptor.
        """
        from sgtk.platform import restart
        self.register_command(
            "Reload and Restart",
            restart,
            {"short_name": "restart",
             "icon": self.__get_platform_resource_path("reload_256.png"),
             "type": "context_menu"}
        )

    @property
    def context_change_allowed(self):
        """
        Whether the engine allows a context change without the need for a restart.
        """
        return True

    @property
    def host_info(self):
        """
        :returns: A dictionary with information about the application hosting this engine.

        The returned dictionary is of the following form on success:

            {
                "name": "Fusion",
                "version": "9",
            }

        The returned dictionary is of following form on an error preventing
        the version identification.

            {
                "name": "Fusion",
                "version: "unknown"
            }
        """

        host_info = {"name": "Fusion", "version": "unknown"}
        try:
            fusion_ver = fusion.Version
            host_info["version"] = fusion_ver
        except:
            # Fallback to 'Fusion' initialized above
            pass
        return host_info

    def _install_cacert_file(self):
        """
        Unfortunately, it seems that the SSL certificate does not work
        with the Fusion urlib2 library so we need to install it from
        the shotgun_apiv3, otherwise, any upload/download operations
        to shotgun will fail, ie. retrieving/uploading thumbnails.
        """

        self.ssl_cert_file = os.environ.get("SSL_CERT_FILE")

        try:
            import inspect
            import tank_vendor.shotgun_api3.lib.httplib2 as sapi3_httplib2
            httplib2_file = inspect.getfile(sapi3_httplib2)
            httplib2_dir = os.path.dirname(httplib2_file)
            cacerts_file = os.path.join(httplib2_dir, "cacerts.txt")
            if os.path.exists(cacerts_file):
                os.environ["SSL_CERT_FILE"] = cacerts_file

        except Exception:
            traceback.print_exc()
            self.logger.warning("Could not install Shotgrid cacert.txt"
                                " certificate due to the following exception:"
                                " ")

    def _restore_cacert_file(self):
        if self.ssl_cert_file is None:
            del os.environ["SSL_CERT_FILE"]
        # else:
        #     os.environ["SSL_CERT_FILE"] = ssl_cert_file

    def pre_app_init(self):
        """
        Runs after the engine is set up but before any apps have been
        initialized.
        """
        # unicode characters returned by the shotgun api need to be converted
        # to display correctly in all of the app windows
        from tank.platform.qt import QtCore

        # tell QT to interpret C strings as utf-8
        utf8 = QtCore.QTextCodec.codecForName("utf-8")
        QtCore.QTextCodec.setCodecForCStrings(utf8)
        self.logger.debug("set utf-8 codec for widget text")

        self.logger.debug("Installing certificate file from shotgun_api3")
        self._install_cacert_file()

        # moved from deprecated method init_engine -------------------------------------
        self.logger.debug("%s: Initializing...", self)

        # check that we are running an ok version of fusion
        current_os = sys.platform
        if current_os not in ["mac", "win32", "linux64"]:
            raise tank.TankError("The current platform is not supported!"
                                 " Supported platforms "
                                 "are Mac, Linux 64 and Windows 64.")

        fusion_build_version = str(fusion.Version)
        fusion_ver = float(".".join(fusion_build_version.split(".")[:2]))

        if fusion_ver < 9.0:
            msg = ("Shotgrid integration is not compatible with Fusion versions"
                   " older than 9")
            raise tank.TankError(msg)

        if fusion_ver > 9.0:
            # show a warning that this version of Fusion isn't yet fully tested
            # with Shotgrid:
            msg = ("The Shotgrid Pipeline Toolkit has not yet been fully "
                   "tested with Fusion %s.  "
                   "You can continue to use Toolkit but you may experience "
                   "bugs or instability."
                   "\n\n"
                   % (fusion_ver))

            # determine if we should show the compatibility warning dialog:
            show_warning_dlg = self.has_ui and SHOW_COMP_DLG not in os.environ

            if show_warning_dlg:
                # make sure we only show it once per session
                os.environ[SHOW_COMP_DLG] = "1"

                # split off the major version number - accomodate complex
                # version strings and decimals:
                major_version_number_str = fusion_build_version.split(".")[0]
                if (major_version_number_str and
                        major_version_number_str.isdigit()):
                    # check against the compatibility_dialog_min_version
                    # setting
                    min_ver = self.get_setting(
                        "compatibility_dialog_min_version")
                    if int(major_version_number_str) < min_ver:
                        show_warning_dlg = False

            if show_warning_dlg:
                # Note, title is padded to try to ensure dialog isn't insanely
                # narrow!
                show_info(msg)

            # always log the warning to the script editor:
            self.logger.warning(msg)

            # In the case of Windows, we have the possility of locking up if
            # we allow the PySide shim to import QtWebEngineWidgets.
            # We can stop that happening here by setting the following
            # environment variable.

            if current_os.startswith("win"):
                self.logger.debug(
                    "Fusion on Windows can deadlock if QtWebEngineWidgets "
                    "is imported. Setting "
                    "SHOTGUN_SKIP_QTWEBENGINEWIDGETS_IMPORT=1..."
                )
                os.environ["SHOTGUN_SKIP_QTWEBENGINEWIDGETS_IMPORT"] = "1"

        # add qt paths and dlls
        self._init_pyside()

        # default menu name is Shotgun but this can be overriden
        # in the configuration to be Sgtk in case of conflicts
        self._menu_name = "Shotgrid"
        if self.get_setting("use_sgtk_as_menu_name", False):
            self._menu_name = "Sgtk"

    @staticmethod
    def __recreate_shotgrid_menu():
        """
        Recreate the Shotgun menu in the current Fusion session.

        This method is useful in case the menu has been destroyed
        (for example if the user has manually deleted the menu in the
        Fusion UI).

        No arguments are required and no return value is expected.

        Note: if the sgtk module is not available, this method will
        not do anything and will not raise an error.

        Used in the Shotgrid menu entry in the Fusion UI.
        """
        if "sgtk" not in sys.modules:
            try:
                import sgtk
            except ImportError as e:
                display_error(f"Could not import sgtk: {e}")
                display_error(traceback.format_exc())
                return

        engine = sgtk.platform.current_engine()
        return engine.create_shotgrid_menu()

    def create_shotgrid_menu(self, disabled=False):
        """
        Creates the main shotgun menu in fusion.
        Note that this only creates the menu, not the child actions
        :return: bool
        """

        # only create the shotgun menu if not in batch mode and menu doesn't
        # already exist
        if self.has_ui:
            # create our menu handler
            tk_fusion = self.import_module("tk_fusion")

            self.menu_generator = tk_fusion.ShotgunMenu(self, self.icon_256)
            self.menu_generator.show()

            return True
        return False

    def _initialise_qapplication(self):
        """
        Ensure the QApplication is initialized
        """
        from sgtk.platform.qt import QtGui

        self._qt_app = QtGui.QApplication.instance()
        if self._qt_app is None:
            self.log_debug("Initialising main QApplication...")
            self._qt_app = QtGui.QApplication(sys.argv)
            self._qt_app.setWindowIcon(QtGui.QIcon(self.icon_256))
            self._qt_app.setQuitOnLastWindowClosed(True)

            # set up the dark style
            self._initialize_dark_look_and_feel()
            self._qt_app.aboutToQuit.connect(self._qt_app.deleteLater)

        # _qt_app.exec_()
        # pyqt_fusion.exec_(_qt_app)

    def post_app_init(self):
        """
        Called when all apps have initialized
        """
        self._initialise_qapplication()

        # for some readon this engine command get's lost so we add it back
        self.__register_reload_command()
        # Run a series of app instance commands at startup.
        self._run_app_instance_commands()

        # create the floating menu
        self.create_shotgrid_menu()

        # self._qt_app.exec_()

    def post_context_change(self, old_context, new_context):
        """
        Runs after a context change. The Fusion event watching will be stopped
        and new callbacks registered containing the new context information.

        :param old_context: The context being changed away from.
        :param new_context: The new context being changed to.
        """

        # restore the open log folder, it get's removed whenever the first time
        # a context is changed
        self.__register_open_log_folder_command()
        self.__register_reload_command()

        if self.get_setting("automatic_context_switch", True):
            # TODO check how to add instance in fusion
            if 'shotgun' in dir(fusion):
                fusion.shotgun._engine_instance = self.instance_name
                fusion.shotgun._menu_name = self._menu_name
                fusion.shotgun._new_context = new_context

            self.logger.debug(
                "Registered new open and save callbacks before "
                "changing context."
            )

            # finally create the menu with the new context if needed
            if old_context != new_context:
                self.create_shotgrid_menu()

    def _run_app_instance_commands(self):
        """
        Runs the series of app instance commands listed in the
        'run_at_startup' setting of the environment configuration yaml file.
        """

        # Build a dictionary mapping app instance names to dictionaries of
        # commands they registered with the engine.
        app_instance_commands = {}
        for cmd_name, value in self.commands.items():
            app_instance = value["properties"].get("app")
            if app_instance:
                # Add entry 'command name: command function' to the command
                # dictionary of this app instance.
                cmd_dict = app_instance_commands.setdefault(
                    app_instance.instance_name, {})
                cmd_dict[cmd_name] = value["callback"]

        # Run the series of app instance commands listed in the
        # 'run_at_startup' setting.
        for app_setting_dict in self.get_setting("run_at_startup", []):
            app_instance_name = app_setting_dict["app_instance"]

            # Menu name of the command to run or '' to run all commands of the
            # given app instance.
            setting_cmd_name = app_setting_dict["name"]

            # Retrieve the command dictionary of the given app instance.
            cmd_dict = app_instance_commands.get(app_instance_name)

            if cmd_dict is None:
                self.logger.warning(
                    "%s configuration setting 'run_at_startup' requests app"
                    " '%s' that is not installed.",
                    self.name, app_instance_name)
            else:
                if not setting_cmd_name:
                    # Run all commands of the given app instance.
                    for cmd_name, command_function in cmd_dict.items():
                        msg = ("%s startup running app '%s' command '%s'.",
                               self.name, app_instance_name, cmd_name)
                        self.logger.debug(msg)

                        command_function()
                else:
                    # Run the command whose name is listed in the
                    # 'run_at_startup' setting.
                    command_function = cmd_dict.get(setting_cmd_name)
                    if command_function:
                        msg = ("%s startup running app '%s' command '%s'.",
                               self.name, app_instance_name, setting_cmd_name)
                        self.logger.debug(msg)

                        command_function()
                    else:
                        known_commands = ', '.join(
                            "'%s'" % name for name in cmd_dict)
                        self.logger.warning(
                            "%s configuration setting 'run_at_startup' "
                            "requests app '%s' unknown command '%s'. "
                            "Known commands: %s",
                            self.name, app_instance_name,
                            setting_cmd_name, known_commands)

    def destroy_engine(self):
        """
        Remove the callback scene events.
        TODO: restore and preserve the existing ones.
        """
        self.logger.debug("%s: Destroying...", self)

        try:
            # self.close_windows()
            self.menu_generator.deleteLater()
        except Exception as e:
            self.logger.error(
                f"Error closing menu: {e}, full traceback:\n{traceback.format_exc()}",
            )

        # if self.get_setting("automatic_context_switch", True):
        #     fusion.setOnProjectCreatedCallback("")
        #     fusion.setOnProjectLoadedCallback("")

        # fineally restore the cacert certificate we replaced if there was one
        # in the first place
        # self._restore_cacert_file()

    def _init_pyside(self):
        """
        Handles the pyside init
        """

        # first see if pyside2 is present
        try:
            from PySide6 import QtGui
        except:
            # fine, we don't expect PySide6 to be present just yet
            self.logger.debug("PySide6 not detected - trying for PySide now...")
        else:
            # looks like pyside2 is already working! No need to do anything
            self.logger.debug(
                "PySide6 detected - the existing version will be used."
            )
            return

        # then see if pyside2 is present
        try:
            from PySide2 import QtGui
        except:
            # must be that a PySide2 version is not installed,
            self.logger.debug(
                "PySide2 not detected - it will be added to the setup now..."
            )
        else:
            # looks like pyside is already working! No need to do anything
            self.logger.debug(
                "PySide2 detected - the existing version will be used."
            )
            return

        current_os = sys.platform.lower()
        if current_os == "darwin":
            desktop_path = os.environ.get("SHOTGUN_DESKTOP_INSTALL_PATH",
                                          "/Applications/Shotgun.app")
            sys.path.append(os.path.join(desktop_path, "Contents", "Resources",
                                         "Python", "lib", "python2.7",
                                         "site-packages"))

        elif current_os == "win32":
            desktop_path = os.environ.get("SHOTGUN_DESKTOP_INSTALL_PATH",
                                          "C:/Program Files/Shotgun")
            sys.path.append(os.path.join(desktop_path,
                                         "Python", "Lib", "site-packages"))

        elif current_os == "linux2":
            desktop_path = os.environ.get("SHOTGUN_DESKTOP_INSTALL_PATH",
                                          "/opt/Shotgun/Shotgun")
            sys.path.append(os.path.join(desktop_path,
                                         "Python", "Lib", "site-packages"))


        else:
            self.logger.error("Unknown platform - cannot initialize PySide!")

        # now try to import it
        try:
            from PySide6 import QtGui
        except Exception as e:
            self.logger.error(
                "PySide6 could not be imported! Apps using pyside will not "
                "operate correctly! Error reported: {}, full traceback:\n {}".format(
                    e, traceback.format_exc()
                )
            )
        try:
            from PySide2 import QtGui
        except Exception as e:
            self.logger.error(
                "PySide2 could not be imported! Apps using pyside will not "
                "operate correctly! Error reported: {}, full traceback:\n {}".format(
                    e, traceback.format_exc()
                )
            )

    def _get_dialog_parent(self):
        """
        Get the QWidget parent for all dialogs created through
        show_dialog & show_modal.
        """

        # Unfornately there is no easy way to retrieve the QMainWindow from
        # Fusion. Following widgets ascendants return QWidget types which
        # cannot be guaranteed to be of QMainWindow class type. Tested but
        # did not work proeprly.

        return None

    @property
    def has_ui(self):
        """
        Detect and return if fusion is running in batch mode
        """
        return True

    def _emit_log_message(self, handler, record):
        """
        Called by the engine to log messages in Fusion script editor.
        All log messages from the toolkit logging namespace will be passed to
        this method.

        :param handler: Log handler that this message was dispatched from.
                        Its default format is "[levelname basename] message".
        :type handler: :class:`~python.logging.LogHandler`
        :param record: Standard python logging record.
        :type record: :class:`~python.logging.LogRecord`
        """
        # Give a standard format to the message:
        #     Shotgrid <basename>: <message>
        # where "basename" is the leaf part of the logging record name,
        # for example "tk-multi-shotgunpanel" or "qt_importer".
        if record.levelno < logging.INFO:
            formatter = logging.Formatter(
                "Debug: Shotgrid %(basename)s: %(message)s")
        else:
            formatter = logging.Formatter("Shotgrid %(basename)s: %(message)s")

        msg = formatter.format(record)

        # Select Fusion display function to use according to the logging
        # record level.
        if record.levelno >= logging.ERROR:
            fct = display_error
        elif record.levelno >= logging.WARNING:
            fct = display_warning
        elif record.levelno >= logging.INFO:
            fct = display_info
        else:
            fct = display_debug

        # Display the message in Fusion script editor in a thread safe manner.
        self.async_execute_in_main_thread(fct, msg)

    def close_windows(self):
        """
        Closes the various windows (dialogs, panels, etc.) opened by the
        engine.
        """

        # Make a copy of the list of sgtk dialogs that have been created by the
        # engine and are still opened since the original list will be updated
        # when each dialog is closed.
        opened_dialog_list = self.created_qt_dialogs[:]

        # Loop through the list of opened sgtk dialogs.
        for dialog in opened_dialog_list:
            dialog_window_title = dialog.windowTitle()
            try:
                # Close the dialog and let its close callback remove it from
                # the original dialog list.
                self.logger.debug("Closing dialog %s.", dialog_window_title)
                dialog.close()
            except Exception as e:
                traceback.print_exc()
                self.logger.error(
                    "Cannot close dialog {}: {}, full traceback:\n{}".format(
                        dialog_window_title, e, traceback.format_exc()
                    )
                )

    # def launch_floating_widget(self):
    #     if not hasattr(self, '_floating_widget'):
    #         self._floating_widget = ShotgunMenu(self)  # assuming ShotgunMenu is the class for the floating QWidget
    #     self._floating_widget.show()

    # def create_menu(self):
    #     menu = fusion.Menu("Shotgrid Toolkit")
    #     action = menu.AddAction("Launch Floating Widget", self.launch_floating_widget)
    #     return menu

    ####################################################################################
    # DO NOT DELETE: Method used by the publisher to update the version of the saver
    # nodes
    ####################################################################################
    def __update_nodes_version(self, new_path=None):
        """
            Update all the saver nodes in the comp.
            Only if the path correspond to a template.
        """
        self.logger.info("Updating saver nodes version...".ljust(80, "-"))
        comp          = fusion.GetCurrentComp()
        work_path     = comp.GetAttrs()['COMPS_FileName']
        if not new_path:
            work_path = new_path
        work_template     = self.sgtk.template_from_path(work_path)
        if not work_template:
            self.logger.error(
                f"Couldn't get a fusion work template from work path: {work_path}"
            )
            return
        work_fields   = work_template.get_fields(work_path)

        while not comp.GetAttrs()["COMPB_Locked"]:
            comp.Lock()

        # by using False as first argument, we are collecting all of the saver nodes,
        # not just the selected ones
        dict_of_tools = comp.GetToolList(False, "Saver")
        self.logger.info(f"dict_of_tools:\n{(pf(dict_of_tools))}")

        # Ensure the collected saver nodes have the newer metadata key
        # "Shotgrid_Saver_Node" and not just the old one "Shotgun_Saver_Node"
        self.__update_saver_metadata(dict_of_tools)

        invalid_paths = {
            "empty": [],
            "no_matching_template": [],
            "no_version_token": [],
            "missing_keys": [],
        }

        for index, tool in dict_of_tools.items():
            self.logger.info(f"Working on saver: {tool.Name}".ljust(40, "-"))
            paths = list(tool.GetAttrs()['TOOLST_Clip_Name'].values())

            if paths:
                clip_path = paths[0]
            else:
                clip_path = None

            # If saver path is empty
            if clip_path in [None, "", " "]:
                self.logger.warning(
                    f"Saver '{tool.Name}' has an invalid path, skipping: {clip_path}"
                )

                try:
                    tool.SetAttrs({"TOOLB_PassThrough": True})
                    self.logger.info(f"Saver '{tool.Name}' has bneen disabled.")
                except Exception as e:
                    self.logger.exception(f"Failed to disable saver '{tool.Name}': {e}")

                invalid_paths["empty"].append({tool.Name: clip_path})
                continue

            is_sg_saver    = tool.GetData("Shotgrid_Saver_Node")
            fields           = None
            current_template = None
            new_render_path  = None

            # Validating metadata
            if is_sg_saver:
                template_name    = tool.GetData("Current_template")
                current_template = self.sgtk.templates[template_name]
            # If the user created the saver manually, we might be able to still get the
            # template from the node path, if it matches with one of the valid templates
            else:
                current_template = self.sgtk.template_from_path(clip_path)

            # Avoid savers out of the pipeline
            if not current_template:
                self.logger.warning(
                    (
                        f"Saver '{tool.Name}' has an invalid path that doesn't match "
                        f"any template, skipping: {clip_path}"
                    )
                )
                invalid_paths["no_matching_template"].append({tool.Name: clip_path})
                continue

            fields = current_template.get_fields(clip_path)

            # Checking if the template use a version token
            if not 'version' in fields.keys():
                self.logger.warning(
                    (
                        f"Saver '{tool.Name}' doesn't use a version token, skipping: "
                        f"{clip_path}\n"
                        f"Available fields for this path:\n{pf(fields)}"
                    )
                )
                invalid_paths["no_version_token"].append({tool.Name: clip_path})
                continue

            for tool_field in fields.keys():
                # Update the fields
                if tool_field in work_fields.keys():
                    fields[tool_field] = work_fields[tool_field]

            # Checking for missing keys
            missing_keys = current_template.missing_keys(fields)
            if missing_keys:
                self.logger.warning(
                    (
                        f"Saver '{tool.Name}' has missing keys, skipping: "
                        f"{clip_path}\n"
                        f"Missing keys:\n{pf(missing_keys)}"
                    )
                )
                invalid_paths["missing_keys"].append({tool.Name: clip_path})
                continue

            # Updating path from current saver
            new_render_path = current_template.apply_fields(fields)
            self.logger.info(
                f"Updating saver '{tool.Name}' path from {clip_path} to {new_render_path}"
            )
            tool.Clip = new_render_path

        comp.Save(work_path)

        while comp.GetAttrs()["COMPB_Locked"]:
            comp.Unlock()

        if any(invalid_paths.values()):
            self.logger.warning(
                f"The following savers couldn't be updated:\n{pf(invalid_paths)}"
            )
        self.logger.info('Nodes update complete')

    def __update_saver_metadata(self, all_savers={}):
        """
        Updates the saver nodes metadata to the new "Shotgrid_Saver_Node" key.

        This method is used to update the saver nodes metadata from the old
        "Shotgun_Saver_Node" key to the new "Shotgrid_Saver_Node" key. Old keys is kept
        for backwards compatibility.

        It iterates over all saver nodes in the composition, checks if the saver node
        has the old key, and if it does, updates it to the new key.
        """
        comp = fusion.GetCurrentComp()

        if not all_savers:
            all_savers = comp.GetToolList(False, "Saver")

        while not comp.GetAttrs()["COMPB_Locked"]:
            comp.Lock()

        for i, saver in all_savers.items():
            self.logger.info(f"Working on saver {i}: {saver.Name}".ljust(60, "."))
            is_sg_saver_old = saver.GetData("Shotgun_Saver_Node")
            is_sg_saver_new = saver.GetData("Shotgrid_Saver_Node")

            if is_sg_saver_old:
                if is_sg_saver_new is not None:
                    saver.SetData("Shotgrid_Saver_Node", is_sg_saver_old)
                    self.logger.info("Updated Shotgrid saver node.")
                else:
                    self.logger.info("Shotgrid saver node already updated.")
            else:
                self.logger.warning("Saver is not a fusion saver, skipping...")

        comp.Save()

        while comp.GetAttrs()["COMPB_Locked"]:
            comp.Unlock()
