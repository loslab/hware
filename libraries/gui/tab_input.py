import sys
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (QWidget, QGridLayout,QPushButton, QApplication)
from PyQt5 import QtCore

from PyQt5.QtWidgets import QLabel, QLineEdit, QGridLayout, QTextEdit,QSizePolicy, QPushButton, QProgressBar,QSlider, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import pathlib
import numpy as np
from libraries import OHW, UserDialogs, helpfunctions

class TabInput(QWidget):
#Python classes follow the CapWords convention
    
    def __init__(self, parent):
        super(TabInput, self).__init__(parent)
        self.parent=parent
        self.initUI()
        
    def initUI(self):
    
        self.info = QTextEdit()
        self.info.setText('In this tab you choose the input video. If a videoinfos.txt file is found, the information is processed automatically. Otherwise, please enter the framerate and microns per pixel.')
        self.info.setReadOnly(True)
        self.info.setMinimumWidth(700)
        self.info.setMaximumHeight(50)
        self.info.setMaximumWidth(800)
        self.info.setStyleSheet("background-color: LightSkyBlue")
    
        self.label_vidinfo = QLabel('Video info:')
        self.label_vidinfo.setFont(QFont("Times",weight=QFont.Bold))
        
        self.label_fps = QLabel('framerate [frames/s]')
        self.label_mpp = QLabel('scale [microns/pixel]')
        self.label_path = QLabel('Video path')
        self.label_input_path = QLabel('Path/...')
        self.label_results = QLabel('Current results folder')
        self.label_results_folder = QLabel('Path/results....')
        
        self.btn_results_folder = QPushButton('Change results folder')
        self.btn_results_folder.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.btn_results_folder.setEnabled(False)
        self.btn_results_folder.clicked.connect(self.on_changeResultsfolder)
        
        #display first image
        self.fig_firstIm, self.ax_firstIm = plt.subplots(1,1)#, figsize = (5,5))
        self.fig_firstIm.patch.set_facecolor('#ffffff')##cd0e49')
        self.fig_firstIm.subplots_adjust(bottom=0, top=1, left=0, right=1)
        self.ax_firstIm.axis('off')
        self.canvas_firstImage = FigureCanvas(self.fig_firstIm)
        self.canvas_firstImage.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.canvas_firstImage.setFixedSize(500,500)
        
        self.edit_fps = QLineEdit()
        self.edit_mpp = QLineEdit()
        
        self.edit_fps.setFixedWidth(70)
        self.edit_mpp.setFixedWidth(70)
        
        #self.edit_fps.textChanged.connect(self.on_change_fps) # don't connect as this would allow changing of
        #self.edit_mpp.textChanged.connect(self.on_change_mpp) # values after calculation is already done
        
        self.button_loadVideo = QPushButton('Load video')
        self.button_loadVideo.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.button_loadVideo.clicked.connect(self.on_loadVideo)
        
        # upon loading video... use standard parameters if no other are present
        self.btn_reloadVideo = QPushButton('Reload analysis video')
        self.btn_reloadVideo.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
        self.btn_reloadVideo.clicked.connect(self.on_reloadVideo)
        self.btn_reloadVideo.setEnabled(False)
        
        self.progressbar_loadVideo = QProgressBar()#self)
        self.progressbar_loadVideo.setMaximum(1)  
        self.progressbar_loadVideo.setValue(0)
        self.progressbar_loadVideo.setFixedWidth(250)
        self.progressbar_loadVideo.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Fixed)
                
        self.label_slider_blackval = QLabel('Black value')
        self.slider_blackval = QSlider(Qt.Vertical)
        self.slider_blackval.setMinimum(0)
        self.slider_blackval.setMaximum(100)
        self.slider_blackval.setValue(0)
        self.slider_blackval.setFixedHeight(200)
        self.slider_blackval.setEnabled(False)
        self.slider_blackval.valueChanged.connect(self.on_change_blackVal)
        
        self.label_slider_whiteval = QLabel('White value')
        self.slider_whiteval = QSlider(Qt.Vertical)
        self.slider_whiteval.setMinimum(0)
        self.slider_whiteval.setMaximum(100)
        self.slider_whiteval.setValue(0)
        self.slider_whiteval.setFixedHeight(200)
        self.slider_whiteval.setEnabled(False)
        self.slider_whiteval.valueChanged.connect(self.on_change_whiteVal)
        
        self.label_brightness = QLabel('Adjust brightness:')
        self.label_brightness.setFont(QFont("Times",weight=QFont.Bold))
        
        self.btn_brightness = QPushButton('Reset brightness')
        self.btn_brightness.clicked.connect(self.on_resetBrightness)
        self.btn_brightness.setEnabled(False)
        
        self.grid_prop = QGridLayout()        
        self.grid_prop.setSpacing(10)
        self.grid_prop.setAlignment(Qt.AlignTop|Qt.AlignLeft)

        self.grid_prop.addWidget(self.button_loadVideo,0,0)
        self.grid_prop.addWidget(self.btn_reloadVideo, 1, 0)
        self.grid_prop.addWidget(self.progressbar_loadVideo,0,1)
        self.grid_prop.addWidget(self.label_vidinfo,2,0,1,2)
        self.grid_prop.addWidget(self.label_path,3,0)
        self.grid_prop.addWidget(self.label_input_path,3,1)
        self.grid_prop.addWidget(self.label_fps, 4, 0)
        self.grid_prop.addWidget(self.edit_fps, 4, 1)
        self.grid_prop.addWidget(self.label_mpp, 5, 0)
        self.grid_prop.addWidget(self.edit_mpp,5, 1)
        self.grid_prop.addWidget(self.label_results,6,0)
        self.grid_prop.addWidget(self.label_results_folder,6,1)
        self.grid_prop.addWidget(self.btn_results_folder,7,0,1,2)
        
        self.grid_slider = QGridLayout()
        self.grid_slider.setSpacing(10)
        self.grid_slider.setAlignment(Qt.AlignTop|Qt.AlignLeft)
        
        self.grid_slider.addWidget(self.label_brightness,0,0,1,2)
        self.grid_slider.addWidget(self.label_slider_blackval,1,0)
        self.grid_slider.addWidget(self.label_slider_whiteval,1,1)
        self.grid_slider.addWidget(self.slider_blackval,2,0, Qt.AlignHCenter)
        self.grid_slider.addWidget(self.slider_whiteval,2,1, Qt.AlignHCenter)
        self.grid_slider.addWidget(self.btn_brightness,1,2)
             
        self.grid_overall = QGridLayout()#self._main)
        self.grid_overall.addWidget(self.info,0,0,1,2)
        self.grid_overall.addLayout(self.grid_prop,1,0)
        self.grid_overall.addLayout(self.grid_slider,2,0,Qt.AlignTop|Qt.AlignLeft) # has to be added here?
        self.grid_overall.addWidget(self.canvas_firstImage,1,1,2,1,Qt.AlignTop|Qt.AlignLeft)#-1,1
        self.grid_overall.setAlignment(Qt.AlignTop|Qt.AlignLeft)      
        
        self.setLayout(self.grid_overall) 

        for label in self.findChildren(QLabel):
            label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        for LineEdit in self.findChildren(QLineEdit):
            LineEdit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        for Slider in self.findChildren(QSlider):
            Slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            
    def on_loadVideo(self):
        self.progressbar_loadVideo.setValue(0)
        
        #choose a folder
        msg = 'Choose an input video: file of type .mp4, .avi, .mov or a .tif file in a folder containing a sequence of .tif-images'
        try:
            fileName  = UserDialogs.chooseFileByUser(message=msg, input_folder=self.parent.config['LAST SESSION']['input_folder'])
        except Exception:
            fileName  = UserDialogs.chooseFileByUser(message=msg)
        
        #if 'cancel' was pressed: simply do nothing and wait for user to click another button
        if (fileName[0]  == ''):
            return

        inputpath = pathlib.Path(fileName[0])
        #save changes to config file
        self.parent.config.set("LAST SESSION", "input_folder", str((inputpath / "..").resolve()))# how to implement with parent?
        helpfunctions.save_config(self.parent.config)

        # create OHW object to work with motion vectors
        self.parent.current_ohw.save_ohw() #save old ohw when loading new file
        self.parent.current_ohw = OHW.OHW()
        self.current_ohw = self.parent.current_ohw
        
        #read imagestack
        self.import_video_thread = self.current_ohw.import_video_thread(inputpath)
        self.import_video_thread.start()
        self.progressbar_loadVideo.setRange(0,0)
        self.import_video_thread.finished.connect(self.finish_loadVideo)
            
    def finish_loadVideo(self):
        self.progressbar_loadVideo.setRange(0,1)
        self.progressbar_loadVideo.setValue(1)
        self.parent.init_ohw()
        #update videoinfos with data from current_ohw

    def on_reloadVideo(self):
        """
            reloads video files into current_ohw
            e.g. when analysis file is opened
        """
        self.progressbar_loadVideo.setValue(0)            
        self.reload_video_thread = self.current_ohw.reload_video_thread()
        self.reload_video_thread.start()
        self.progressbar_loadVideo.setRange(0,0)
        self.reload_video_thread.finished.connect(self.finish_reloadVideo)
        
    def on_changeResultsfolder(self):
        #choose a folder
        msg = 'Choose a new folder for saving your results'
        folderName = UserDialogs.chooseFolderByUser(msg, input_folder=self.current_ohw.analysis_meta['results_folder'])#, input_folder=self.config['LAST SESSION']['results_folder'])  
        
        #if 'cancel' was pressed: simply do nothing and wait for user to click another button
        if (folderName == ''):
            return
        
        self.current_ohw.analysis_meta["results_folder"] = pathlib.Path(folderName)
        self.label_results_folder.setText(folderName)
        # print('New results folder: %s' %folderName)
        
    def finish_reloadVideo(self):
        self.progressbar_loadVideo.setRange(0,1)
        self.progressbar_loadVideo.setValue(1)
        self.current_ohw.set_analysisImageStack(px_longest = self.current_ohw.analysis_meta["px_longest"])
        self.parent.init_ohw()
        
    def init_ohw(self): #was update_tab_input
        """
            updates info displayed in inputtab
            -> loading of new video or loading of analysis file
        """
        self.current_ohw = self.parent.current_ohw
        self.edit_fps.setText(str(self.current_ohw.videometa['fps']))
        self.edit_mpp.setText(str(self.current_ohw.videometa['microns_per_px']))            
        # disable input field if videoinfos.txt available? if self.current_ohw.videometa['infofile_exists'] == True: ....
        
        # check if video is loaded and update controls
        if self.current_ohw.video_loaded == True:
            self.display_firstImage(self.current_ohw.rawImageStack[0])
            self.slider_blackval.setEnabled(True)
            self.slider_whiteval.setEnabled(True)
            self.btn_brightness.setEnabled(True)
            self.btn_reloadVideo.setEnabled(False)
            self.set_start_brightness()

        else:
            self.display_firstImage()
            self.slider_blackval.setEnabled(False)
            self.slider_whiteval.setEnabled(False)
            self.btn_brightness.setEnabled(False)
            self.btn_reloadVideo.setEnabled(True)
        
        inputpath = str(self.current_ohw.videometa['inputpath'])
        self.label_input_path.setText(inputpath)
        
        results_folder = str(self.current_ohw.analysis_meta['results_folder']) #pathlib.PureWindowsPath(
        self.label_results_folder.setText(results_folder)
        self.btn_results_folder.setEnabled(True)
    
    def display_firstImage(self, image = None):
        self.ax_firstIm.clear()
        self.ax_firstIm.axis('off')
        # display first image and update controls
        if type(image) == np.ndarray:
            #print(self.current_ohw.videometa["Blackval"], self.current_ohw.videometa["Whiteval"])
            self.imshow_firstImage = self.ax_firstIm.imshow(image, cmap = 'gray', vmin = self.current_ohw.videometa["Blackval"], vmax = self.current_ohw.videometa["Whiteval"])
        else:
            self.ax_firstIm.text(0.5, 0.5,'no video loaded yet',
                size=14, ha='center', va='center', backgroundcolor='indianred', color='w')
        self.canvas_firstImage.draw()
        
    def on_change_blackVal(self):          
        """
            change the white values for image display
            using a slider with 2 handles would be easiest option...
        """
     
        # save the new value to videometa
        self.current_ohw.videometa["Blackval"] = self.slider_blackval.value()

        # set allowed whitevals and blackvals           
        self.slider_whiteval.setMinimum(self.current_ohw.videometa["Blackval"])            
        self.update_brightness()

    def on_change_whiteVal(self):          
        """
            change the white values for image display
        """
        # save the new value to videometa
        self.current_ohw.videometa["Whiteval"] = self.slider_whiteval.value()

        # set allowed whitevals and blackvals           
        self.slider_blackval.setMaximum(self.current_ohw.videometa["Whiteval"])            
        self.update_brightness()

    def on_resetBrightness(self):
        """ resets the image display back to the original values
        """
        self.current_ohw.videometa["Blackval"] = self.current_ohw.raw_videometa["Blackval"]
        self.current_ohw.videometa["Whiteval"] = self.current_ohw.raw_videometa["Whiteval"]
        
        self.set_start_brightness()
        self.update_brightness()

    #def on_change_fps(self):
    #    self.current_ohw.videometa['fps'] = float(self.edit_fps.text())
    
    #def on_change_mpp(self):
    #    self.current_ohw.videometa['microns_per_px'] = float(self.edit_mpp.text())
        
    def update_brightness(self):
        vmin, vmax = self.current_ohw.videometa["Blackval"], self.current_ohw.videometa["Whiteval"]
        self.imshow_firstImage.set_clim(vmin=vmin, vmax=vmax)
        self.canvas_firstImage.draw()
        
        if (self.current_ohw.video_loaded and self.current_ohw.analysis_meta["has_MVs"]):
            self.parent.tab_quiver.updateQuiverBrightness(vmin=vmin, vmax=vmax) # how can this be done in a nice way?
            
    def set_start_brightness(self):
        ''' set brightness sliders to raw values '''
        self.slider_whiteval.blockSignals(True)# prevent calling on_change_whiteVal/blackVal
        self.slider_blackval.blockSignals(True)
        self.slider_whiteval.setMaximum(self.current_ohw.videometa["Whiteval"]*3)
        self.slider_blackval.setMaximum(self.current_ohw.videometa["Whiteval"])      
        self.slider_whiteval.setValue(self.current_ohw.videometa["Whiteval"])
        self.slider_blackval.setValue(self.current_ohw.videometa["Blackval"])
        self.slider_whiteval.setMinimum(self.current_ohw.videometa["Blackval"])
        self.slider_whiteval.blockSignals(False)
        self.slider_blackval.blockSignals(False)