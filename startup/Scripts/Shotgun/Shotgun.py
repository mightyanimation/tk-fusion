import os
import re
import sys
import sgtk
import BlackmagicFusion as bmd
import traceback
import logging
from collections import OrderedDict

fusion = bmd.scriptapp("Fusion")
comp = fusion.GetCurrentComp()

logger = sgtk.LogManager.get_logger(__name__)


logger.debug("Launching toolkit in classic mode.")

env_engine = os.environ.get("SGTK_ENGINE")
env_context = os.environ.get("SGTK_CONTEXT")
context = sgtk.context.deserialize(env_context)

try:
    path = comp.GetAttrs()['COMPS_FileName']
    tk = sgtk.sgtk_from_path(path)
    context = tk.context_from_path(path)
except:
    pass

engine = sgtk.platform.start_engine(env_engine, context.sgtk, context)

from sgtk.platform.qt import QtGui, QtCore


class Window(QtGui.QWidget):
    """Simple Test"""
    
    def __init__(self):
        self.pyside2_bool = int(QtCore.__version__.split('.')[0]) > 4
        super(Window, self).__init__()
        self.setGeometry(50, 50, 200, 100)
        self.setMaximumWidth(225)
        self.setWindowTitle("Shotgun: Menu Panel")

        #Global layout
        self.qvboxLayout = QtGui.QVBoxLayout()
        self.setLayout(self.qvboxLayout)

        # Global context menu
        self.context_button = QtGui.QPushButton(str(engine.context))
        self.context_button.setStyleSheet("background-color: #4A586E")
        self.context_menu = QtGui.QMenu(self)
        self.context_button.setMenu(self.context_menu)
        self.qvboxLayout.addWidget(self.context_button)
        line_01 = QtGui.QFrame()
        line_01.setFrameShape(QtGui.QFrame.HLine)
        line_01.setFrameShadow(QtGui.QFrame.Sunken)
        self.qvboxLayout.addWidget(line_01)

        self.func_index = 0
        self.func_relations = {}

        # Populating menu
        self.populateLayout()

        # Menu always on top
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)


    def super_connect(self, pysideElement, cmd_name, element_type, external_func=None):
        if element_type == 'Action':
            """ Wrapper between pyside and pyside2 to connect QActions """
            action = pysideElement.triggered if self.pyside2_bool else pysideElement.activated
        elif element_type == 'Button':
            action = pysideElement.clicked

        if external_func is not None:
            action.connect(lambda: self.exec_n_close('ignored', external_func))
            return None

        # Add a relation with index strings will allow us to have
        # dynamic functions saved in a dict, otherwise you will 
        # execute always the last command in the forloops
        self.func_relations[str(self.func_index)] = str(cmd_name) 
        
        if self.func_index == 0: action.connect(lambda: self.exec_n_close('0'))
        elif self.func_index == 1: action.connect(lambda: self.exec_n_close('1'))
        elif self.func_index == 2: action.connect(lambda: self.exec_n_close('2'))
        elif self.func_index == 3: action.connect(lambda: self.exec_n_close('3'))
        elif self.func_index == 4: action.connect(lambda: self.exec_n_close('4'))
        elif self.func_index == 5: action.connect(lambda: self.exec_n_close('5'))
        elif self.func_index == 6: action.connect(lambda: self.exec_n_close('6'))
        elif self.func_index == 7: action.connect(lambda: self.exec_n_close('7'))
        elif self.func_index == 8: action.connect(lambda: self.exec_n_close('8'))
        elif self.func_index == 9: action.connect(lambda: self.exec_n_close('9'))
        elif self.func_index == 10: action.connect(lambda: self.exec_n_close('10'))
        elif self.func_index == 11: action.connect(lambda: self.exec_n_close('11'))
        elif self.func_index == 12: action.connect(lambda: self.exec_n_close('12'))
        elif self.func_index == 13: action.connect(lambda: self.exec_n_close('13'))
        elif self.func_index == 14: action.connect(lambda: self.exec_n_close('14'))
        elif self.func_index == 15: action.connect(lambda: self.exec_n_close('15'))
        elif self.func_index == 16: action.connect(lambda: self.exec_n_close('16'))
        elif self.func_index == 17: action.connect(lambda: self.exec_n_close('17'))
        elif self.func_index == 18: action.connect(lambda: self.exec_n_close('18'))
        elif self.func_index == 19: action.connect(lambda: self.exec_n_close('19'))
        elif self.func_index == 20: action.connect(lambda: self.exec_n_close('20'))
        elif self.func_index == 21: action.connect(lambda: self.exec_n_close('21'))
        elif self.func_index == 22: action.connect(lambda: self.exec_n_close('22'))
        elif self.func_index == 23: action.connect(lambda: self.exec_n_close('23'))
        elif self.func_index == 24: action.connect(lambda: self.exec_n_close('24'))
        elif self.func_index == 25: action.connect(lambda: self.exec_n_close('25'))
        elif self.func_index == 26: action.connect(lambda: self.exec_n_close('26'))
        elif self.func_index == 27: action.connect(lambda: self.exec_n_close('27'))
        elif self.func_index == 28: action.connect(lambda: self.exec_n_close('28'))
        elif self.func_index == 29: action.connect(lambda: self.exec_n_close('29'))

        elif self.func_index == 30: action.connect(lambda: self.exec_n_close('30'))
        elif self.func_index == 31: action.connect(lambda: self.exec_n_close('31'))
        elif self.func_index == 32: action.connect(lambda: self.exec_n_close('32'))
        elif self.func_index == 33: action.connect(lambda: self.exec_n_close('33'))
        elif self.func_index == 34: action.connect(lambda: self.exec_n_close('34'))
        elif self.func_index == 35: action.connect(lambda: self.exec_n_close('35'))
        elif self.func_index == 36: action.connect(lambda: self.exec_n_close('36'))
        elif self.func_index == 37: action.connect(lambda: self.exec_n_close('37'))
        elif self.func_index == 38: action.connect(lambda: self.exec_n_close('38'))
        elif self.func_index == 39: action.connect(lambda: self.exec_n_close('39'))
        elif self.func_index == 40: action.connect(lambda: self.exec_n_close('40'))
        elif self.func_index == 41: action.connect(lambda: self.exec_n_close('41'))
        elif self.func_index == 42: action.connect(lambda: self.exec_n_close('42'))
        elif self.func_index == 43: action.connect(lambda: self.exec_n_close('43'))
        elif self.func_index == 44: action.connect(lambda: self.exec_n_close('44'))
        elif self.func_index == 45: action.connect(lambda: self.exec_n_close('45'))
        elif self.func_index == 46: action.connect(lambda: self.exec_n_close('46'))
        elif self.func_index == 47: action.connect(lambda: self.exec_n_close('47'))
        elif self.func_index == 48: action.connect(lambda: self.exec_n_close('48'))
        elif self.func_index == 49: action.connect(lambda: self.exec_n_close('49'))
        elif self.func_index == 50: action.connect(lambda: self.exec_n_close('50'))
        
        # action.connect(lambda: self.exec_n_close(str(self.func_index)))
        self.func_index +=1

    def exec_n_close(self, index, external_func=None):
        if external_func is None:
            engine.commands[self.func_relations[index]].get('callback').__call__()
        else:
            external_func()
        self.close()
        #self.context_button.setText(str(engine.context))

    def populateLayout(self):

        # Context options will be displayed under the context button
        context_options = OrderedDict()
        context_options["Jump to Shotgun"] = {'function': self._jump_to_sg}
        context_options["Jump to File System"] = {'function': self._jump_to_fs}
        context_options["Ensure Tasks Folders"] = None
        context_options["Separator 01"] = None

        context_options['Jump to Screening Room in RV'] = None
        context_options['Jump to Screening Room Web Player'] = None
        context_options['Work Area Info...'] = None
        context_options["Separator 02"] = None

        context_options["Reload and Restart"] = None
        context_options["Open Log Folder"] = None
        context_options["Toggle Debug Logging"] = None
        
        # Populating menu with engine fuctions 
        for cmd_name, cmd_data in engine.commands.items():
            # Check if the option has icon
            tmp_func = cmd_data.get('callback')
            properties = cmd_data['properties']
            icon_str = icon_path = description = None
            if 'icon' in properties.keys(): icon_str = 'icon'
            if 'icons' in properties.keys(): icon_str = 'icons'
            if 'description' in properties.keys():
                description = properties['description']

            if icon_str:
                icon_data = properties[icon_str]
                if isinstance(icon_data, str): icon_path=icon_data
                else:
                    i_key = icon_data.keys()[0]
                    icon_path = icon_data[i_key]['png']

                # Special cases, for some reason, there is a string
                # in the path that does not exists....
                icon_path = icon_path.replace('__init__.pyc', '')

            # If the command should be in the context menu
            if cmd_name in context_options.keys():
                context_options[cmd_name] = {'icon': icon_path,
                                             'description': description}
                # End skip to the next iteration
                continue

            # Create the button for the main menu
            tmp_button = QtGui.QPushButton('  {}'.format(cmd_name))

            # updating action
            self.super_connect(tmp_button, cmd_name, 'Button')

            # If the button has icon
            if icon_path: tmp_button.setIcon(QtGui.QIcon(icon_path))
            # If the button has description
            if description: tmp_button.setToolTip(description)
            self.qvboxLayout.addWidget(tmp_button)

        # Populating context  button: menu elements
        for ctx_menu_name, ctx_menu_func in context_options.items():
            # Case 01
            # Separators
            if 'Separator' in ctx_menu_name:
                self.context_menu.addSeparator()
                self.context_menu.addSeparator()
                continue

            # Clear empty options (if there is no context function)
            if ctx_menu_func is None:
                continue

            #Creating button
            tmp_menu_btn = QtGui.QAction(ctx_menu_name, self)
            
            # Case 02
            # Functions
            if 'icon' in ctx_menu_func.keys(): tmp_icon = ctx_menu_func['icon']    
            else: tmp_icon = None

            if 'description' in ctx_menu_func.keys(): tmp_desc = ctx_menu_func['description']
            else: tmp_desc = None

            # updating action
            if 'function' in ctx_menu_func.keys():
                tmp_func = ctx_menu_func['function']
                self.super_connect(tmp_menu_btn, cmd_name, 'Action', tmp_func)
            else:
                self.super_connect(tmp_menu_btn, cmd_name, 'Action')

            if tmp_icon: tmp_menu_btn.setIcon(QtGui.QIcon(tmp_icon))
            if 'setToolTip' in dir(tmp_menu_btn):
                if tmp_desc: tmp_menu_btn.setToolTip(tmp_desc)
            self.context_menu.addAction(tmp_menu_btn)

        # Regular menu element

        line_02 = QtGui.QFrame()
        line_02.setFrameShape(QtGui.QFrame.HLine)
        line_02.setFrameShadow(QtGui.QFrame.Sunken)
        self.qvboxLayout.addWidget(line_02)

        #   Ouput options
        if engine.context.entity is not None:
            sg_saver_dpx_out = QtGui.QAction("Dpx Output", self)
            self.super_connect(sg_saver_dpx_out, 'X', 'Action',
                            lambda: self.__create_sg_saver('dpx'))

            sg_saver_exr16_out = QtGui.QAction("Exr, 16 bit Output", self)
            self.super_connect(sg_saver_exr16_out, 'X', 'Action',
                            lambda: self.__create_sg_saver('exr'))

            sg_saver_pngProxy_out = QtGui.QAction("Png, Proxy with Alpha", self)
            self.super_connect(sg_saver_pngProxy_out, 'X', 'Action',
                            lambda: self.__create_sg_saver('png'))

            sg_saver_review_out = QtGui.QAction("Shotgun Quick Review", self)
            self.super_connect(sg_saver_review_out, 'X', 'Action',
                            lambda: self.__create_sg_saver('mov'))

            shotgun_output_menu = QtGui.QMenu(self)
            map(shotgun_output_menu.addAction,
                [sg_saver_dpx_out, sg_saver_exr16_out,
                sg_saver_pngProxy_out, sg_saver_review_out])

            sg_saver = QtGui.QPushButton("Create Output Node")
            sg_saver.setMenu(shotgun_output_menu)
            sg_saver.setStyleSheet("background-color: #810B44")

            sg_saver_update = QtGui.QPushButton("Update Output Nodes")
            sg_saver_update.clicked.connect(lambda: self.__update_sg_saver())
            sg_saver_update.setStyleSheet("background-color: #4A586E")

            map(self.qvboxLayout.addWidget, [sg_saver, sg_saver_update])
                    
    def run(self):
        self.show()
    
    def _jump_to_sg(self):
        """
        Jump to shotgun, launch web browser
        """
        url = engine.context.shotgun_url
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _jump_to_fs(self):
        """
        Jump from context to FS
        """
        # launch one window for each location on disk
        paths = engine.context.filesystem_locations
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
                engine.logger.error("Failed to launch '%s'!", cmd)

    def __create_sg_saver(self, ext_type):
        comp = fusion.GetCurrentComp()
        path = comp.GetAttrs()['COMPS_FileName']

        task_type = engine.context.entity.get("type")
        work_template = engine.sgtk.template_from_path(path)
        fields = work_template.get_fields(path)

        comp_format = comp.GetPrefs().get('Comp').get('FrameFormat')
        fields['height'] = int(comp_format.get('Height'))
        fields['width'] = int(comp_format.get('Width'))
        fields['output'] = 'output'

        text, ok = QtGui.QInputDialog.getText(self, 'Input Name Dialog', 'Enter output name:')
        
        if text and ok:
            fields['output'] = text

        review_template = engine.get_template_by_name("fusion_%s_render_mono_%s" % (task_type.lower(), ext_type))
        output = review_template.apply_fields(fields)
        output = re.sub(r'%(\d+)d', '', output)

        comp.Lock()

        saver = comp.Saver({"Clip": output})
        saver.CreateDir = 0
        saver.SetAttrs({"TOOLS_Name": "shotgun_%s" % ext_type})
        comp.Unlock()

    def __update_sg_saver(self):
        comp = fusion.GetCurrentComp()
        path = comp.GetAttrs()['COMPS_FileName']

        work_template = engine.sgtk.template_from_path(path)
        work_version = work_template.get_fields(path).get('version')
        
        savers = comp.GetToolList(False, "Saver").values()

        saver_names = []

        for saver in savers:
            path = saver.GetAttrs()['TOOLST_Clip_Name'].values()[0]
            template = engine.sgtk.template_from_path(path)
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

app = QtGui.QApplication.instance()

wid = Window()
wid.run()

engine._qt_app.exec_()