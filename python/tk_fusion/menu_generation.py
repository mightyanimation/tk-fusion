import os
import re
import sys
import sgtk
import time
import pprint
import traceback
import subprocess

import BlackmagicFusion as bmd
from sgtk.platform.qt import QtGui, QtCore

pp = pprint.pprint
pf = pprint.pformat


class ShotgunMenu(QtGui.QWidget):
    """Simple Test"""

    def __init__(self, engine, icon_path):
        self.engine = engine
        self.icon_path = icon_path

        # Verify fusion
        self.verify_fusion()

        self.pyside2_bool = int(QtCore.__version__.split('.')[0]) > 4
        super(ShotgunMenu, self).__init__()
        #self.setGeometry(50, 50, 260, 100)
        self.setMinimumWidth(250)
        self.setWindowTitle("Shotgrid: Menu Panel")
        icon = QtGui.QIcon(self.icon_path)
        self.setWindowIcon(icon)

        # Global layout
        qvboxLayoutGlobal = QtGui.QVBoxLayout()
        qvboxLayoutGlobal.setContentsMargins(0, 0, 0, 6)
        qvboxLayoutGlobal.setSizeConstraint(QtGui.QLayout.SetFixedSize)
        self.setLayout(qvboxLayoutGlobal)

        # Global context menu
        self.context_button = QtGui.QPushButton(str(self.engine.context))
        self.context_button.setStyleSheet("background-color: #4A586E")
        self.context_button.setMinimumSize(QtCore.QSize(210, 20))
        self.context_menu = QtGui.QMenu(self)
        self.context_button.setMenu(self.context_menu)

        frame_01 = QtGui.QFrame(self)
        frame_01.setFrameShape(QtGui.QFrame.NoFrame)
        frame_01_qhboxLayout = QtGui.QHBoxLayout()
        frame_01_qhboxLayout.setContentsMargins(6, 6, 6, 0)
        frame_01.setLayout(frame_01_qhboxLayout)
        frame_01_qhboxLayout.addWidget(self.context_button)

        self.show_btn = QtGui.QPushButton('<')
        self.show_btn.setMaximumSize(QtCore.QSize(20, 20))
        self.show_btn.clicked.connect(self.show_options)
        frame_01_qhboxLayout.addWidget(self.show_btn)

        self.frame_02 = QtGui.QFrame(self)
        self.frame_02.setFrameShape(QtGui.QFrame.NoFrame)
        self.qvboxLayout = QtGui.QVBoxLayout()
        self.qvboxLayout.setContentsMargins(6, 0, 6, 0)
        self.frame_02.setLayout(self.qvboxLayout)

        line_01 = QtGui.QFrame()
        line_01.setFrameShape(QtGui.QFrame.HLine)
        line_01.setFrameShadow(QtGui.QFrame.Sunken)

        qvboxLayoutGlobal.addWidget(frame_01)
        qvboxLayoutGlobal.addWidget(line_01)
        qvboxLayoutGlobal.addWidget(self.frame_02)

        self.func_index = 0
        self.func_relations = {}

        # Menu always on top
        flags = QtCore.Qt.WindowFlags(QtCore.Qt.WindowStaysOnTopHint |
                QtCore.Qt.WindowTitleHint)
        self.setWindowFlags(flags)

        self.populateLayout()

    def get_command_info(self, command_name):
        """
        Receive the name of the command or app register in the engine,
        and return the description and the icon if they exists.

        Parameters:
            command_name (str): Register name in the engine commands/App.

        Returns:
            value 1: Icon file path if exists, else None.
            value 2: Description string if exists, else None.
        """
        icon_str = icon_path = description = None

        command_dict = self.engine.commands[command_name]
        command_properties = command_dict['properties']

        if 'icon' in command_properties: icon_str = 'icon'
        if 'icons' in command_properties: icon_str = 'icons'
        if 'description' in command_properties:
            description = command_properties['description']

        if icon_str:
            icon_data = command_properties[icon_str]
            if isinstance(icon_data, str): icon_path=icon_data
            else:
                i_key = list(icon_data.keys())[0]
                icon_path = icon_data[i_key]['png']
            # Special cases, for some reason, there is a string
            # in the path that does not exists....
            icon_path = icon_path.replace('__init__.pyc', '')

        return icon_path, description

    def show_options(self):
        """
        Show/hide engine app buttons

        Parameters:
            None
        Returns:
            None
        """
        # Change text
        if self.show_btn.text() == '>': self.show_btn.setText('<')
        else: self.show_btn.setText('>')

        # Change visibility
        self.frame_02.setVisible(not self.frame_02.isVisible())

    def connect_to_engine(self):
        triggered_element = self.sender().objectName()
        if triggered_element in self.engine.commands:
            self.engine.commands[triggered_element]['callback'].__call__()
        elif triggered_element == 'Unlock_comp':
            self.unlock_comp()

    def populateLayout(self):
        """
        Populate the shotgun menu options

        Parameters:
            None
        Returns:
            None
        """
        eng_dict = {}
        # Context options will be displayed under the context button
        context_engine_options =  [
            ['Jump to Shotgun', self._jump_to_sg],
            ['Jump to File System', self._jump_to_fs],
            'Ensure Tasks Folders', 2,
            'Jump to Screening Room in RV',
            'Jump to Screening Room Web Player', 'Work Area Info...', 2,
            'Reload and Restart', 'Open Log Folder', 'Toggle Debug Logging']

        for ctx_option in context_engine_options:
            if isinstance(ctx_option, list):
                # Creating menu button
                menu_action = QtGui.QAction(ctx_option[0], self)
                menu_action.triggered.connect(ctx_option[1])
                self.context_menu.addAction(menu_action)

            elif ctx_option in self.engine.commands:
                # Creating menu button
                menu_action = QtGui.QAction(ctx_option, self)
                menu_action.setObjectName(ctx_option)
                menu_action.triggered.connect(self.connect_to_engine)

                # Get app/command extra info
                icon_path, description_str = self.get_command_info(ctx_option)
                # Set icon
                if icon_path: menu_action.setIcon(QtGui.QIcon(icon_path))
                # Set tooltip
                if description_str: menu_action.setToolTip(description_str)

                self.context_menu.addAction(menu_action)

            elif isinstance(ctx_option, int):
                # Separators
                for x in range(ctx_option): self.context_menu.addSeparator()

        # Populating menu with engine fuctions
        counter = 0
        for cmd_name, cmd_data in self.engine.commands.items():
            eng_dict[id(cmd_data)] = cmd_data
            # Skip if the engine app/command  is already in the context menu
            if cmd_name in context_engine_options: continue

            # Create the button for the main menu
            if counter % 4 == 0 and counter != 0:
                line_sep = QtGui.QFrame()
                line_sep.setFrameShape(QtGui.QFrame.HLine)
                line_sep.setFrameShadow(QtGui.QFrame.Sunken)
                self.qvboxLayout.addWidget(line_sep)
            counter += 1
            app_button = QtGui.QPushButton('  {}'.format(cmd_name))
            app_button.setObjectName('{}'.format(cmd_name))

            # updating action
            app_button.clicked.connect(self.connect_to_engine)

            icon_path, description = self.get_command_info(cmd_name)
            # If the button has icon
            if icon_path: app_button.setIcon(QtGui.QIcon(icon_path))
            # If the button has description
            if description: app_button.setToolTip(description)
            self.qvboxLayout.addWidget(app_button)

        # Regular menu element
        line_02 = QtGui.QFrame()
        line_02.setFrameShape(QtGui.QFrame.HLine)
        line_02.setFrameShadow(QtGui.QFrame.Sunken)
        self.qvboxLayout.addWidget(line_02)

        unlock_comp_btn = QtGui.QPushButton('Unlock comp')
        unlock_comp_btn.setObjectName('Unlock_comp')
        unlock_comp_btn.clicked.connect(self.connect_to_engine)
        unlock_comp_btn.setToolTip('Option to unlock fusion when the viewer is freeze')
        self.qvboxLayout.addWidget(unlock_comp_btn)

    def _jump_to_sg(self):
        """
        Jump to shotgun, launch web browser
        """
        url = self.engine.context.shotgun_url
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def unlock_comp(self):
        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()
        was_locked_bool = False
        while comp.GetAttrs()['COMPB_Locked']:
            was_locked_bool = True
            comp.Unlock()

        if was_locked_bool:
            msg_ = 'Unlock complete'
        else:
            msg_ = 'Comp was not locked'

        msgBox = QtGui.QMessageBox()
        msgBox.setText(msg_)
        msgBox.exec_()

    def _jump_to_fs(self):
        """
        Jump from context to FS
        """
        # launch one window for each location on disk
        paths = self.engine.context.filesystem_locations
        for disk_location in paths:

            # get the setting
            system = sys.platform

            # run the app
            if system == "linux2":
                cmd = 'xdg-open "%s"' % disk_location
            elif system == "darwin":
                cmd = 'open "%s"' % disk_location
            elif system == "win32":
                cmd = 'cmd.exe /C start "Folder" "%s"' % disk_location
            else:
                raise Exception("Platform '%s' is not supported." % system)

            exit_code = os.system(cmd)
            if exit_code != 0:
                self.engine.logger.error("Failed to launch '%s'!", cmd)

    def verify_fusion(self):
        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()
        fusion_exe = fusion.GetAttrs()['FUSIONS_FileName']

        # Check if are not using FusionRenderNode
        if not fusion_exe.endswith("FusionRenderNode.exe"): return None

        # TODO: check how to load fusion.exe instead of FusionRenderNode.exe
        print('{0}\n{1}\{0}'.format(24 * '*', fusion_exe))
        subprocess_ = subprocess.Popen(['tasklist'], stdout=subprocess.PIPE)
        output, error = subprocess_.communicate()
        #print output
        target_process = "FusionRenderNode"
        pid = None
        for line in output.splitlines():
            if not 'FusionRenderNode' in str(line): continue
            for sub_ in str(line).split(' '):
                if sub_.isdigit():
                    pid = int(sub_)
                    break
            break

        # if we didn't find the FusionRenderNode process
        # This happen if other process kill the process first
        if pid is None: return None

        #Closing process
        try:
            os.kill(pid, 9)
            # logger.debug(' ...Closing FusionRenderNode...')
            print(' ...Closing FusionRenderNode...')
            time.sleep(1)
        except:
            time.sleep(1)

        fusion = bmd.scriptapp("Fusion") # Reload fusion
        comp = fusion.GetCurrentComp() # Reload comp
