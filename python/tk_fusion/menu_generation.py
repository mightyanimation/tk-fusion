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
        self.saver_nodes = {}
        # Verify fusion
        self.verify_fusion()

        self.pyside2_bool = int(QtCore.__version__.split('.')[0]) > 4
        super(ShotgunMenu, self).__init__()
        #self.setGeometry(50, 50, 260, 100)
        self.setMinimumWidth(250)
        self.setWindowTitle("Shotgrid: Menu Panel")
        icon = QtGui.QIcon(self.icon_path)
        self.setWindowIcon(icon)

        #Global layout
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

        #self.qvboxLayout.addWidget(frame_01)
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
        elif triggered_element in self.saver_nodes:
            self.create_saver(triggered_element)
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
                self.context_menu.addSeparator()
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
                self.context_menu.addSeparator()

            elif isinstance(ctx_option, int):
                # Separators
                for x in range(ctx_option): self.context_menu.addSeparator()

        # Populating menu with engine fuctions
        for cmd_name, cmd_data in self.engine.commands.items():
            eng_dict[id(cmd_data)] = cmd_data
            # Skip if the engine app/command  is already in the context menu
            if cmd_name in context_engine_options: continue

            # Create the button for the main menu
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

        savers_menu = QtGui.QMenu(self)
        sg_saver = QtGui.QPushButton("Create Saver Nodes")
        sg_saver.setMenu(savers_menu)
        sg_saver.setStyleSheet("background-color: #810B44")

        for element in self.engine.get_setting('saver_nodes'):
            self.saver_nodes[element['name']] = element
            menu_action = QtGui.QAction(element['name'], self)
            menu_action.setObjectName(element['name'])
            menu_action.triggered.connect(self.connect_to_engine)
            savers_menu.addAction(menu_action)

        if self.saver_nodes:
            self.qvboxLayout.addWidget(sg_saver)

    def _jump_to_sg(self):
        """
        Jump to shotgun, launch web browser
        """
        url = self.engine.context.shotgun_url
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def create_saver(self, sg_saver_name):
        logger = self.engine.logger

        fusion        = bmd.scriptapp("Fusion")
        comp          = fusion.GetCurrentComp()
        path          = comp.GetAttrs()['COMPS_FileName']
        sg_saver_info = self.saver_nodes[sg_saver_name]

        work_template_name = sg_saver_info.get('work_template')
        if not work_template_name:
            # try to solve the work template from the current scene
            work_template = self.engine.sgtk.template_from_path(path)
            logger.info(f"template from sgtk: {work_template}")
        else:
            work_template = self.engine.sgtk.templates.get(work_template_name)
            logger.info(f"template from settings: {work_template}")

        if not work_template:
            msg_ = 'To create a saver node\nSave your comp first!'
            msgBox = QtGui.QMessageBox()
            msgBox.setText(msg_)
            msgBox.exec_()
            return

        logger.info(f"sg_saver_info:\n{pf(sg_saver_info)}")
        logger.info(f"path: {path}")
        logger.info(f"work_template: {work_template}")
        logger.info(f"work_template.name: {work_template.name}")

        fields = work_template.validate_and_get_fields(os.path.normpath(path))
        logger.info(f"work_template fields:\n{pf(fields)}")
        if not fields:
            logger.error("Failed to get work template fields")
            return
        work_version = fields.get('version')
        comp_format = comp.GetPrefs().get('Comp').get('FrameFormat')
        fields['height'] = int(comp_format.get('Height'))
        fields['width'] = int(comp_format.get('Width'))
        try:
            sg_shot = self.get_sg_shot_info(['sg_cut_in'])
            fields['SEQ'] = sg_shot['sg_cut_in']
        except:
            fields['SEQ'] = 1001

        # Applying aov fields!
        if 'aov_name' in sg_saver_info:
            fields['aov_name'] = sg_saver_info['aov_name']
        else:
            title, msg = 'Create AOV saver', 'Enter AOV name:'
            text, resp = QtGui.QInputDialog.getText(self, title, msg)
            if resp:
                fields['aov_name'] = text
            else:
                return

        render_template_name = sg_saver_info['render_template']
        render_template = self.engine.sgtk.templates[render_template_name]
        logger.info(f"fields before applying them to render_template:\n{pf(fields)}")

        # validate fields before applying them to render_template
        missing_fields = render_template.missing_keys(fields)
        if missing_fields:
            logger.error(f"Missing fields in render_template: {missing_fields}")
            return

        render_path = render_template.apply_fields(fields)

        while not comp.GetAttrs()['COMPB_Locked']:
            comp.Lock()

        x_pos, y_pos = self.get_good_position(comp)

        # get the first selected node. If more that one nodes are selected, only the
        # first one is used
        selected_node = None
        selected_nodes = comp.GetToolList(True)
        if selected_nodes:
            selected_node = selected_nodes.get(1)
            if selected_node:
                x_pos, y_pos = self.get_tool_pos(comp, selected_node)
                x_pos += 0.5
                y_pos += 3

        logger.info(f"found good position, x: {x_pos}, y: {y_pos}")
        saver = comp.AddTool("Saver", x_pos, y_pos)
        # saver      = comp.Saver({"Clip": render_path})
        saver.Clip = render_path
        saver_atts = {
            "TOOLS_Name": "sg_%{}".format(sg_saver_name),
            "format_id": sg_saver_info['format_id'],
            'format_settings': sg_saver_info['format_settings']
        }
        saver.SetAttrs(saver_atts)

        # try to connect the original selected node to the newly created saver node
        if selected_node:
            saver.Input.ConnectTo(selected_node.Output)

        # finally set the node color
        saver.TileColor = {
            "R": 0.920,
            "G": 0.430,
            "B": 0.0,
        }

        while comp.GetAttrs()['COMPB_Locked']:
            comp.Unlock()

        saver.SetData("Shotgun_Saver_Node", True)
        saver.SetData("Current_template", render_template.name)

    def get_sg_shot_info(self, shot_fields):
        engine = self.engine
        sg = engine.shotgun
        sg_proj = engine.context.project

        entity_name = engine.context.entity.get("name")
        shot_filter = [['project', 'is', sg_proj],
                       ['code', 'is', entity_name]]
        # shot_fields = ['sg_cut_in', 'sg_cut_out']
        sg_shot = sg.find_one('Shot', shot_filter, shot_fields)
        return sg_shot

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

    # def __create_sg_saver(self, ext_type):
    #     fusion = bmd.scriptapp("Fusion")
    #     comp = fusion.GetCurrentComp()
    #     path = comp.GetAttrs()['COMPS_FileName']

    #     task_type = self.engine.context.entity.get("type")
    #     work_template = self.engine.sgtk.template_from_path(path)
    #     fields = work_template.get_fields(path)

    #     comp_format = comp.GetPrefs().get('Comp').get('FrameFormat')
    #     fields['height'] = int(comp_format.get('Height'))
    #     fields['width'] = int(comp_format.get('Width'))
    #     fields['output'] = 'output'

    #     text, ok = QtGui.QInputDialog.getText(self, 'Input Name Dialog', 'Enter output name:')

    #     if text and ok:
    #         fields['output'] = text

    #     review_template = self.engine.get_template_by_name("fusion_%s_render_mono_%s" % (task_type.lower(), ext_type))
    #     output = review_template.apply_fields(fields)
    #     output = re.sub(r'%(\d+)d', '', output)

    #     while not comp.GetAttrs()['COMPB_Locked']:
    #         comp.Lock()
    #     saver = comp.Saver({"Clip": output})
    #     saver.CreateDir = 0
    #     saver.SetAttrs({"TOOLS_Name": "shotgun_%s" % ext_type})
    #     while comp.GetAttrs()['COMPB_Locked']:
    #         comp.Unlock()


    # def __update_sg_saver(self):
    #     fusion = bmd.scriptapp("Fusion")
    #     comp = fusion.GetCurrentComp()
    #     path = comp.GetAttrs()['COMPS_FileName']

    #     work_template = self.engine.sgtk.template_from_path(path)
    #     work_version = work_template.get_fields(path).get('version')

    #     savers = comp.GetToolList(False, "Saver").values()

    #     saver_names = []
    #     while not comp.GetAttrs()['COMPB_Locked']:
    #         comp.Lock()
    #     for saver in savers:
    #         path = saver.GetAttrs()['TOOLST_Clip_Name'].values()[0]
    #         template = self.engine.sgtk.template_from_path(path)
    #         if template:
    #             fields = template.get_fields(path)
    #             template_version = fields.get('version')
    #             if template_version is not work_version:
    #                 fields['version'] = work_version
    #                 saver.Clip = template.apply_fields(fields)
    #                 saver_names.append("<b>(%s)</b> form: v%03d to: v%03d<br>" % (saver.GetAttrs("TOOLS_Name"), template_version, work_version))

    #     while comp.GetAttrs()['COMPB_Locked']:
    #         comp.Unlock()
    #     if saver_names:
    #         QtGui.QMessageBox.information(self, "Shotgun Saver Updater",
    #             "%s Saver Nodes: <br><br>%s <br><br>"
    #             "Have been updated!" % (len(saver_names), "".join(saver_names))
    #             )
    #     else:
    #         QtGui.QMessageBox.information(self, "Shotgun Saver Updater",
    #             "No one node have been updated!")

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

    def get_tool_pos(self, comp, tool):
        flow_view = comp.CurrentFrame.FlowView
        tool_pos = flow_view.GetPosTable(tool)
        x_pos = tool_pos[1.0]
        y_pos = tool_pos[2.0]

        return x_pos, y_pos

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
        flow_view = comp.CurrentFrame.FlowView
        max_x = None
        max_y = None

        for tool in comp.GetToolList(False).values():
            pos = flow_view.GetPosTable(tool)
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
