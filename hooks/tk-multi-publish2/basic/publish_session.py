# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sgtk
from sgtk.util.filesystem import ensure_folder_exists

import BlackmagicFusion as bmd
fusion = bmd.scriptapp("Fusion")

HookBaseClass = sgtk.get_hook_baseclass()


class FusionSessionPublishPlugin(HookBaseClass):
    """
    Plugin for publishing an open fusion session.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this::

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_session.py"

    """

    # NOTE: The plugin icon and name are defined by the base file plugin.

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        loader_url = "https://support.shotgunsoftware.com/hc/en-us/articles/219033078"

        return """
        Publishes the file to Shotgun. A <b>Publish</b> entry will be
        created in Shotgun which will include a reference to the file's current
        path on disk. If a publish template is configured, a copy of the
        current session will be copied to the publish template path which
        will be the file that is published. Other users will be able to access
        the published file via the <b><a href='%s'>Loader</a></b> so long as
        they have access to the file's location on disk.

        If the session has not been saved, validation will fail and a button
        will be provided in the logging output to save the file.

        <h3>File versioning</h3>
        If the filename contains a version number, the process will bump the
        file to the next version after publishing.

        The <code>version</code> field of the resulting <b>Publish</b> in
        Shotgun will also reflect the version number identified in the filename.
        The basic worklfow recognizes the following version formats by default:

        <ul>
        <li><code>filename.v###.ext</code></li>
        <li><code>filename_v###.ext</code></li>
        <li><code>filename-v###.ext</code></li>
        </ul>

        After publishing, if a version number is detected in the work file, the
        work file will automatically be saved to the next incremental version
        number. For example, <code>filename.v001.ext</code> will be published
        and copied to <code>filename.v002.ext</code>

        If the next incremental version of the file already exists on disk, the
        validation step will produce a warning, and a button will be provided in
        the logging output which will allow saving the session to the next
        available version number prior to publishing.

        <br><br><i>NOTE: any amount of version number padding is supported. for
        non-template based workflows.</i>

        <h3>Overwriting an existing publish</h3>
        In non-template workflows, a file can be published multiple times,
        however only the most recent publish will be available to other users.
        Warnings will be provided during validation if there are previous
        publishes.
        """ % (loader_url,)

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

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

        # inherit the settings from the base publish plugin
        base_settings = super(FusionSessionPublishPlugin, self).settings or {}

        # settings specific to this class
        fusion_publish_settings = {
            "Publish Template": {
                "type": "template",
                "default": None,
                "description": "Template path for published work files. Should"
                               "correspond to a template defined in "
                               "templates.yml.",
            }
        }

        # update the base settings
        base_settings.update(fusion_publish_settings)

        return base_settings

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["fusion.*", "file.fusion"]
        """
        return ["fusion.session"]

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        # if a publish template is configured, disable context change. This
        # is a temporary measure until the publisher handles context switching
        # natively.
        if settings.get("Publish Template").value:
            item.context_change_allowed = False

        path = _session_path()

        if not path:
            # the session has not been saved before (no path determined).
            # provide a save button. the session will need to be saved before
            # validation will succeed.
            self.logger.warn(
                "The Fusion session has not been saved.",
                extra=_get_save_as_action()
            )

        self.logger.info(
            "Fusion '%s' plugin accepted the current Fusion session." %
            (self.name,)
        )
        return {
            "accepted": True,
            "checked": True
        }

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """

        publisher = self.parent
        path = _session_path()

        # ---- ensure the session has been saved

        if not path:
            # the session still requires saving. provide a save button.
            # validation fails.
            error_msg = "The Fusion session has not been saved."
            self.logger.error(
                error_msg,
                extra=_get_save_as_action()
            )
            raise Exception(error_msg)

        # ---- check the session against any attached work template

        # get the path in a normalized state. no trailing separator,
        # separators are appropriate for current os, no double separators,
        # etc.
        path = sgtk.util.ShotgunPath.normalize(path)

        # if the session item has a known work template, see if the path
        # matches. if not, warn the user and provide a way to save the file to
        # a different path
        work_template = item.properties.get("work_template")
        if work_template:
            if not work_template.validate(path):
                self.logger.warning(
                    "The current session does not match the configured work "
                    "file template.",
                    extra={
                        "action_button": {
                            "label": "Save File",
                            "tooltip": "Save the current Fusion session to a "
                                       "different file name",
                            # will launch wf2 if configured
                            "callback": _get_save_as_action()
                        }
                    }
                )
            else:
                self.logger.debug(
                    "Work template configured and matches session file."
                )
        else:
            self.logger.debug("No work template configured.")

        # ---- see if the version can be bumped post-publish

        # check to see if the next version of the work file already exists on
        # disk. if so, warn the user and provide the ability to jump to save
        # to that version now
        (next_version_path, version) = self._get_next_version_info(path, item)
        if next_version_path and os.path.exists(next_version_path):

            # determine the next available version_number. just keep asking for
            # the next one until we get one that doesn't exist.
            while os.path.exists(next_version_path):
                (next_version_path, version) = self._get_next_version_info(
                    next_version_path, item
                )

            error_msg = "The next version of this file already exists on disk."
            self.logger.error(
                error_msg,
                extra={
                    "action_button": {
                        "label": "Save to v%s" % (version,),
                        "tooltip": "Save to the next available version number, "
                                   "v%s" % (version,),
                        "callback": lambda: _save_session(next_version_path)
                    }
                }
            )
            raise Exception(error_msg)

        # ---- populate the necessary properties and call base class validation

        # populate the publish template on the item if found
        publish_template_setting = settings.get("Publish Template")
        publish_template = publisher.engine.get_template_by_name(
            publish_template_setting.value
        )
        if publish_template:
            item.properties["publish_template"] = publish_template

        # set the session path on the item for use by the base plugin validation
        # step. NOTE: this path could change prior to the publish phase.
        item.properties["path"] = path

        # run the base class validation
        return super(FusionSessionPublishPlugin, self).validate(settings, item)

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # get the path in a normalized state. no trailing separator, separators
        # are appropriate for current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(_session_path())

        # ensure the session is saved
        _save_session(path)

        # update the item with the saved session path
        item.properties["path"] = path

        # Unfortunately, it seems that the SSL certificate does not work
        # with the Fusion urlib2 library so we force it here
        ssl_cert_file = os.environ.get("SSL_CERT_FILE")

        try:
            import inspect
            import tank_vendor.shotgun_api3.lib.httplib2 as sapi3_httplib2
            httplib2_file = inspect.getfile(sapi3_httplib2)
            httplib2_dir = os.path.dirname(httplib2_file)
            cacerts_file = os.path.join(httplib2_dir, "cacerts.txt")
            os.environ["SSL_CERT_FILE"] = cacerts_file
        except ImportError as e:
            self.parent.engine.logger.exception(
                f"Failed to set SSL_CERT_FILE env var: {e}"
            )

        # let the base class register the publish
        super(FusionSessionPublishPlugin, self).publish(settings, item)

        if ssl_cert_file is None:
            del os.environ["SSL_CERT_FILE"]
        else:
            os.environ["SSL_CERT_FILE"] = ssl_cert_file

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once all the publish
        tasks have completed, and can for example be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        # do the base class finalization
        super(FusionSessionPublishPlugin, self).finalize(settings, item)

        # bump the session file to the next version
        self._save_to_next_version(item.properties["path"], item, _save_session)


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


def _save_session(path):
    """
    Save the current session to the supplied path.
    """

    # Ensure that the folder is created when saving
    folder = os.path.dirname(path)
    ensure_folder_exists(folder)

    comp = fusion.GetCurrentComp()
    comp.Save(path)


# TODO: method duplicated in all the fusion hooks
def _get_save_as_action():
    """
    Simple helper for returning a log action dict for saving the session
    """

    engine = sgtk.platform.current_engine()

    callback = _save_as

    # if workfiles2 is configured, use that for file save
    if "tk-multi-workfiles2" in engine.apps:
        app = engine.apps["tk-multi-workfiles2"]
        if hasattr(app, "show_file_save_dlg"):
            callback = app.show_file_save_dlg

    return {
        "action_button": {
            "label": "Save As...",
            "tooltip": "Save the current session",
            "callback": callback
        }
    }


def _save_as():
    comp = fusion.GetCurrentComp()
    path = comp.GetAttrs()['COMPS_FileName']

    # if isinstance(path, unicode):
    #     path = path.encode("utf-8")

    if path:
        comp.Save(path)
