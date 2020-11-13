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
logging.basicConfig(level=logging.WARNING)
engine.logger.setLevel(logging.WARNING)

from sgtk.platform.qt import QtGui, QtCore


class Window(QtGui.QWidget):
    """Simple Test"""
    
    def __init__(self):
        self.pyside2_bool = int(QtCore.__version__.split('.')[0]) > 4
        super(Window, self).__init__()
        self.setGeometry(50, 50, 200, 100)
        #self.setFixedSize(220,440)
        self.setMaximumWidth(215)
        self.setWindowTitle("Shotgun: Menu Panel")
        #self.mainlayout()

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

        # Populating menu
        self.populateLayout()

        # Menu always on top
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)


    def new_activate(self, pysideAction, targetFunction, *args):
        """ Wrapper between pyside and pyside2 to connect QActions """
        tmp_func = lambda: targetFunction(args) if len(args) else targetFunction()
        action = pysideAction.triggered if self.pyside2_bool else pysideAction.activated
        action.connect(tmp_func)

    def populateLayout(self):
        context_options = OrderedDict()
        context_options["Jump to Shotgun"] = self._jump_to_sg
        context_options["Jump to File System"] = self._jump_to_fs
        context_options["Ensure Tasks Folders"] = None
        context_options["Separator 01"] = None

        context_options['Jump to Screening Room in RV'] = None
        context_options['Jump to Screening Room Web Player'] = None
        context_options['Work Area Info...'] = None
        context_options["Separator 02"] = None

        context_options["Reload and Restart"] = None
        context_options["Open Log Folder"] = None
        context_options["Toggle Debug Logging"] = None


        
        for cmd_name, cmd_data in engine.commands.items():
            # Check if the option has icon
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

                icon_path = icon_path.replace('__init__.pyc', '')

            # If the command should be in the context menu
            if cmd_name in context_options.keys():
                context_options[cmd_name] = {'function':cmd_data['callback'],
                                             'icon': icon_path,
                                             'description': description}
                # End skip to the next iteration
                continue

            # Create the button for the main menu
            tmp_button = QtGui.QPushButton('  {}'.format(cmd_name))
            tmp_button.clicked.connect(cmd_data['callback'])

            # If the button has icon
            if icon_path: tmp_button.setIcon(QtGui.QIcon(icon_path))

            # If the button has description
            if description: tmp_button.setToolTip(description)


            self.qvboxLayout.addWidget(tmp_button)

        for ctx_menu_name, ctx_menu_func in context_options.items():
            #Creating button
            tmp_menu_btn = QtGui.QAction(ctx_menu_name, self)

            # Case 01
            # Separators
            if 'Separator' in ctx_menu_name:
                self.context_menu.addSeparator()
                self.context_menu.addSeparator()
                continue

            # Case 02
            # If we only have a function to handle
            if not isinstance(ctx_menu_func, dict):
                self.new_activate(tmp_menu_btn, ctx_menu_func)
                self.context_menu.addAction(tmp_menu_btn)
                continue
            
            # Case 03
            # Extra info
            print ctx_menu_name, ctx_menu_func
            tmp_func = ctx_menu_func['function']
            tmp_icon = ctx_menu_func['icon']
            tmp_desc = ctx_menu_func['description']

            # updating action
            self.new_activate(tmp_menu_btn, tmp_func)
            if tmp_icon: tmp_menu_btn.setIcon(QtGui.QIcon(tmp_icon))
            if 'setToolTip' in dir(tmp_menu_btn):
                if tmp_desc: tmp_menu_btn.setToolTip(tmp_desc)
            self.context_menu.addAction(tmp_menu_btn)

        
    def mainlayout(self):
        #######################################
        self.jump_to_sg = QtGui.QAction("Jump to Shotgun", self)
        self.new_activate(self.jump_to_sg, self._jump_to_sg)

        self.jump_to_fs = QtGui.QAction("Jump to File System", self)
        self.new_activate(self.jump_to_fs, self._jump_to_fs)

        self.jump_to_rv = QtGui.QAction("Jump to Screening Room in RV", self)
        self.new_activate(self.jump_to_rv, self.callMenu, 'Jump to Screening Room in RV')

        self.jump_to_wp = QtGui.QAction("Jump to Screening Room Web Player", self)
        self.new_activate(self.jump_to_wp, self.callMenu, 'Jump to Screening Room Web Player')

        self.work_aria_info = QtGui.QAction("Work Area Info...", self)
        self.new_activate(self.work_aria_info, self.callMenu, 'Work Area Info...')

        self.context_menu = QtGui.QMenu(self)
        map(self.context_menu.addAction, [self.jump_to_sg, self.jump_to_fs])
        self.context_menu.addSeparator()
        map(self.context_menu.addAction, [self.jump_to_rv, self.jump_to_wp, self.work_aria_info])
        self.context_button = QtGui.QPushButton(str(engine.context))
        self.context_button.setStyleSheet("background-color: #4A586E")
        self.context_button.setMenu(self.context_menu)

        #######################################
        self.open = QtGui.QPushButton("File Open...")
        self.open.clicked.connect(lambda: self.callMenu('File Open...'))

        self.save = QtGui.QPushButton("File Save...")
        self.save.clicked.connect(lambda: self.callMenu('File Save...'))

        self.snapshot = QtGui.QPushButton("Snapshot...")
        self.snapshot.clicked.connect(lambda: self.callMenu('Snapshot...'))

        self.publish = QtGui.QPushButton("Publish...")
        self.publish.clicked.connect(lambda: self.callMenu('Publish...'))

        self.load = QtGui.QPushButton("Load...")
        self.load.clicked.connect(lambda: self.callMenu('Load...'))

        self.breakdown = QtGui.QPushButton("Scene Breakdown...")
        self.breakdown.clicked.connect(lambda: self.callMenu('Scene Breakdown...'))

        #######################################
        self.snapshot_menu_history = QtGui.QAction("Snapshot History...", self)
        self.new_activate(self.snapshot_menu_history, self.callMenu, 'Snapshot History...')

        self.snapshot_menu_snapshot = QtGui.QAction("Snapshot...", self)
        self.new_activate(self.snapshot_menu_snapshot, self.callMenu, 'Snapshot...')

        self.snapshot_menu = QtGui.QMenu(self)
        self.snapshot_menu.addAction(self.snapshot_menu_history)
        self.snapshot_menu.addAction(self.snapshot_menu_snapshot)

        self.snapshot_button = QtGui.QPushButton("Scene Snapshot")
        self.snapshot_button.setMenu(self.snapshot_menu)

        #######################################
        self.pannel = QtGui.QPushButton("Shotgun Panel...")
        self.pannel.clicked.connect(lambda: self.callMenu('Shotgun Panel...'))

        #######################################
        self.shotgun_workfiles_menu_open = QtGui.QAction("File Open...", self)
        self.new_activate(self.shotgun_workfiles_menu_open, self.callMenu, 'File Open...')

        self.shotgun_workfiles_menu_save = QtGui.QAction("File Save...", self)
        self.new_activate(self.shotgun_workfiles_menu_save, self.callMenu, 'File Save...')

        self.shotgun_workfiles_menu = QtGui.QMenu(self)
        self.shotgun_workfiles_menu.addAction(self.shotgun_workfiles_menu_open)
        self.shotgun_workfiles_menu.addAction(self.shotgun_workfiles_menu_save)

        self.shotgun_workfiles = QtGui.QPushButton("Shotgun Workfiles") 
        self.shotgun_workfiles.setMenu(self.shotgun_workfiles_menu)

        #######################################
        self.syncFr = QtGui.QPushButton("Sync Frame Range with Shotgun")
        self.syncFr.clicked.connect(lambda: self.callMenu('Sync Frame Range with Shotgun'))

        #######################################
        self.sg_saver_dpx_out = QtGui.QAction("Dpx Output", self)
        self.new_activate(self.sg_saver_dpx_out, self.__create_sg_saver, 'dpx')

        self.sg_saver_exr16_out = QtGui.QAction("Exr, 16 bit Output", self)
        self.new_activate(self.sg_saver_exr16_out, self.__create_sg_saver, 'exr')

        self.sg_saver_pngProxy_out = QtGui.QAction("Png, Proxy with Alpha", self)
        self.new_activate(self.sg_saver_pngProxy_out, self.__create_sg_saver, 'png')

        self.sg_saver_review_out = QtGui.QAction("Shotgun Quick Review", self)
        self.new_activate(self.sg_saver_review_out, self.__create_sg_saver, 'mov')

        self.shotgun_output_menu = QtGui.QMenu(self)
        map(self.shotgun_output_menu.addAction,
            [self.sg_saver_dpx_out, self.sg_saver_exr16_out,
             self.sg_saver_pngProxy_out, self.sg_saver_review_out])

        self.sg_saver = QtGui.QPushButton("Create Output Node")
        self.sg_saver.setMenu(self.shotgun_output_menu)
        self.sg_saver.setStyleSheet("background-color: #810B44")

        self.sg_saver_update = QtGui.QPushButton("Update Output Nodes")
        self.sg_saver_update.clicked.connect(lambda: self.__update_sg_saver())
        self.sg_saver_update.setStyleSheet("background-color: #4A586E")

        #######################################
        qvbox = QtGui.QVBoxLayout()
        qvbox.addWidget(self.context_button)

        self.line_context = QtGui.QFrame()
        self.line_context.setFrameShape(QtGui.QFrame.HLine)
        self.line_context.setFrameShadow(QtGui.QFrame.Sunken)
        map(qvbox.addWidget,
            [self.line_context, self.open, self.snapshot,
             self.save, self.publish])

        self.line_open = QtGui.QFrame()
        self.line_open.setFrameShape(QtGui.QFrame.HLine)
        self.line_open.setFrameShadow(QtGui.QFrame.Sunken)
        map(qvbox.addWidget,
            [self.line_open, self.load, self.breakdown, self.snapshot_button,
             self.pannel, self.shotgun_workfiles, self.syncFr])

        self.line_tools = QtGui.QFrame()
        self.line_tools.setFrameShape(QtGui.QFrame.HLine)
        self.line_tools.setFrameShadow(QtGui.QFrame.Sunken)
        map(qvbox.addWidget,
            [self.line_tools, self.sg_saver, self.sg_saver_update])
        
        # qvbox.insertStretch(2)
        self.setLayout(qvbox)
                    
    def run(self):
        self.show()
    
    def callMenu(self, name):
        if isinstance(name, tuple):
            name = name[0]
        for item in engine.commands.items():
            if name in item[0] or name == item[0]:
                item[1].get('callback').__call__()
                break
        
        if name in ["File Open...", "File Save..."]:
            self.context_button.setText(str(engine.context))

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