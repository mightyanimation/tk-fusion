import os
import re
import sys
import sgtk
import BlackmagicFusion as bmd
import traceback
import logging
import subprocess
import time
from sgtk.platform.qt import QtGui, QtCore

class ShotgunMenu(QtGui.QWidget):
    """Simple Test"""
    
    def __init__(self, engine):
        self.engine = engine
        self.saver_nodes = {}
        # Verify fusion
        self.verify_fusion()
        
        self.pyside2_bool = int(QtCore.__version__.split('.')[0]) > 4
        super(ShotgunMenu, self).__init__()
        #self.setGeometry(50, 50, 260, 100)
        self.setMinimumWidth(250)
        self.setWindowTitle("Shotgun: Menu Panel")

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
        
        if 'icon' in command_properties.keys(): icon_str = 'icon'
        if 'icons' in command_properties.keys(): icon_str = 'icons'
        if 'description' in command_properties.keys():
            description = command_properties['description']

        if icon_str:
            icon_data = command_properties[icon_str]
            if isinstance(icon_data, str): icon_path=icon_data
            else:
                i_key = icon_data.keys()[0]
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
        if triggered_element in self.engine.commands.keys():
            self.engine.commands[triggered_element]['callback'].__call__()
        elif triggered_element in self.saver_nodes.keys():
            self.create_saver(triggered_element)

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
                #Creating menu button
                menu_action = QtGui.QAction(ctx_option[0], self)
                menu_action.triggered.connect(ctx_option[1])
                self.context_menu.addAction(menu_action)

            elif ctx_option in self.engine.commands.keys():
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

        if len(self.saver_nodes.keys()):
            self.qvboxLayout.addWidget(sg_saver)
    
    def _jump_to_sg(self):
        """
        Jump to shotgun, launch web browser
        """
        url = self.engine.context.shotgun_url
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def create_saver(self, sg_saver_name):
        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()
        path = comp.GetAttrs()['COMPS_FileName']
        sg_saver_info = self.saver_nodes[sg_saver_name]

        work_template = self.engine.sgtk.template_from_path(path)
        fields = work_template.get_fields(path)

        work_version = work_template.get_fields(path).get('version')

        comp_format = comp.GetPrefs().get('Comp').get('FrameFormat')
        fields['height'] = int(comp_format.get('Height'))
        fields['width'] = int(comp_format.get('Width'))
        try:
            sg_shot = get_sg_shot_info(['sg_cut_in'])
            fields['SEQ'] = sg_shot['sg_cut_in']
        except:
            fields['SEQ'] = 1001

        render_template_name = sg_saver_info['render_template']
        render_template = self.engine.sgtk.templates[render_template_name]
        render_path = render_template.apply_fields(fields)

        comp.Lock(); comp.Lock()
        saver = comp.Saver({"Clip": render_path})
        saver_atts = {"TOOLS_Name": "sg_%{}".format(sg_saver_name),
                      "format_id": sg_saver_info['format_id'],
                      'format_settings': sg_saver_info['format_settings']}
        saver.SetAttrs(saver_atts)
        comp.Unlock(), comp.Unlock()
    
    def get_sg_shot_info(self, shot_fields):
        engine = self.engine
        sg = engine.shotgun
        sg_proj = engine.context.project

        context_tokens = str(engine.context).split(' ')
        entity_name = context_tokens[2]
        shot_filter = [['project', 'is', sg_proj],
                       ['code', 'is', entity_name]]
        # shot_fields = ['sg_cut_in', 'sg_cut_out']
        sg_shot = sg.find_one('Shot', shot_filter, shot_fields)
        return sg_shot



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

    def __create_sg_saver(self, ext_type):
        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()
        path = comp.GetAttrs()['COMPS_FileName']

        task_type = self.engine.context.entity.get("type")
        work_template = self.engine.sgtk.template_from_path(path)
        fields = work_template.get_fields(path)

        comp_format = comp.GetPrefs().get('Comp').get('FrameFormat')
        fields['height'] = int(comp_format.get('Height'))
        fields['width'] = int(comp_format.get('Width'))
        fields['output'] = 'output'

        text, ok = QtGui.QInputDialog.getText(self, 'Input Name Dialog', 'Enter output name:')
        
        if text and ok:
            fields['output'] = text

        review_template = self.engine.get_template_by_name("fusion_%s_render_mono_%s" % (task_type.lower(), ext_type))
        output = review_template.apply_fields(fields)
        output = re.sub(r'%(\d+)d', '', output)

        comp.Lock()

        saver = comp.Saver({"Clip": output})
        saver.CreateDir = 0
        saver.SetAttrs({"TOOLS_Name": "shotgun_%s" % ext_type})
        comp.Unlock()

    def __update_sg_saver(self):
        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()
        path = comp.GetAttrs()['COMPS_FileName']

        work_template = self.engine.sgtk.template_from_path(path)
        work_version = work_template.get_fields(path).get('version')
        
        savers = comp.GetToolList(False, "Saver").values()

        saver_names = []

        for saver in savers:
            path = saver.GetAttrs()['TOOLST_Clip_Name'].values()[0]
            template = self.engine.sgtk.template_from_path(path)
            if template:
                fields = template.get_fields(path)
                template_version = fields.get('version')
                if template_version is not work_version:
                    fields['version'] = work_version
                    saver.Clip = template.apply_fields(fields)
                    saver_names.append("<b>(%s)</b> form: v%03d to: v%03d<br>" % (saver.GetAttrs("TOOLS_Name"), template_version, work_version))
        if saver_names:
            QtGui.QMessageBox.information(self, "Shotgun Saver Updater",
                "%s Saver Nodes: <br><br>%s <br><br>"
                "Have been updated!" % (len(saver_names), "".join(saver_names))
                )
        else:
            QtGui.QMessageBox.information(self, "Shotgun Saver Updater",
                "No one node have been updated!")

    def verify_fusion(self):
        fusion = bmd.scriptapp("Fusion")
        comp = fusion.GetCurrentComp()
        fusion_exe = fusion.GetAttrs()['FUSIONS_FileName']

        # Check if are not using FusionRenderNode
        if not fusion_exe.endswith("FusionRenderNode.exe"): return None

        # TODO: check how to load fusion.exe instead of FusionRenderNode.exe
        print '{}\n{}\{}'.format(24 * '*', fusion_exe, 24 * '*')
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
            logger.debug(' ...Closing FusionRenderNode...')
            print ' ...Closing FusionRenderNode...'
            time.sleep(1)
        except:
            time.sleep(1)
        
        fusion = bmd.scriptapp("Fusion") # Reload fusion
        comp = fusion.GetCurrentComp() # Reload comp
   

        

