# -*- coding: utf-8 -*-

import os, sys
import time
import pathlib
import glob
import cv2
import configparser
import copy
from matplotlib.lines import Line2D
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

from PyQt5.QtWidgets import QMainWindow, QHeaderView, QCheckBox, QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, QDoubleSpinBox, QStyle, QSlider, QSizePolicy, QAction, QTextEdit, QMessageBox, QComboBox, QProgressBar, QSpinBox, QFileDialog, QTabWidget, QWidget, QLabel, QVBoxLayout, QGridLayout, QPushButton, QApplication, QDesktopWidget, QDialogButtonBox
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor, QImage
from PyQt5.QtCore import Qt, pyqtSignal
 
from libraries import MultipleFoldersByUser, UserDialogs, Filters, helpfunctions, QuiverExportOptions, plotfunctions, OHW

class TableWidget(QWidget):
        def __init__(self, parent):   
            super(QWidget, self).__init__(parent)
            
            #read config file
            self.config = configparser.ConfigParser()
            self.config.read('config.ini')
         
            self.layout = QGridLayout(self)
 
            # create OHW object to work with motion vectors
            self.OHW = OHW.OHW()
            # Initialize tab screen
            self.tabs = QTabWidget()
            # Add tabs to widget        
            self.layout.addWidget(self.tabs)
            self.setLayout(self.layout)
            #settings for tabs
            #place tabs at the left side of the GUI:
            #self.tabs.setTabPosition(QTabWidget.West)

            self.plotted_peaks = False
            
            self.tab1 = QWidget()    
            self.tab2 = QWidget()
            self.tab3 = QWidget()
            self.tab4 = QWidget()
            self.tab5 = QWidget()
            self.tab6 = QWidget()
            self.tabROIs = QWidget()
            self.tabs.resize(800,800)
             
            # Add tabs
            self.tabs.addTab(self.tab1,"Video Input ")
            self.tabs.addTab(self.tabROIs, "Manage ROIs")
            self.tabs.addTab(self.tab2,"Compute motion")
            self.tabs.addTab(self.tab3,"Beating kinetics")
            self.tabs.addTab(self.tab4,"Heatmaps and Quiverplots")
            self.tabs.addTab(self.tab5,"Time averaged motion")
            self.tabs.addTab(self.tab6,"Batch analysis")
            
            color_for_info = QColor(198, 255, 26)
            self.pixmap_width = 250
            self.ROI_coordinates = []
            self.ROI_names = []
            self.ROI_OHWs = []
            
            #default values for quiver export
       #     self.config.getboolean(section='DEFAULT QUIVER SETTINGS', option='one_view')
            self.quiver_settings = {}# self.config['DEFAULT QUIVER SETTINGS']
            for item in ['one_view', 'three_views', 'show_scalebar']:
                self.quiver_settings[item] = self.config.getboolean(section='DEFAULT QUIVER SETTINGS', option=item)
             
            for item in ['quiver_density']:
                self.quiver_settings[item] = self.config.getint(section='DEFAULT QUIVER SETTINGS', option=item)
        
            for item in ['video_length']:
                self.quiver_settings[item] = self.config.getfloat(section='DEFAULT QUIVER SETTINGS', option=item)
        
 ########### fill the first tab ##################
            info_loadFile = QTextEdit()
            info_loadFile.setText('In this tab you choose the input folder. If a videoinfos.txt file is found, the information is processed automatically. Otherwise, please enter the framerate and microns per pixel.')
            info_loadFile.setReadOnly(True)
            info_loadFile.setMaximumHeight(40)
            info_loadFile.setMaximumWidth(800)
            info_loadFile.setTextBackgroundColor(color_for_info)
            info_loadFile.setStyleSheet("background-color: LightSkyBlue")
            
            label_loadFile = QLabel('Load file(s): ')
            self.label_fps = QLabel('Enter the framerate [frames/sec]: ')
            self.label_px_per_micron = QLabel('Enter the number of micrometer per pixel: ')
            label_display = QLabel('Display image: ')
            label_loadFile.setFont(QFont("Times",weight=QFont.Bold))
            label_display.setFont(QFont("Times",weight=QFont.Bold))


            self.line_fps = QLineEdit()
            self.line_px_perMicron = QLineEdit()

            self.line_px_perMicron.setText(self.config['DEFAULT VALUES']['px_per_micron'])
            self.line_fps.setText(self.config['DEFAULT VALUES']['fps'])
            self.line_px_perMicron.textChanged.connect(self.changePxPerMicron)
            self.line_fps.textChanged.connect(self.changeFPS)            
            
            """
            #call changeFPS and changeDPI for the first time to get initial values
            # not necessary anymore, as values directly read in from file
            self.fps = self.changeFPS()
            self.px_per_micron = self.changePxPerMicron()
            # todo: check if values are also updated
            """
            
            #display image
            source = 'Chosen image: '
            self.label_chosen_image = QLabel(str(source + ' - '))
            self.image = QLabel()
            self.image.setPixmap(QPixmap('icons/dummy_image.png').scaledToWidth(self.pixmap_width))
        
            #display first image... really necessary to use a mpl figure for that purpose?
            self.fig_firstIm, self.ax_firstIm = plt.subplots(1,1)
            self.ax_firstIm.axis('off')
            self.canvas_firstImage = FigureCanvas(self.fig_firstIm)
            
            #load-video button
            self.button_loadVideo = QPushButton('Load video')
            self.button_loadVideo.resize(self.button_loadVideo.sizeHint())
            self.button_loadVideo.clicked.connect(self.on_loadVideo)
                       
            #create sliders to change the blackval and whiteval of the image
            self.label_slider_blackval = QLabel('Black value: ')
            self.slider_blackval = QSlider(Qt.Vertical)
            self.slider_blackval.setMinimum(0)
            self.slider_blackval.setMaximum(100)
            self.slider_blackval.setValue(0)
            #self.slider_blackval.setTickPosition(QSlider.TicksBelow)
            #self.slider_blackval.setTickInterval(5)
            self.slider_blackval.valueChanged.connect(self.change_blackWhiteVal)
            
            self.label_slider_whiteval = QLabel('White value: ')
            self.slider_whiteval = QSlider(Qt.Vertical)
            self.slider_whiteval.setMinimum(0)
            self.slider_whiteval.setMaximum(100)
            self.slider_whiteval.setValue(0)
            #self.slider_whiteval.setTickPosition(QSlider.TicksBelow)
            #self.slider_whiteval.setTickInterval(5)
            self.slider_whiteval.valueChanged.connect(self.change_blackWhiteVal)
            
            #reset the black and white values
            self.button_reset_blackWhiteVal = QPushButton('Reset black and white value')
            self.button_reset_blackWhiteVal.resize(self.button_reset_blackWhiteVal.sizeHint())
            self.button_reset_blackWhiteVal.clicked.connect(self.on_resetBlackWhiteVal)
            
            #label to display current results folder
            self.label_resultsfolder = QLabel('Current results folder: ')
            self.label_resultsfolder.setFont(QFont("Times",weight=QFont.Bold))
                        
            #button for changing the results folder
            self.button_change_resultsfolder = QPushButton('Change results folder ')
            self.button_change_resultsfolder.resize(self.button_change_resultsfolder.sizeHint())
            self.button_change_resultsfolder.clicked.connect(self.on_changeResultsfolder)
            self.button_change_resultsfolder.setEnabled(False)
            
            #succeed-button
            self.button_succeed_tab1 = QPushButton('Move on to the next tab if this button is green!')
            self.button_succeed_tab1.setStyleSheet("background-color: IndianRed")
            
            #reset-button
            self.button_reset = QPushButton('Restart with new data')
            self.button_reset.resize(self.button_reset.sizeHint())
            self.button_reset.clicked.connect(self.restartGUI)      
            
            #progressbar in tab1  
            #rename progressbars in future?
            self.progressbar_loadStack = QProgressBar(self)
            self.progressbar_loadStack.setMaximum(1)  
            self.progressbar_loadStack.setValue(0)
            
            col_left = 0
            col_right =  0, 1, 2
            self.tab1.layout = QGridLayout(self)
            self.tab1.layout.setSpacing(25)
            self.tab1.layout.addWidget(self.button_reset,           1,  1, 1, 2)
            self.tab1.layout.addWidget(info_loadFile,               1,  0)
            self.tab1.layout.addWidget(label_loadFile,              2,  0)            
            self.tab1.layout.addWidget(self.label_fps,              4,  0)
            self.tab1.layout.addWidget(self.line_fps,               4,  1, 1, 2)
            self.tab1.layout.addWidget(self.label_px_per_micron,    5,  0)
            self.tab1.layout.addWidget(self.line_px_perMicron,      5,  1, 1, 2)
            self.tab1.layout.addWidget(self.button_loadVideo,      6,  0)
            self.tab1.layout.addWidget(self.progressbar_loadStack,  7,  0)
            self.tab1.layout.addWidget(self.button_succeed_tab1,    8,  0)
            self.tab1.layout.addWidget(label_display,               9, 0)
            self.tab1.layout.addWidget(self.label_chosen_image,     10, 0)
          #  self.tab1.layout.addWidget(self.button_selectROI,       11, 0)
           # self.tab1.layout.addWidget(self.button_manageROIs,      12, 0)
            self.tab1.layout.addWidget(self.image,                  14, 0)
            self.tab1.layout.addWidget(self.label_resultsfolder,    19, 0)
            self.tab1.layout.addWidget(self.button_change_resultsfolder, 20,0)
            
            self.tab1.setLayout(self.tab1.layout)

########### fill the ROI selection tab ###########
            info_ROI = QTextEdit()
            info_ROI.setText('In this tab you can add, edit and choose Regions of Interest.')
            info_ROI.setReadOnly(True)
            info_ROI.setMaximumHeight(40)
            info_ROI.setMaximumWidth(800)
            info_ROI.setStyleSheet("background-color: LightSkyBlue")
            
            #Button for ROI selection
            self.button_selectROI = QPushButton('Add a Region of Interest (ROI)')
            self.button_selectROI.resize(self.button_selectROI.sizeHint())
            self.button_selectROI.clicked.connect(self.on_selectROI)
            self.button_selectROI.setEnabled(False)

#            #add a table to display ROIs and corresponding names
#            self.ROI_tableWidget = QTableWidget()
#            self.ROI_tableWidget.setRowCount(2)
#            self.ROI_tableWidget.setColumnCount(2)
#            #titles
#            header = self.ROI_tableWidget.horizontalHeader()
#            header.setSectionResizeMode(QHeaderView.ResizeToContents)       
#            header.setSectionResizeMode(0, QHeaderView.Stretch)
#            
#            header_vert = self.ROI_tableWidget.verticalHeader()
#            header_vert.setSectionResizeMode(QHeaderView.ResizeToContents)
#            header_vert.setSectionResizeMode(0, QHeaderView.Stretch)
#            header_vert.setSectionResizeMode(1, QHeaderView.Stretch)
#            
             #set exemplary item 
            self.ROI = QLabel()
            self.ROI.setPixmap(QPixmap('icons/dummy_image.png').scaledToWidth(self.pixmap_width))
#            self.ROI_tableWidget.setItem(0,0,
#                                         QTableWidgetItem(QIcon(QPixmap('icons/dummy_image.png')), 'meee'))#.scaledToWidth(self.pixmap_width)),
#                                                   #       'meeee')           
            self.fig_ROI, self.ax_ROI = plt.subplots(1,1)
            self.ax_ROI.axis('off')
            self.canvas_ROI = FigureCanvas(self.fig_ROI)            
            
            #dict for ROIs 
            #save ROI names and corresponding OHWs!
            self.ROI_Management = {}
            self.ROIManagement_title = QLabel('Currently available ROIs:')
            self.ROIManagement_title.setFont(QFont("Times",weight=QFont.Bold))
        
            self.tabROIs.layout = QGridLayout(self)
            self.tabROIs.layout.setSpacing(25)
            self.tabROIs.layout.addWidget(info_ROI,                     0,0)
            self.tabROIs.layout.addWidget(self.button_selectROI,        1,0)
            self.tabROIs.layout.addWidget(self.ROIManagement_title,     2,0)
            self.tabROIs.layout.addWidget(QLineEdit('Example ROI'),     3,0)
            self.tabROIs.layout.addWidget(self.ROI,                     3,1)
            self.tabROIs.setLayout(self.tabROIs.layout)
            
########### fill the second tab ##################
            info_measurement = QTextEdit()
            info_measurement.setText('In this tab you set the settings for the block-matching algorithm and perform the calculation of the motion vectors. You can also export the motion vectors.')
            info_measurement.setReadOnly(True)
            info_measurement.setMaximumHeight(40)
            info_measurement.setMaximumWidth(800)
            info_measurement.setStyleSheet("background-color: LightSkyBlue")
            
            label_measure = QLabel('Measure velocity (block-matching): ')
            label_settings = QLabel('Settings: ')
            label_measure.setFont(QFont("Times",weight=QFont.Bold))
            label_settings.setFont(QFont("Times",weight=QFont.Bold))
            label_addOptions = QLabel('Additional options: ')
            label_addOptions.setFont(QFont("Times",weight=QFont.Bold))
            
            #user settings  
            label_blockwidth =  QLabel('Blockwidth (in pixels):')
            label_delay =       QLabel('Delay (in frames): ')
            label_maxShift =    QLabel('Maximum shift p (in pixels): ')
            self.spinbox_blockwidth = QSpinBox()
            self.spinbox_delay = QSpinBox()
            self.spinbox_maxShift = QSpinBox()
            
            #settings for the spinboxes
            self.spinbox_blockwidth.setRange(2,128)
            self.spinbox_blockwidth.setSingleStep(2)
            self.spinbox_blockwidth.setSuffix(' pixels')
            self.spinbox_blockwidth.setValue(int(self.config['DEFAULT VALUES']['blockwidth']))
            self.spinbox_delay.setRange(1,10)
            self.spinbox_delay.setSuffix(' frames')
            self.spinbox_delay.setSingleStep(1)
            self.spinbox_delay.setValue(int(self.config['DEFAULT VALUES']['delay']))
            self.spinbox_maxShift.setSuffix(' pixels')
            self.spinbox_maxShift.setValue(int(self.config['DEFAULT VALUES']['maxShift']))

            #if value of box is changed
            self.spinbox_blockwidth.valueChanged.connect(self.changeBlockwidth)
            self.spinbox_delay.valueChanged.connect(self.changeDelay)
            self.spinbox_maxShift.valueChanged.connect(self.changeMaxShift)
            
            self.check_scaling = QCheckBox('Scale the image to 1024 x 1024 pixels during calculation')
            #default values:
            self.scaling_status = True
            self.factor_scaling = 1024  #todo: remove factor_scaling as class variable here
            self.check_scaling.setChecked(self.scaling_status)
            self.check_scaling.stateChanged.connect(self.changeStatus)
            
            #enable/disable filtering
            self.check_filter = QCheckBox("Filter motion vectors during calculation")
            self.filter_status = True
            
            self.check_filter.setChecked(self.filter_status)
            self.check_filter.stateChanged.connect(self.changeStatus)
            
            self.button_getMVs = QPushButton('Get motion vectors')
            self.button_getMVs.resize(self.button_getMVs.sizeHint())
            self.button_getMVs.clicked.connect(self.on_getMVs)
            self.button_getMVs.setEnabled(False)
            
            self.button_save_motionVectors = QPushButton('Save motion vectors')
            self.button_save_motionVectors.resize(self.button_save_motionVectors.sizeHint())
            self.button_save_motionVectors.clicked.connect(self.on_saveMVs)
            self.button_save_motionVectors.setEnabled(False)
            
            #succed-button
            self.button_succeed_MVs = QPushButton('Move on to the next tab if this button is green!')
            self.button_succeed_MVs.setStyleSheet("background-color: IndianRed")
            
            #progressbar in tab2    
            self.progressbar_MVs = QProgressBar(self)
            self.progressbar_MVs.setMaximum(100)
            self.progressbar_MVs.setValue(0)
            
            self.tab2.layout = QGridLayout(self)
            self.tab2.layout.setSpacing(25)
            self.tab2.layout.addWidget(info_measurement, 0,0)
            self.tab2.layout.addWidget(label_settings, 1,0)
            self.tab2.layout.addWidget(label_blockwidth,2,0)
            self.tab2.layout.addWidget(self.spinbox_blockwidth,2,1)
            self.tab2.layout.addWidget(label_delay,3,0)
            self.tab2.layout.addWidget(self.spinbox_delay, 3,1)
            self.tab2.layout.addWidget(label_maxShift,4,0)
            self.tab2.layout.addWidget(self.spinbox_maxShift,4,1)
            self.tab2.layout.addWidget(label_addOptions, 5,0)
            self.tab2.layout.addWidget(self.check_scaling, 6,0)
            self.tab2.layout.addWidget(self.check_filter, 7,0 )
            self.tab2.layout.addWidget(label_measure, 8,0)
            self.tab2.layout.addWidget(self.button_getMVs, 9,0)
            self.tab2.layout.addWidget(self.progressbar_MVs, 10,0)
            self.tab2.layout.addWidget(self.button_succeed_MVs, 11,0)
            self.tab2.layout.addWidget(self.button_save_motionVectors, 12,0)
            
            self.tab2.setLayout(self.tab2.layout)
            
########### fill the third tab ##################
            info_analysisBasic = QTextEdit()
            info_analysisBasic.setText('In this tab you can plot the motion as an EKG and calculate statistics based on the found peaks. Change the parameters manually to optimize the peak detection. You can save the graphs and export the peaks.')
            info_analysisBasic.setReadOnly(True)
            info_analysisBasic.setMaximumHeight(40)
            info_analysisBasic.setMaximumWidth(800)
            info_analysisBasic.setStyleSheet("background-color: LightSkyBlue")
            
            #create a label for choosing the ROI
            label_ekg_choose_ROI = QLabel('Choose the ROI to be displayed: ')
            label_ekg_choose_ROI.setFont(QFont("Times",weight=QFont.Bold))
            
            #create a drop-down menu for choosing the ROI to be displayed
            self.ekg_combobox = QComboBox()
            self.ekg_combobox.addItem('Full image')    
            #self.ekg_combobox.activated[str].connect(self.on_chooseROI)
            self.ekg_combobox.currentIndexChanged[int].connect(self.on_chooseROI)
            
            label_results = QLabel('Results: ')
            label_results.setFont(QFont("Times",weight=QFont.Bold))

            self.fig_kinetics, self.ax_kinetics = plt.subplots(1,1)
            self.fig_kinetics.set_size_inches(16,12)
            self.canvas_kinetics = FigureCanvas(self.fig_kinetics)           
            
            #spinboxes to choose for manual detection
            label_ratio = QLabel('Ratio of peaks: ')           
            self.spinbox_ratio = QDoubleSpinBox()
            self.spinbox_ratio.setRange(0.01, 0.90)
            self.spinbox_ratio.setSingleStep(0.01)
            self.spinbox_ratio.setValue(0.05)           
            
            label_neighbours = QLabel('Number of neighbouring values for evaluation:') 
            self.spinbox_neighbours = QSpinBox()    
            self.spinbox_neighbours.setRange(2,10)
            self.spinbox_neighbours.setSingleStep(2)
            self.spinbox_neighbours.setValue(4)
            
            #create labels for the statistics
            label_max_contraction = QLabel('Detected maximum contraction: ')
            label_max_relaxation = QLabel('Detected maximum relaxation: ')
            label_time_contraction = QLabel('Mean contraction interval: ')
            label_time_relaxation = QLabel('Mean relaxation interval: ')
            label_time_contr_relax = QLabel('Mean interval between contraction and relaxation: ')
            label_bpm = QLabel('Heart rate: ')
            
            self.label_max_contraction_result = QLabel('... needs to be calculated ...')            
            self.label_max_relaxation_result = QLabel('... needs to be calculated ...')
            self.label_time_contraction_result = QLabel('... needs to be calculated ...')
            self.label_time_relaxation_result = QLabel('... needs to be calculated ...')
            self.label_time_contr_relax_result = QLabel('... needs to be calculated ...')
            self.label_bpm_result = QLabel('... needs to be calculated ...')
            
            label_furtherAnalysis = QLabel('Further options:')
            label_furtherAnalysis.setFont(QFont("Times",weight=QFont.Bold))
            
            label_evaluate = QLabel('Start evaluation')
            label_evaluate.setFont(QFont("Times",weight=QFont.Bold))
            
            self.button_detectPeaks = QPushButton('Start peak detection')
            self.button_saveKinetics = QPushButton('Save current EKG graph as ...')
            self.button_export_peaks = QPushButton('Save raw and analyzed peaks ')
            self.button_export_ekg_csv = QPushButton('Save EKG as excel file (.xlsx)')
            self.button_export_statistics = QPushButton('Save statistical analysis ')
            
            self.button_detectPeaks.resize(self.button_detectPeaks.sizeHint())
            self.button_saveKinetics.resize(self.button_saveKinetics.sizeHint())
            self.button_export_peaks.resize(self.button_export_peaks.sizeHint())
            self.button_export_ekg_csv.resize(self.button_export_ekg_csv.sizeHint())
            self.button_export_statistics.resize(self.button_export_statistics.sizeHint())
            self.button_saveKinetics.setEnabled(False)
            self.button_export_peaks.setEnabled(False)
            self.button_export_ekg_csv.setEnabled(False)
            self.button_export_statistics.setEnabled(False)
            self.button_detectPeaks.setEnabled(False)
            
            self.button_detectPeaks.clicked.connect(self.on_detectPeaks)            
            self.button_saveKinetics.clicked.connect(self.on_saveKinetics)
            self.button_export_peaks.clicked.connect(self.on_exportPeaks)
            self.button_export_ekg_csv.clicked.connect(self.on_exportEKG_CSV)
            self.button_export_statistics.clicked.connect(self.on_exportStatistics)
                      
            self.tab3.layout = QGridLayout(self)
            self.tab3.layout.addWidget(info_analysisBasic,      0,0)
            self.tab3.layout.addWidget(label_ekg_choose_ROI,    1,0)
            self.tab3.layout.addWidget(self.ekg_combobox,       2,0)
            self.tab3.layout.addWidget(label_results,           3,0)
            self.tab3.layout.addWidget(label_ratio,             4,0)
            self.tab3.layout.addWidget(self.spinbox_ratio,      4,1)
            self.tab3.layout.addWidget(label_neighbours,        5,0)
            self.tab3.layout.addWidget(self.spinbox_neighbours, 5,1)
            self.tab3.layout.addWidget(self.button_detectPeaks, 6,0)
            self.tab3.layout.addWidget(self.canvas_kinetics,    7,0)
            self.tab3.layout.addWidget(label_max_contraction,   8,0)
            self.tab3.layout.addWidget(self.label_max_contraction_result, 8,1)
            self.tab3.layout.addWidget(label_max_relaxation,    9,0)
            self.tab3.layout.addWidget(self.label_max_relaxation_result, 9,1)
            self.tab3.layout.addWidget(label_time_contraction,  10,0)
            self.tab3.layout.addWidget(self.label_time_contraction_result, 10,1)
            self.tab3.layout.addWidget(label_time_relaxation,   11,0)            
            self.tab3.layout.addWidget(self.label_time_relaxation_result, 11,1)
            self.tab3.layout.addWidget(label_time_contr_relax,  12,0)
            self.tab3.layout.addWidget(self.label_time_contr_relax_result, 12,1)
            self.tab3.layout.addWidget(label_bpm,               13,0)
            self.tab3.layout.addWidget(self.label_bpm_result,   13,1)
            self.tab3.layout.addWidget(label_furtherAnalysis,   14,0)
            self.tab3.layout.addWidget(self.button_saveKinetics,15,0)
            self.tab3.layout.addWidget(self.button_export_peaks,16,0)
            self.tab3.layout.addWidget(self.button_export_ekg_csv, 17,0)
            self.tab3.layout.addWidget(self.button_export_statistics, 18,0)
            self.tab3.setLayout(self.tab3.layout)

########### fill the fourth tab ##################
            info_heat_quiver = QTextEdit()
            info_heat_quiver.setText('In this tab you can calculate heatmaps and quiverplots and use the slider to look at the different frames.')
            info_heat_quiver.setReadOnly(True)
            info_heat_quiver.setMaximumHeight(40)
            info_heat_quiver.setMaximumWidth(800)
            info_heat_quiver.setStyleSheet("background-color: LightSkyBlue")
 
            #create a label for choosing the ROI
            label_advanced_choose_ROI = QLabel('Choose the ROI to be displayed: ')
            label_advanced_choose_ROI.setFont(QFont("Times",weight=QFont.Bold))
            
            #create a drop-down menu for choosing the ROI to be displayed
            self.advanced_combobox = QComboBox()
            self.advanced_combobox.addItem('Full image')    
#            self.advanced_combobox.activated[str].connect(self.on_chooseROI)
            self.advanced_combobox.currentIndexChanged[int].connect(self.on_chooseROI)

            
            label_heatmaps = QLabel('Heatmaps')
            label_heatmaps.setFont(QFont("Times",weight=QFont.Bold))
            
            label_quivers = QLabel('Quivers')
            label_quivers.setFont(QFont("Times",weight=QFont.Bold))

            #Button for starting the creation of heatmaps and heatmap video
            self.button_heatmaps_video = QPushButton('Export Heatmap Video')
            self.button_heatmaps_video.resize(self.button_heatmaps_video.sizeHint())
            self.button_heatmaps_video.clicked.connect(self.on_saveHeatmapvideo)            
            #is disabled, enabled after successful calculation of MotionVectors
            self.button_heatmaps_video.setEnabled(False)
                          
            #create  a slider to switch manually between the heatmaps
            self.label_slider_info = QLabel('Use the slider to switch between heatmaps of the different frames: ')
            self.slider_heatmaps = QSlider(Qt.Horizontal)
            self.slider_heatmaps.setMinimum(0)
            self.slider_heatmaps.setMaximum(100)
            self.slider_heatmaps.setValue(0)
            self.slider_heatmaps.setEnabled(False)
            self.slider_heatmaps.setTickPosition(QSlider.TicksBelow)
            self.slider_heatmaps.setTickInterval(5)
            self.slider_heatmaps.valueChanged.connect(self.slider_heatmaps_valueChanged)
            
            #create buttons for saving a specific heatmap or quiverplot frame
            self.button_save_Heatmap = QPushButton('Save this heatmap frame to image file...')
            self.button_save_Heatmap.resize(self.button_save_Heatmap.sizeHint())
            self.button_save_Heatmap.clicked.connect(self.on_saveHeatmap)      
            #is disabled, enabled after successful calculation of Heatmaps
            self.button_save_Heatmap.setEnabled(False)
            
            self.button_save_Quiver = QPushButton('Save this quiver frame to image file...')
            self.button_save_Quiver.resize(self.button_save_Quiver.sizeHint())
            self.button_save_Quiver.clicked.connect(self.on_saveQuiver)            
            #is disabled, enabled after successful calculation of QuiverPlots
            self.button_save_Quiver.setEnabled(False)
            
            #create a second slider for the quiver plots
            self.label_slider_quivers = QLabel('Use the slider to switch between quiverplots of the different frames: ')
            self.slider_quiver = QSlider(Qt.Horizontal)
            self.slider_quiver.setMinimum(0)
            self.slider_quiver.setMaximum(100)
            self.slider_quiver.setValue(0)
            self.slider_quiver.setEnabled(False)
            self.slider_quiver.setTickPosition(QSlider.TicksBelow)
            self.slider_quiver.valueChanged.connect(self.slider_quiver_valueChanged)
            self.slider_quiver.setTickPosition(QSlider.TicksBelow)
            self.slider_quiver.setTickInterval(5)
            
            #display the chosen heatmap
            self.label_heatmap_result = QLabel('Heatmap result:')
            #display the chosen heatmap
            self.label_heatmap_result = QLabel('Heatmap result:')
            self.image_heatmap = QLabel()
            self.image_heatmap.setPixmap(QPixmap('icons/dummy_heatmap.png').scaledToWidth(self.pixmap_width))
            
            # display figures for heatmaps in Canvas
            self.fig_heatmaps, self.ax_heatmaps = plt.subplots(1,1)
            self.fig_heatmaps.set_size_inches(16,12)
            self.ax_heatmaps.axis('off')
            
            self.canvas_heatmap = FigureCanvas(self.fig_heatmaps)
            
            #button for changing the quiver export settings
            self.button_change_quiverSettings = QPushButton('Change quiver export settings')
            self.button_change_quiverSettings.resize(self.button_change_quiverSettings.sizeHint())
            self.button_change_quiverSettings.clicked.connect(self.on_change_quiverSettings)
            
            #Button for starting the creation of quiver plots and quiver video
            self.button_quivers_video = QPushButton('Export quiver video')
            self.button_quivers_video.resize(self.button_quivers_video.sizeHint())
            self.button_quivers_video.clicked.connect(self.on_saveQuivervideo)
            #is disabled, enabled after successful calculation of MotionVectors
            self.button_quivers_video.setEnabled(False)
                     
             #display the chosen quiver plot
            self.label_quiver_result = QLabel('Quiver result: ')
            self.label_quiver_result = QLabel('Quiver result: ')
            self.image_quiver = QLabel()
            self.image_quiver.setPixmap(QPixmap('icons/dummy_quiver.png').scaledToWidth(self.pixmap_width))
 
            # display figures for quivers in Canvas
            self.fig_quivers, self.ax_quivers = plt.subplots(1,1)
            self.fig_quivers.set_size_inches(16,12)
            self.ax_quivers.axis('off')
            
            self.canvas_quivers = FigureCanvas(self.fig_quivers)
                  
            #succed-button
            self.button_succeed_heatmaps = QPushButton('Heatmap-video creation was successful')
            self.button_succeed_heatmaps.setStyleSheet("background-color: IndianRed")
            self.button_succeed_quivers = QPushButton('Quiver-video creation was successful')
            self.button_succeed_quivers.setStyleSheet("background-color: IndianRed")

            #progressbar for heatmaps
            self.progressbar_heatmaps = QProgressBar(self)
            self.progressbar_heatmaps.setValue(0)
            
            #progressbar for quivers
            self.progressbar_quivers = QProgressBar(self)
            self.progressbar_quivers.setValue(0)
        
            #define layout
            colHeatmap = 0
            colQuiver = 2
            self.tab4.layout = QGridLayout()
            self.tab4.layout.addWidget(info_heat_quiver, 0,0)
            self.tab4.layout.addWidget(label_advanced_choose_ROI,   1,  0)
            self.tab4.layout.addWidget(self.advanced_combobox,      2,  0)
            self.tab4.layout.addWidget(label_heatmaps,              3,  colHeatmap)
            self.tab4.layout.addWidget(label_quivers,               3,  colQuiver)
            self.tab4.layout.addWidget(self.button_change_quiverSettings, 2, colQuiver)
            self.tab4.layout.addWidget(self.button_heatmaps_video,  4,  colHeatmap)
            self.tab4.layout.addWidget(self.button_quivers_video,   4,  colQuiver)
            self.tab4.layout.addWidget(self.progressbar_heatmaps,   5,  colHeatmap)
            self.tab4.layout.addWidget(self.progressbar_quivers,    5,  colQuiver)
            self.tab4.layout.addWidget(self.button_succeed_heatmaps,6,  colHeatmap)
            self.tab4.layout.addWidget(self.button_succeed_quivers, 6,  colQuiver)
            self.tab4.layout.addWidget(self.label_heatmap_result,   7,  colHeatmap)
            self.tab4.layout.addWidget(self.label_quiver_result,    7,  colQuiver)
            self.tab4.layout.addWidget(self.image_heatmap,          8,  colHeatmap)
            self.tab4.layout.addWidget(self.image_quiver,           8,  colQuiver)
            self.tab4.layout.addWidget(self.button_save_Heatmap,    11,  colHeatmap)
            self.tab4.layout.addWidget(self.button_save_Quiver,     11,  colQuiver)
            
            #create sliders for heatmaps and quivers
            self.tab4.layout.addWidget(self.label_slider_info,      9,0)
            self.tab4.layout.addWidget(self.label_slider_quivers,   9,2)
            self.tab4.layout.addWidget(self.slider_heatmaps,        10,0)
            self.tab4.layout.addWidget(self.slider_quiver,          10,2)

            self.tab4.layout.setColumnStretch(0,1)
            self.tab4.layout.setColumnStretch(1,1)
            self.tab4.layout.setColumnStretch(2,1)
            self.tab4.layout.setHorizontalSpacing(20)
            self.tab4.setLayout(self.tab4.layout)
       

########### fill the fifth tab ##################
            info_timeAveraged = QTextEdit()
            info_timeAveraged.setText('In this tab you can save the time averaged motion: absolute contractility and contractility in x- and y-direction.')
            info_timeAveraged.setReadOnly(True)
            info_timeAveraged.setMaximumHeight(40)
            info_timeAveraged.setMaximumWidth(800)
            info_timeAveraged.setStyleSheet("background-color: LightSkyBlue")
            
            label_time_avg_motion = QLabel('Motion averaged over time')
            label_time_avg_motion.setFont(QFont("Times",weight=QFont.Bold))
         
            #create a label for choosing the ROI
            label_timeavg_chooseROI = QLabel('Choose the ROI to be displayed: ')
            label_timeavg_chooseROI.setFont(QFont("Times",weight=QFont.Bold))
            
            #create a drop-down menu for choosing the ROI to be displayed
            self.timeavg_combobox = QComboBox()
            self.timeavg_combobox.addItem('Full image')    
            self.timeavg_combobox.currentIndexChanged[int].connect(self.on_chooseROI)
            
            #display the calculated time averaged motion
            self.label_time_averaged_result_total = QLabel('Absolute contractility:')
            self.label_time_averaged_result_x = QLabel('Contractility in x-direction:')
            self.label_time_averaged_result_y = QLabel('Contractility in y-direction:')
            self.image_motion_total = QLabel()
            self.image_motion_x  = QLabel()
            self.image_motion_y = QLabel()
            
            self.image_motion_total.setPixmap(QPixmap('icons/dummy_TimeAveraged_totalMotion.png').scaledToWidth(self.pixmap_width))
            self.image_motion_x.setPixmap(QPixmap('icons/dummy_TimeAveraged_x.png').scaledToWidth(self.pixmap_width))
            self.image_motion_y.setPixmap(QPixmap('icons/dummy_TimeAveraged_y.png').scaledToWidth(self.pixmap_width))
            
            # create mpl figurecanvas for display of averaged motion
            self.fig_motion_total, self.ax_motion_total = plt.subplots(1,1)
            self.fig_motion_x, self.ax_motion_x = plt.subplots(1,1)
            self.fig_motion_y, self.ax_motion_y = plt.subplots(1,1)
            
            self.fig_motion_total.set_size_inches(16,12)
            self.fig_motion_x.set_size_inches(16,12)
            self.fig_motion_y.set_size_inches(16,12)
            
            self.ax_motion_total.axis('off')
            self.ax_motion_x.axis('off')
            self.ax_motion_y.axis('off')
            
            self.canvas_motion_total = FigureCanvas(self.fig_motion_total)
            self.canvas_motion_x = FigureCanvas(self.fig_motion_x)
            self.canvas_motion_y = FigureCanvas(self.fig_motion_y)
            
            #button for saving plots
            label_save_motion = QLabel('Save the plots as: ')
            self.button_save_timeMotion = QPushButton('Click for saving')
            self.button_save_timeMotion.resize(self.button_save_timeMotion.sizeHint())
            self.button_save_timeMotion.clicked.connect(self.on_saveTimeAveragedMotion)
            self.button_save_timeMotion.setEnabled(False)
            
            #combobox for file extensions
            self.combo_avgExt = QComboBox(self)
            self.combo_avgExt.addItem('.png')
            self.combo_avgExt.addItem('.jpeg')
            self.combo_avgExt.addItem('.tiff')
            self.combo_avgExt.addItem('.svg')
            self.combo_avgExt.addItem('.eps')

            #succed-button
            self.button_succeed_motion = QPushButton('Plotting of time averaged motion was successful')
            self.button_succeed_motion.setStyleSheet("background-color: IndianRed")
 
            #define layout
            self.tab5.layout = QGridLayout()
            self.tab5.layout.addWidget(info_timeAveraged,                       0,0)
            self.tab5.layout.addWidget(label_timeavg_chooseROI,                 1,0)
            self.tab5.layout.addWidget(self.timeavg_combobox,                   2,0)
            self.tab5.layout.addWidget(label_time_avg_motion,                   3,0)
            self.tab5.layout.addWidget(self.button_succeed_motion,              4,0)
            self.tab5.layout.addWidget(self.label_time_averaged_result_total,   5,0)
            self.tab5.layout.addWidget(self.image_motion_total,                 6,0)
            self.tab5.layout.addWidget(self.label_time_averaged_result_x,       7,0)
            self.tab5.layout.addWidget(self.image_motion_x,                     8,0)
            self.tab5.layout.addWidget(self.label_time_averaged_result_y,       7,1)
            self.tab5.layout.addWidget(self.image_motion_y,                     8,1)

            self.tab5.layout.addWidget(label_save_motion,                       9,0)
            self.tab5.layout.addWidget(self.combo_avgExt,                       9,1)
            self.tab5.layout.addWidget(self.button_save_timeMotion, 10,0)

            self.tab5.layout.setHorizontalSpacing(20)
            self.tab5.setLayout(self.tab5.layout)
           

########### fill the sixth tab ##################
            info_batch = QTextEdit()
            info_batch.setText('In this tab you can automate the analysis of multiple folders without further interaction during the processing.')
            info_batch.setReadOnly(True)
            info_batch.setMaximumHeight(40)
            info_batch.setMaximumWidth(800)
            info_batch.setTextBackgroundColor(color_for_info)
            info_batch.setStyleSheet("background-color: LightSkyBlue")
            
            #select the folders
            self.batch_folders = []
            self.info_batchfolders = QLabel('Currently selected folders for automated analysis:')
            self.info_batchfolders.setFont(QFont("Times",weight=QFont.Bold))
            self.names_batchfolders = QTextEdit()
            
            #button for adding folders
            self.button_addBatchFolder = QPushButton('Add folders...')
            self.button_addBatchFolder.resize(self.button_addBatchFolder.sizeHint())
            self.button_addBatchFolder.clicked.connect(self.on_addBatchFolder)
            
            #dropdown for choosing folder to be removed
            self.combo_removefolder = QComboBox(self)
            
            #button for removing folders
            self.button_removeBatchFolder = QPushButton('... will be removed from folders.')
            self.button_removeBatchFolder.resize(self.button_removeBatchFolder.sizeHint())
            self.button_removeBatchFolder.clicked.connect(self.removeBatchFolder)
            self.button_removeBatchFolder.setEnabled(False)
            
            #options: needed parameters
            label_batch_parameters = QLabel('Settings during calculation of motion vectors:')
            label_batch_parameters.setFont(QFont("Times",weight=QFont.Bold))
            label_batch_blockwidth = QLabel('Blockwidth (in pixels)')
            label_batch_delay = QLabel('Delay (in frames)')
            label_batch_maxShift = QLabel('Maximum shift p (in pixels)')
            
            #spinboxes incl settings
            self.batch_spinbox_blockwidth  = QSpinBox()
            self.batch_spinbox_delay = QSpinBox()
            self.batch_spinbox_maxShift = QSpinBox()
            
            self.batch_spinbox_blockwidth.setRange(2,128)
            self.batch_spinbox_blockwidth.setSingleStep(2)
            self.batch_spinbox_blockwidth.setSuffix(' pixels')
            self.batch_spinbox_blockwidth.setValue(16)
            self.batch_spinbox_delay.setRange(2,10)
            self.batch_spinbox_delay.setSuffix(' frames')
            self.batch_spinbox_delay.setSingleStep(1)
            self.batch_spinbox_delay.setValue(2)
            self.batch_spinbox_maxShift.setSuffix(' pixels')
            self.batch_spinbox_maxShift.setValue(7)

            #if value of box is changed
            self.batch_spinbox_blockwidth.valueChanged.connect(self.changeBatchSettings)
            self.batch_spinbox_delay.valueChanged.connect(self.changeBatchSettings)
            self.batch_spinbox_maxShift.valueChanged.connect(self.changeBatchSettings)
            
            #options for automated analysis
            label_batchOptions = QLabel('Choose options for automated analysis of the chosen folders:')
            label_batchOptions.setFont(QFont("Times",weight=QFont.Bold))
            
            self.batch_checkFilter = QCheckBox("Filter motion vectors during calculation")
            self.batch_checkHeatmaps = QCheckBox("Create heatmap video")
            self.batch_checkQuivers = QCheckBox("Create quiver plot video")
            self.batch_checkTimeAveraged = QCheckBox("Create plots for time averaged motion")
            self.batch_checkSaveMotionVectors = QCheckBox("Save the generated motion vectors")
            self.batch_checkScaling = QCheckBox("Scale the image to 1024 x 1024 pixels during calculation")
            
            #create a variable for the checkbox status
            self.batch_filter_status = True
            self.batch_heatmap_status = True
            self.batch_quiver_status = True
            self.batch_timeAver_status = True
            self.batch_scaling_status = True
            self.batch_saveMotionVectors_status = False
            
            self.batch_checkFilter.setChecked(self.batch_filter_status)
            self.batch_checkSaveMotionVectors.setChecked(self.batch_saveMotionVectors_status)
            self.batch_checkHeatmaps.setChecked(self.batch_heatmap_status)
            self.batch_checkQuivers.setChecked(self.batch_quiver_status)
            self.batch_checkTimeAveraged.setChecked(self.batch_timeAver_status)
            self.batch_checkScaling.setChecked(self.batch_scaling_status)
            
            self.batch_checkFilter.stateChanged.connect(self.changeStatus)
            self.batch_checkHeatmaps.stateChanged.connect(self.changeStatus)
            self.batch_checkQuivers.stateChanged.connect(self.changeStatus)
            self.batch_checkSaveMotionVectors.stateChanged.connect(self.changeStatus)
            self.batch_checkScaling.stateChanged.connect(self.changeStatus)
            
            #button for starting the analysis
            self.button_batch_startAnalysis = QPushButton('Start the automated analysis of the chosen folders...')
            self.button_batch_startAnalysis.resize(self.button_batch_startAnalysis.sizeHint())
            self.button_batch_startAnalysis.clicked.connect(self.on_startBatchAnalysis)
            self.button_batch_startAnalysis.setEnabled(False)
            
            #button for aborting the analysis
            self.button_batch_stopAnalysis = QPushButton('Stop onging analysis')
            self.button_batch_stopAnalysis.resize(self.button_batch_stopAnalysis.sizeHint())
            self.button_batch_stopAnalysis.clicked.connect(self.on_stopBatchAnalysis)
            self.button_batch_stopAnalysis.setEnabled(False)
            
            #label to display current results folder
            self.label_resultsfolder_batch = QLabel('Current results folder: ')
            self.label_resultsfolder_batch.setFont(QFont("Times",weight=QFont.Bold))
          
            #button for changing the results folder
            self.button_change_resultsfolder_batch = QPushButton('Change results folder ')
            self.button_change_resultsfolder_batch.resize(self.button_change_resultsfolder_batch.sizeHint())
            self.button_change_resultsfolder_batch.clicked.connect(self.on_changeResultsfolder)
            self.button_change_resultsfolder_batch.setEnabled(True)
            
            #create a progressbar    
            self.progressbar_batch = QProgressBar(self)
            self.progressbar_batch.setMaximum(100)  
            self.progressbar_batch.setValue(0)
            
            #Layout management
            self.tab6.layout = QGridLayout(self)
            #self.tab6.layout.setSpacing(25)
            self.tab6.layout.addWidget(info_batch,                      1,0)
            self.tab6.layout.addWidget(self.info_batchfolders,          2,0)
            self.tab6.layout.addWidget(self.names_batchfolders,         3,0)
            self.tab6.layout.addWidget(self.button_addBatchFolder,      3,1)
            self.tab6.layout.addWidget(self.combo_removefolder,         4,0)
            self.tab6.layout.addWidget(self.button_removeBatchFolder,   4,1)
            self.tab6.layout.addWidget(label_batch_parameters,          5,0)
            self.tab6.layout.addWidget(label_batch_blockwidth,          6,0)
            self.tab6.layout.addWidget(self.batch_spinbox_blockwidth,   6,1)
            self.tab6.layout.addWidget(label_batch_delay,               7,0)
            self.tab6.layout.addWidget(self.batch_spinbox_delay,        7,1)
            self.tab6.layout.addWidget(label_batch_maxShift,            8,0)
            self.tab6.layout.addWidget(self.batch_spinbox_maxShift,     8,1)            
            self.tab6.layout.addWidget(label_batchOptions,              9,0)
            self.tab6.layout.addWidget(self.batch_checkScaling,         10,0)
            self.tab6.layout.addWidget(self.batch_checkFilter,          11,0)
            self.tab6.layout.addWidget(self.batch_checkHeatmaps,        12,0)
            self.tab6.layout.addWidget(self.batch_checkQuivers,         13,0)
            self.tab6.layout.addWidget(self.label_resultsfolder_batch,  14,0)
            self.tab6.layout.addWidget(self.button_change_resultsfolder_batch, 15,0)
            self.tab6.layout.addWidget(self.button_batch_startAnalysis, 16,0)
            self.tab6.layout.addWidget(self.progressbar_batch,          17,0)
            self.tab6.layout.addWidget(self.button_batch_stopAnalysis,  17,1)
            
            self.tab6.setLayout(self.tab6.layout)

###############################################################################
        def change_ROI_names(self, ROI_nr):
            """ emitted when name of one of the ROIs is changed by the user in one of the lineedits
            Parameters: 
                ROI_nr      index of the ROI
            """
            #get the new name from the LineEdit which send the signal
            new_name = self.sender().text()
            self.ROI_names[ROI_nr] = new_name
            
            #change the resultsfolder name in the corresponding ROI_OHW
            self.ROI_OHWs[ROI_nr].results_folder = self.OHW.results_folder.joinpath(self.ROI_names[ROI_nr])
            
            #change the items in all the comboboxes, first item is the full image 
            self.ekg_combobox.setItemText(ROI_nr+1,         new_name)
            self.advanced_combobox.setItemText(ROI_nr+1,    new_name)
            self.timeavg_combobox.setItemText(ROI_nr+1,     new_name)
            
        def on_chooseROI(self, current_index):
            """ choose a ROI for displaying and analyzing results in beating_kinetics, heatmaps and quiverplots
            """
            if current_index == 0:
                self.current_dataset = self.OHW
            #self.current_ROI is specified as ROI_nr, index in self.ROI_OHWs!
            else:
                self.current_ROI_idx = current_index-1
                self.current_dataset = self.ROI_OHWs[self.current_ROI_idx]
                print(self.ROI_names[self.current_ROI_idx])
            
            if self.sender() == self.ekg_combobox:
                self.current_dataset.initialize_calculatedMVs()
                self.initialize_kinetics()
            
            elif self.sender() == self.advanced_combobox:
                self.initialize_MV_graphs()
                self.button_succeed_heatmaps.setStyleSheet("background-color: IndianRed")
                self.button_succeed_quivers.setStyleSheet("background-color: IndianRed")
                self.progressbar_heatmaps.setValue(0)
                self.progressbar_quivers.setValue(0)
            
            elif self.sender() == self.timeavg_combobox:
                self.initializeTimeAveragedMotion()
                
        def on_selectROI(self):
            """ select a ROI from the first image of the rawImageStack, calculation of MVs will be performed on ROI only after this 
            """
            widget_height = self.frameSize().height()
            
            #take the first image of rawImageStack and scale to fit on display
            img = cv2.cvtColor(self.OHW.rawImageStack[0], cv2.COLOR_GRAY2RGB)      
            hpercent = (widget_height / float(img.shape[1]))
            wsize = int((float(img.shape[0]) * float(hpercent)))
            image_scaled = cv2.resize(img, (wsize, widget_height))
            
            #convert to uint8 if needed
            if img.dtype != 'uint8':
                image_norm = image_scaled
                image_norm = cv2.normalize(image_scaled, image_norm, 0, 1, cv2.NORM_MINMAX)*255
                image_scaled = image_norm.astype(np.uint8)
                   
            #open the ROI selection
            r = cv2.selectROI('Press Enter to save the currently selected ROI:', image_scaled, fromCenter=False)
            
            #transform the coordinates back to match the image of original size
            r_transf = [r[idx]/hpercent for idx in range(0,len(r))]
            
            #add the new ROI to the OHWs, the ROI_names
            new_nr = len(self.ROI_names) + 1 
            new_name = 'ROI_{}'.format(new_nr)
            self.ROI_names.append(new_name)
            self.ekg_combobox.addItem(new_name)
            self.advanced_combobox.addItem(new_name) 
            self.timeavg_combobox.addItem(new_name)
            
            #create new OHW
            self.manageROIs(r_transf)
            cv2.destroyAllWindows()
            
            self.check_scaling.setEnabled(False)
            self.scaling_status = False
            self.check_scaling.setEnabled(False)
            self.scaling_status = False
        
        def manageROIs(self, r):
            """
            Parameters:     
                r       coordinates returned by cv2.selectROI
            """
            self.ROI_coordinates.append(r)
          
            self.ROI_OHWs = []
            for nr_ROI in range(0, len(self.ROI_coordinates)):
                #create new OHW object for each ROI
                current_ROI_OHW = copy.deepcopy(self.OHW)
                #create new subfolder for storing ROI analysis
                current_ROI_OHW.results_folder = self.OHW.results_folder.joinpath(self.ROI_names[nr_ROI])
                #mark as ROI_OHW
                current_ROI_OHW.isROI_OHW = True
                current_ROI_OHW.createROIImageStack(self.ROI_coordinates[nr_ROI])
                                
                #display ROI in tab
                current_row = 3 + nr_ROI#len(self.ROI_coordinates)
                self.display_ROI(current_ROI_OHW.ROIImageStack[0], nr_ROI, current_row)
            
                #add OHW to list of all ROI OHWs
                self.ROI_OHWs.append(current_ROI_OHW)
    
            
        def changeBatchSettings(self):
            if self.sender() == self.batch_spinbox_blockwidth:
                self.blockwidth_batch = self.batch_spinbox_blockwidth.value()
                return self.batch_spinbox_blockwidth.value()
            
            elif self.sender() == self.batch_spinbox_delay:
                self.delay_batch = self.batch_spinbox_delay.value()
                return self.batch_spinbox_delay.value()
            
            elif self.sender() == self.batch_spinbox_maxShift:
                self.maxshift_batch = self.batch_spinbox_maxShift.value()
                return self.batch_spinbox_maxShift.value()
            
        def on_startBatchAnalysis(self):
            # get current settings from checkboxes and spinboxes
            self.blockwidth_batch = self.batch_spinbox_blockwidth.value()
            self.delay_batch = self.batch_spinbox_delay.value()
            self.maxShift_batch = self.batch_spinbox_maxShift.value()
            self.batch_factor_scaling = self.batch_checkScaling.isChecked()
            self.batch_filter_status = self.batch_checkFilter.isChecked()
            self.batch_heatmap_status = self.batch_checkHeatmaps.isChecked()
            self.batch_quiver_status = self.batch_checkQuivers.isChecked()
            self.batch_scaling_status = self.batch_checkScaling.isChecked()
            
            print('Starting the batch analysis...')
            print('These are your folders: ', self.batch_folders)
            self.button_addBatchFolder.setEnabled(False)
            self.button_removeBatchFolder.setEnabled(False)
            self.button_batch_startAnalysis.setEnabled(False)
            
            if (self.results_folder_batch == ''):
                self.button_batch_startAnalysis.setEnabled(True)
                print('Batch analysis did not start correctly. Start again!')
                return
            
            #enable the stop button
            self.button_batch_stopAnalysis.setEnabled(True)
            
            #create a thread for batch analysis:
            self.thread_batchAnalysis = self.perform_batchAnalysis_thread()
    
            self.thread_batchAnalysis.start()
            self.thread_batchAnalysis.finished.connect(self.finish_batchAnalysis)
            self.thread_batchAnalysis.progressSignal.connect(self.updateProgressBar_batch)
               
        def getMaximumSignals_batch(self):
            #calculates the number of signals to be emitted
            #needed for progressbar during batch analysis
            count = 0
            
            #add 2 signals for reading data and calculating MVs
            count += 2
            
            if self.batch_heatmap_status == True:
                count += 1
            
            if self.batch_quiver_status == True:
                count += 1
            
            #multiply this number by the number of batch folders to be evaluated
            count_tot = count * len(self.batch_folders)
           
            #return this number, needed during threading
            return count_tot 
        
        def perform_batchAnalysis_thread(self):
            current_batch_thread = helpfunctions.turn_function_into_thread(self.perform_batchAnalysis, emit_progSignal=True)
            return current_batch_thread  
 
        def perform_batchAnalysis(self, progressSignal=None):
             #number of signals to be emitted  
            self.maxNumberSignals = self.getMaximumSignals_batch()
            
            #internal counter of current batch signals
            self.count_batch_signals = 0               

            print('Current folders for batch analysis:')
            print(self.batch_folders)
            
            for folder in self.batch_folders:
               
                print('Start Analysis for folder %s:' %folder)
            #### perform analysis for one folder:
                current_ohw = OHW.OHW()
                
                # create a subfolder for the results 
               # save_subfolder = self.results_folder_batch / folder.split('/')[-1]
                save_subfolder = str(pathlib.PureWindowsPath(self.results_folder_batch)) + '/' + folder.split('/')[-1] #+ '/results'
                if not os.path.exists(str(save_subfolder)):
                    os.makedirs(str(save_subfolder))
                current_ohw.results_folder = save_subfolder

                # read data
                current_ohw.read_imagestack(folder)
                print('    ... finished reading data.')
                #progress signal for finishing reading data
                if progressSignal != None:
                    self.count_batch_signals += 1
                    progressSignal.emit(self.count_batch_signals/self.maxNumberSignals)
                    
                # scale data if desired
                if self.batch_scaling_status == True:
                    current_ohw.scale_ImageStack()
                else:
                  #  current_ohw.scale_ImageStack(current_ohw.rawImageStack.shape[0][1])   # too hacky, refactor...
                    if current_ohw.ROIImageStack is not None:
                        current_ohw.scale_ImageStack(current_ohw.ROIImageStack.shape[1], current_ohw.ROIImageStack[2])
                    else: 
                        current_ohw.scale_ImageStack(current_ohw.rawImageStack.shape[1], current_ohw.rawImageStack[2])     
                # calculate MVs
                current_ohw.calculate_MVs(blockwidth=self.blockwidth_batch, delay=self.delay_batch, max_shift=self.maxShift_batch)
                print('    ... finished calculating motion vectors.')
                #progress signal for finishing calc MVs
                if progressSignal != None:
                    self.count_batch_signals += 1
                    progressSignal.emit(self.count_batch_signals/self.maxNumberSignals)
             
                # plot beating kinetics
                current_filename = str(save_subfolder) +'/' + 'beating_kinetics.png'
                current_ohw.plot_beatingKinetics(filename=current_filename, keyword='batch')
                print('    ... finished plotting beating kinetics.')
                
                # create heatmap video if chosen by user
                if self.batch_heatmap_status == True:
                    current_ohw.save_heatmap(subfolder=pathlib.Path(save_subfolder), keyword='batch')
                    print('    ... finished saving heatmaps.')
                #progress signal for finishing heatmap data
                    if progressSignal != None:
                        self.count_batch_signals += 1
                        progressSignal.emit(self.count_batch_signals/self.maxNumberSignals)

                # create quiver video if chosen by user
                if self.batch_quiver_status == True:
                    current_ohw.save_quiver(subfolder=pathlib.Path(save_subfolder), keyword='batch')
                    print('    ... finished saving quivers.')
                    #progress signal for finishing quiver data
                    if progressSignal != None:
                        self.count_batch_signals += 1
                        progressSignal.emit(self.count_batch_signals/self.maxNumberSignals)
        
        def finish_batchAnalysis(self):
            print('Yeah we are done with this thread.')
            self.progressbar_batch.setRange(0,1)
            self.progressbar_batch.setValue(1)
            
            #prepare for another round of analysis:
            self.button_batch_stopAnalysis.setEnabled(False)
            self.button_batch_startAnalysis.setEnabled(True)
            
        def on_stopBatchAnalysis(self):
            self.thread_batchAnalysis.endThread()
            
            #get ready for new analysis:
            self.button_batch_startAnalysis.setEnabled(True)
            self.button_batch_stopAnalysis.setEnabled(False)
            self.button_addBatchFolder.setEnabled(True)
            self.progressbar_batch.setValue(0)
            print('Threads are terminated. Ready for new analysis.')
            
            #display a message for successful stopping
            msg_text = 'Analysis of multiple folders was stopped successfully. You can start again.' # to: ' + text_for_saving
            msg_title = 'Successful'
            msg = QMessageBox.information(self, msg_title, msg_text, QMessageBox.Ok)
            if msg == QMessageBox.Ok:
                pass  
            
        def on_addBatchFolder(self):
            folderDialog = MultipleFoldersByUser.MultipleFoldersDialog()
            chosen_folders = folderDialog.getSelection()
            
            for item in chosen_folders:
                self.batch_folders.append(item)
                self.names_batchfolders.append(item)
                self.combo_removefolder.addItem(item)
            self.button_removeBatchFolder.setEnabled(True)
            
            if len(self.batch_folders) > 0:
                #sobald erster Folder hinzugefügt wird 
                self.button_batch_startAnalysis.setEnabled(True)
                #self.results_folder_batch = os.path.dirname(os.path.dirname(chosen_folders[0]))
                self.results_folder_batch = pathlib.Path(os.path.dirname(chosen_folders[0]))
                
                 #display new results folder
                current_folder = 'Current results folder: ' + str(pathlib.PureWindowsPath(self.results_folder_batch))
                self.label_resultsfolder_batch.setText(current_folder)
                
        def removeBatchFolder(self):
            print('Remove a folder..')
            folder_toberemoved = self.combo_removefolder.currentText()
            #remove the folder from the folder that should be analysed:
            self.batch_folders.remove(folder_toberemoved)
            #adapt the textedit and the combobox:
            self.names_batchfolders.clear()
            self.combo_removefolder.clear()
            
            for folder in self.batch_folders:
                self.names_batchfolders.append(folder)
                self.combo_removefolder.addItem(folder)
            
            if len(self.batch_folders)==0:
                self.button_removeBatchFolder.setEnabled(False)
                self.button_batch_startAnalysis.setEnabled(False)
                
            else:
                self.button_removeBatchFolder.setEnabled(True)

        def on_loadVideo(self, grid):
            #change button color if not already done
            self.button_succeed_tab1.setStyleSheet("background-color: IndianRed")
            self.progressbar_loadStack.setValue(0)
            
            #choose a folder
            msg = 'Choose an input video: file of type .mp4, .avi, .mov or a .tif file in a folder containing a sequence of .tif-images'
            try:
                fileName  = UserDialogs.chooseFileByUser(message=msg, input_folder=self.config['LAST SESSION']['input_folder'])  
            except Exception:
                fileName  = UserDialogs.chooseFileByUser(message=msg)
            
            print(fileName)
            #if 'cancel' was pressed: simply do nothing and wait for user to click another button
            if (fileName[0]  == ''):
                return
            try:
                inputpath = pathlib.Path(fileName[0])
                #save changes to config file
                self.config.set("LAST SESSION", "input_folder", str((inputpath / "..").resolve()))#easier with parent?
                self.save_to_config()
                
                #read imagestack
                self.import_video_thread = self.OHW.import_video_thread(inputpath)
                self.import_video_thread.start()
                #self.progressbar_loadStack.setFormat("loading Folder")  #is not displayed yet?
                self.progressbar_loadStack.setRange(0,0)
                self.import_video_thread.finished.connect(self.finish_loadVideo)
            except Exception:
                pass 
                        
        def finish_loadVideo(self):
            self.progressbar_loadStack.setRange(0,1)
            self.progressbar_loadStack.setValue(1)
            
            self.line_fps.setText(str(self.OHW.videometa['fps']))
            self.line_px_perMicron.setText(str(self.OHW.videometa['microns_per_pixel']))            
            # disable input field if videoinfos.txt available? if self.OHW.videometa['infofile_exists'] == True: ....
            
            self.add_sliders_blackWhiteVal()
            self.on_resetBlackWhiteVal()
            
            # display first image and update controls
            self.display_firstImage(self.OHW.rawImageStack[0])            
            
            inputpath = str('Chosen folder: ' + str(self.OHW.videometa['inputpath']))
            self.label_chosen_image.setText(inputpath)
            self.button_getMVs.setEnabled(True)
            self.button_succeed_tab1.setStyleSheet("background-color: YellowGreen")
            
            #display results folder and enable change of this folder
            current_folder = 'Current results folder: ' + str(pathlib.PureWindowsPath(self.OHW.analysis_meta['results_folder']))
            self.label_resultsfolder.setText(current_folder)
            self.button_change_resultsfolder.setEnabled(True)
            self.button_selectROI.setEnabled(True)
        
        def add_sliders_blackWhiteVal(self):
            """ add sliders for black and white value adaption to the tab, store original values
            """
            #store the original black and white values
            self.blackval_orig = self.OHW.videometa["Blackval"]
            self.whiteval_orig = self.OHW.videometa["Whiteval"]

            #update slider information
            self.slider_blackval.setMaximum(self.OHW.videometa["Whiteval"])
            self.slider_whiteval.setMinimum(self.OHW.videometa["Blackval"])
            self.slider_whiteval.setMaximum(self.OHW.videometa["Whiteval"]*3)
            self.slider_blackval.setValue(self.OHW.videometa["Blackval"])
            self.slider_whiteval.setValue(self.OHW.videometa["Whiteval"])
            
            #add sliders 
            self.tab1.layout.addWidget(self.label_slider_blackval,  12,1)
            self.tab1.layout.addWidget(self.slider_blackval,        13,1, 3, 1)
            self.tab1.layout.addWidget(self.label_slider_whiteval,  12,2)
            self.tab1.layout.addWidget(self.slider_whiteval,        13,2, 3, 1)
            
            self.tab1.layout.addWidget(self.button_reset_blackWhiteVal, 19, 1, 1, 2)
            
        def on_changeResultsfolder(self):
            #choose a folder
            msg = 'Choose a new folder for saving your results'
            folderName = UserDialogs.chooseFolderByUser(msg, input_folder=self.OHW.analysis_meta['results_folder'])#, input_folder=self.config['LAST SESSION']['results_folder'])  
            
            #if 'cancel' was pressed: simply do nothing and wait for user to click another button
            if (folderName == ''):
                return
            
            self.OHW.analysis_meta["results_folder"] = pathlib.Path(folderName)
            self.label_resultsfolder.setText(folderName)
            # fix for batch and rois!
            '''
            if self.sender() == self.button_change_resultsfolder:
                #change the results folder of the OHW class
                self.OHW.results_folder = pathlib.Path(folderName)
                
                #change the results folder for all OHW
                if len(self.ROI_OHWs) is not 0:
                    for ROI_nr in range(0,len(self.ROI_OHWs)):
                        self.ROI_OHWs[ROI_nr].results_folder = pathlib.Path(folderName).joinpath(self.ROI_names[ROI_nr])
                #display
                current_folder = 'Current results folder: ' + str(pathlib.PureWindowsPath(self.OHW.results_folder))
                self.label_resultsfolder.setText(current_folder)
                

            elif self.sender() == self.button_change_resultsfolder_batch:
                #change the batch results folder!
                self.results_folder_batch = pathlib.Path(folderName)
                
                #display new results folder
                current_folder = 'Current results folder: ' + str(pathlib.PureWindowsPath(self.results_folder_batch))
                self.label_resultsfolder_batch.setText(current_folder)
            '''    
            print('New results folder: %s' %folderName)            
            
        def display_firstImage(self, image):
             # display first image and update controls
            self.imshow_firstImage = self.ax_firstIm.imshow(image, cmap = 'gray', vmin = self.OHW.videometa["Blackval"], vmax = self.OHW.videometa["Whiteval"])
            self.canvas_firstImage.draw()            
            self.tab1.layout.addWidget(self.canvas_firstImage, 14,0) 

        def change_blackWhiteVal(self):          
            """ change the black and white values saved for image display
            """
            #save the new values to videometa
            self.OHW.videometa["Blackval"] = self.slider_blackval.value()
            self.OHW.videometa["Whiteval"] = self.slider_whiteval.value()
#            
#            #set allowed whitevals and blackvals            
            self.slider_blackval.setMaximum(self.OHW.videometa["Whiteval"])
            self.slider_whiteval.setMinimum(self.OHW.videometa["Blackval"])
            
            self.display_firstImage(image=self.OHW.rawImageStack[0])

        def on_resetBlackWhiteVal(self):
            """ resets the image display back to the original values
            """
             #save the new values to videometa
            self.OHW.videometa["Blackval"] = self.blackval_orig
            self.OHW.videometa["Whiteval"] = self.whiteval_orig
            
            self.slider_blackval.setValue(self.blackval_orig)
            self.slider_whiteval.setValue(self.whiteval_orig)
#            
#            #set allowed whitevals and blackvals            
#            self.slider_blackval.setMaximum(current_whiteval)
#            self.slider_whiteval.setMinimum(current_blackval)
            
            self.display_firstImage(image=self.OHW.rawImageStack[0])
            
        def display_ROI(self, ROI, ROI_nr, row):
            fig_ROI, ax_ROI = plt.subplots(1,1)
            ax_ROI.axis('off')
            canvas_ROI = FigureCanvas(fig_ROI)   
            
            #create frame
            frame = patches.Rectangle((0,0),ROI.shape[1],ROI.shape[0],linewidth=2,edgecolor='k',facecolor='none')
            # Add the patch to the Axes
            ax_ROI.add_patch(frame)
            
            # canvas_ROI.drawRectangle([0,0, ROI.shape[1], ROI.shape[0]])
            imshow_ROI = ax_ROI.imshow(ROI, cmap = 'gray', vmin = self.OHW.videometa["Blackval"], vmax = self.OHW.videometa["Whiteval"])

#            #adapt size
#            fig_size = plt.rcParams["figure.figsize"]
#            ratio = fig_size[1]/fig_size[0]
#            #change height
#            fig_size[1] = 4
#            fig_size[0] = fig_size[1] * ratio
    
            canvas_ROI.draw()           
            current_lineedit = QLineEdit()
            current_lineedit.setText(self.ROI_names[ROI_nr])
            #if text is changed by user, save it to ROI_names:
            current_lineedit.textEdited.connect(lambda: self.change_ROI_names(ROI_nr=ROI_nr))
            self.tabROIs.layout.addWidget(current_lineedit, row, 0)
            self.tabROIs.layout.addWidget(canvas_ROI,row,1) 
        
        def changeBlockwidth(self):
            self.blockwidth = self.spinbox_blockwidth.value()
            return self.blockwidth
        
        def changeDelay(self):
            self.delay = self.spinbox_delay.value()
            return self.delay    
        
        def changeMaxShift(self):
            self.maxShift = self.spinbox_maxShift.value()
            return self.maxShift
        
        def changeFPS(self):
            self.OHW.videometa['fps'] = float(self.line_fps.text())
            if len(self.ROI_OHWs) is not 0:
                for ROI_nr in range(0,len(self.ROI_OHWs)):
                    self.ROI_OHWs[ROI_nr].videometa['fps'] = float(self.line_fps.text())
        
        def changePxPerMicron(self):
            self.OHW.videometa['microns_per_pixel'] = float(self.line_px_perMicron.text())
            if len(self.ROI_OHWs) is not 0:
                for ROI_nr in range(0,len(self.ROI_OHWs)):
                    self.ROI_OHWs[ROI_nr].videometa['fps'] = float(self.line_fps.text())
    
        def on_detectPeaks(self):
            #detect peaks and draw them as EKG
            
            ratio = self.spinbox_ratio.value()
            number_of_neighbours = self.spinbox_neighbours.value()
            self.current_dataset.detect_peaks(ratio, number_of_neighbours)
            self.updatePeaks()

        def updatePeaks(self):
            """
                update detected peaks in graph
            """
            
            Peaks = self.current_dataset.get_peaks()     
            
            # clear old peaks first
            if self.plotted_peaks == True:
                self.highpeaks.remove()
                self.lowpeaks.remove()
                self.plotted_peaks = False
            
            if type(Peaks["t_peaks_low_sorted"]) == np.ndarray:
                # plot peaks, low peaks are marked as triangles , high peaks are marked as circles         
                self.highpeaks, = self.ax_kinetics.plot(Peaks["t_peaks_low_sorted"], Peaks["peaks_low_sorted"], marker='o', ls="", ms=5, color='r' )
                self.lowpeaks, = self.ax_kinetics.plot(Peaks["t_peaks_high_sorted"], Peaks["peaks_high_sorted"], marker='^', ls="", ms=5, color='r' )       
                self.plotted_peaks = True
                
            self.canvas_kinetics.draw()

            peakstatistics = self.current_dataset.get_peakstatistics()
            peaktime_intervals = self.current_dataset.get_peaktime_intervals()
            bpm = self.current_dataset.get_bpm()
            
            try:
                #display statistics
                text_contraction = str(peakstatistics["max_contraction"]) + ' +- '+ str(peakstatistics["max_contraction"]) +  u' \xb5m/sec'
                text_relaxation = str(peakstatistics["max_relaxation"]) + ' +- '+ str(peakstatistics["max_relaxation_std"]) +  u' \xb5m/sec'
                text_time_contraction = str(peaktime_intervals["contraction_interval_mean"]) + ' +- ' + str(peaktime_intervals["contraction_interval_std"]) + ' sec'
                text_time_relaxation = str(peaktime_intervals["relaxation_interval_mean"]) + ' +- ' + str(peaktime_intervals["relaxation_interval_std"]) + ' sec'
                text_time_contr_relax = str(peaktime_intervals["contr_relax_interval_mean"]) + ' +- ' + str(peaktime_intervals["contr_relax_interval_std"]) + ' sec'
                text_bpm = str(bpm["bpm_mean"]) + ' +- ' + str(bpm["bpm_std"]) + ' beats/min'
            
            except (NameError, AttributeError):
                return
            
            self.label_max_contraction_result.setText(text_contraction)
            self.label_max_relaxation_result.setText(text_relaxation)
            self.label_time_contraction_result.setText(text_time_contraction)
            self.label_time_relaxation_result.setText(text_time_relaxation)
            self.label_time_contr_relax_result.setText(text_time_contr_relax)
            self.label_bpm_result.setText(text_bpm)
            
            #enable saving of peaks and statistics
            self.button_export_peaks.setEnabled(True)
            self.button_export_ekg_csv.setEnabled(True)
            self.button_export_statistics.setEnabled(True)
            
        def on_exportPeaks(self):
            
            self.current_dataset.export_peaks()            
            helpfunctions.msgbox(self, 'Raw and analyzed peaks were successfully saved')
            
        def on_exportEKG_CSV(self):
            
            self.current_dataset.exportEKG_CSV()
            helpfunctions.msgbox(self, 'EKG values were successfully saved')
            
        def on_exportStatistics(self):
            
            self.current_dataset.exportStatistics()
            helpfunctions.msgbox(self, 'Statistics were successfully saved')
            
        def on_saveKinetics(self):
            
            mark_peaks = self.plotted_peaks
            
            #allowed file types:
            file_types = "PNG (*.png);;JPEG (*.jpeg);;TIFF (*.tiff);;BMP(*.bmp);; Scalable Vector Graphics (*.svg)"
            #let the user choose a folder from the starting path
            path = str(pathlib.PureWindowsPath(self.current_dataset.analysis_meta["results_folder"] / 'beating_kinetics.PNG'))
            filename_save = QFileDialog.getSaveFileName(None, 'Choose a folder and enter a filename', path, file_types)

            #if 'cancel' was pressed: simply do nothing and wait for user to click another button
            if (filename_save == ('','')):
                return
            try:
                self.current_dataset.plot_beatingKinetics(mark_peaks, filename_save)
                mainWidget = self.findMainWindow()
                mainWidget.adjustSize()
                print('Graphs were saved successfully.')
                
            except (IndexError, NameError, AttributeError):
                pass
        
        def on_getMVs(self):
            #disable button to not cause interference between different calculations
            self.button_getMVs.setEnabled(False)
            
            #get current parameters entered by user
            blockwidth = self.changeBlockwidth()
            maxShift = self.changeMaxShift()
            delay = self.changeDelay()
            
            px_longest = None
            if self.scaling_status == True:
                px_longest = 1024
            '''
            else:                
                #if at least one ROI was selected, use ROI ImageStack and also calculate the whole image
                if len(self.ROI_OHWs) is not 0:
                    for nr_ROI in range(0, len(self.ROI_OHWs)):
                        #calculate motion vectors for each ROI
                        self.ROI_OHWs[nr_ROI].scale_ImageStack(self.ROI_OHWs[nr_ROI].ROIImageStack.shape[1], 
                                                               self.ROI_OHWs[nr_ROI].ROIImageStack.shape[2])
    
                        cal_MVs_thread = self.ROI_OHWs[nr_ROI].calculate_MVs_thread(blockwidth = blockwidth, delay = delay, max_shift = maxShift)
                        cal_MVs_thread.start()
                        self.ready = False
                        cal_MVs_thread.progressSignal.connect(self.updateMVProgressBar)
                        #initialize_calculatedMVs only for the full image, for the ROIs on-the-fly
                        #cal_MVs_thread.finished.connect(self.initialize_calculatedMVs)

#                #always calculate the full image
                self.OHW.scale_ImageStack(self.OHW.rawImageStack.shape[1], self.OHW.rawImageStack.shape[2])     
            '''
            
            self.OHW.set_analysisImageStack(px_longest = px_longest) # scale + set roi, , roi=[0,0,500,500]
            
            calculate_motion_thread = self.OHW.calculate_motion_thread(blockwidth = blockwidth, delay = delay, max_shift = maxShift)
            calculate_motion_thread.start()
            calculate_motion_thread.progressSignal.connect(self.updateMVProgressBar)
            calculate_motion_thread.finished.connect(self.initialize_motion)
              
        def updateMVProgressBar(self, value):
                self.progressbar_MVs.setValue(value*100)

        def updateProgressBar_batch(self, value):
                self.progressbar_batch.setValue(value*100)
                
        def updateProgressBar(self, value):
                self.progressbar_tab2.setValue(value*100)
        
        def initialize_motion(self):
            if not hasattr(self, 'current_dataset'):
                self.current_dataset = self.OHW
            
            self.current_dataset.initialize_motion()
            
            #set the succeed button to green:
            self.button_succeed_MVs.setStyleSheet("background-color: YellowGreen")
                
            #enable other buttons for further actions
            self.button_save_motionVectors.setEnabled(True)
            self.button_detectPeaks.setEnabled(True)
            self.button_saveKinetics.setEnabled(True)
            self.button_heatmaps_video.setEnabled(True)
            self.button_quivers_video.setEnabled(True)
            self.slider_heatmaps.setEnabled(True)
            self.slider_quiver.setEnabled(True)
            
            self.initialize_kinetics()
            
            # fill graphs with data from first frame
            self.initialize_MV_graphs()
                        
            # initialize time averaged motion
            #self.initializeTimeAveragedMotion()

            #enable further buttons
            self.button_save_Heatmap.setEnabled(True)
            self.button_save_Quiver.setEnabled(True)
            self.button_save_timeMotion.setEnabled(True)
            self.button_getMVs.setEnabled(True)
            
            '''
            #set ready for next thread
            self.ready = True
            
            #get the current video length and save it to the quiver settings
            self.quiver_settings['video_length'] = str(1/self.current_dataset.videometa["fps"] * self.current_dataset.absMotions.shape[0])
            '''
            
        def initialize_kinetics(self):
            """
                initializes graph for beating kinetics "EKG"
            """
            print("initialize beating kinetics graphs")
            
            self.fig_kinetics, self.ax_kinetics = plotfunctions.plot_Kinetics(self.current_dataset.timeindex, self.current_dataset.mean_absMotions, Peaks=None, mark_peaks=False, file_name=None)#'test.png'           
            
            self.canvas_kinetics = FigureCanvas(self.fig_kinetics)  
            self.fig_kinetics.subplots_adjust(bottom = 0.2)            
            
            self.tab3.layout.addWidget(self.canvas_kinetics, 7,0)
            self.canvas_kinetics.draw()
            
        def initialize_MV_graphs(self):
            print("initialize MV graphs")
            # initialize heatmaps, display first frame           
            
            scale_max = helpfunctions.get_scale_maxMotion2(self.current_dataset.absMotions) #decide on which scale to use
            
            self.imshow_heatmaps = self.ax_heatmaps.imshow(self.current_dataset.absMotions[0], vmin = 0, vmax = scale_max, cmap = 'jet', interpolation = 'bilinear')
            self.slider_heatmaps.setMaximum(self.current_dataset.absMotions.shape[0]-1)
            
            """
            # Titel noch nicht in GUI hinzufügen bzw. Größe anpassen...
            cbar_heatmaps = self.fig_heatmaps.colorbar(self.imshow_heatmaps)
            cbar_heatmaps.ax.tick_params(labelsize=20)
            for l in cbar_heatmaps.ax.yaxis.get_ticklabels():
                l.set_weight("bold")
            self.ax_heatmaps.set_title('Motion [µm/s]', fontsize = 16, fontweight = 'bold')            
            """
            
            self.canvas_heatmap.draw()
            self.tab4.layout.addWidget(self.canvas_heatmap, 8, 0)
            
            
            # initialize quivers, display first frame
            #new figure
            # display figures for quivers in Canvas
            self.fig_quivers, self.ax_quivers = plt.subplots(1,1)
            self.fig_quivers.set_size_inches(16,12)
            self.ax_quivers.axis('off')
            self.canvas_quivers = FigureCanvas(self.fig_quivers)
            '''
            if not self.current_dataset.isROI_OHW:
                if self.quiver_settings['show_scalebar']:
                    #only draw scalebar if it is the full image and if specified in the quiver settings
                    self.current_dataset.plot_scalebar()
                    
                else:
                    #remove scalebar by recalculating the scaled imagestack
                    self.current_dataset.scale_ImageStack(self.OHW.rawImageStack.shape[1], self.OHW.rawImageStack.shape[2])
            '''

            self.slider_quiver.setMaximum(self.current_dataset.mean_absMotions.shape[0]-1)# or introduce new variable which counts the amount of motion timepoints

            blockwidth = self.current_dataset.analysis_meta["MV_parameters"]["blockwidth"]
            microns_per_pixel = self.current_dataset.videometa["microns_per_pixel"]
            scalingfactor = self.current_dataset.analysis_meta["scalingfactor"]
            scale_max = helpfunctions.get_scale_maxMotion2(self.current_dataset.absMotions)
            
            skipquivers =  int(self.quiver_settings['quiver_density'])
            distance_between_arrows = blockwidth * skipquivers
            arrowscale = 1 / (distance_between_arrows / scale_max)
            
            #self.MotionCoordinatesX, self.MotionCoordinatesY = np.meshgrid(np.arange(blockwidth/2, self.current_dataset.scaledImageStack.shape[2]-blockwidth/2, blockwidth)+1, np.arange(blockwidth/2, self.current_dataset.scaledImageStack.shape[1]-blockwidth/2+1, blockwidth))  #changed arange range, double check!
            
            self.qslice=(slice(None,None,skipquivers),slice(None,None,skipquivers))
            qslice = self.qslice
            
            self.imshow_quivers = self.ax_quivers.imshow(
                    self.current_dataset.analysisImageStack[0], cmap = "gray", 
                    vmin = self.current_dataset.videometa["Blackval"], vmax = self.current_dataset.videometa["Whiteval"])
            self.quiver_quivers = self.ax_quivers.quiver(
                    self.current_dataset.MotionCoordinatesX[qslice], 
                    self.current_dataset.MotionCoordinatesY[qslice], 
                    self.current_dataset.MotionX[0][qslice], 
                    self.current_dataset.MotionY[0][qslice], 
                    pivot='mid', color='r', units ="xy", scale_units = "xy", angles = "xy", 
                    scale = arrowscale, width = 3, headwidth = 2, headlength = 3) #adjust scale to max. movement   #width = blockwidth / 4?
            
            self.canvas_quivers.draw()
            self.tab4.layout.addWidget(self.canvas_quivers,  8,  2)


        def on_saveMVs(self):
            """
                saves raw MVs to results folder
            """
            self.current_dataset.save_MVs()
            helpfunctions.msgbox(self, 'Motion vectors were successfully saved')
            
        def findMainWindow(self): #-> typing.Union[QMainWindow, None]:
            # Global function to find the (open) QMainWindow in application
            app = QApplication.instance()
            for widget in app.topLevelWidgets():
                if isinstance(widget, QMainWindow):
                    return widget
            return None
        
        def restartGUI(self):
            #restarts the application to work with new data
            python = sys.executable
            os.execl(python, python, *sys.argv)
        
        def updateHeatMap(self, frame):
            #callback when slider is moved
            self.imshow_heatmaps.set_data(self.current_dataset.absMotions[frame])
            self.canvas_heatmap.draw()
 
        def updateQuiver(self, frame):
            #callback when slider is moved
            self.imshow_quivers.set_data(self.current_dataset.analysisImageStack[frame])    #introduce a displayImageStack here?
            self.quiver_quivers.set_UVC(self.current_dataset.MotionX[frame][self.qslice], self.current_dataset.MotionY[frame][self.qslice])
            self.canvas_quivers.draw()

        def on_saveHeatmapvideo(self):
            """
                saves the heatmpavideo
            """
            #reset the color of success-button
            self.button_succeed_heatmaps.setStyleSheet("background-color: IndianRed")
            self.progressbar_heatmaps.setValue(0)
            
            save_heatmap_thread = self.current_dataset.save_heatmap_thread(singleframe = False)
            save_heatmap_thread.start()
            self.progressbar_heatmaps.setRange(0,0)
            save_heatmap_thread.finished.connect(self.finish_saveHeatmapvideo)
        
        def finish_saveHeatmapvideo(self):
            self.progressbar_heatmaps.setRange(0,1)
            self.progressbar_heatmaps.setValue(1)
            helpfunctions.msgbox(self, 'Heatmap video was saved successfully')
            
            #set succeed button to green if video creation finished
            self.button_succeed_heatmaps.setStyleSheet("background-color: YellowGreen")            
        
        def on_saveHeatmap(self):
            """
                saves the selected frame (singleframe = framenumber)
            """
            singleframe=self.slider_heatmaps.value()
            self.current_dataset.save_heatmap(singleframe = singleframe)
            
            helpfunctions.msgbox(self, 'Heatmap of frame ' + str(singleframe) + ' was saved successfully')
        
        def on_change_quiverSettings(self):
            #calculate maximum video length
          #  del self.quiver_settings['video_length']
            self.quiver_settings['video_length'] = str(1/self.current_dataset.videometa["fps"] * self.current_dataset.absMotions.shape[0])

            # open new window and let user change export settings
            self.settingsWindow = QuiverExportOptions.QuiverExportOptions(prevSettings = self.quiver_settings)
            self.settingsWindow.table_widget.got_settings.connect(self.save_quiver_settings)
            self.settingsWindow.show()
            
        def save_quiver_settings(self, settings):
            """
                receive the signals from quiver settings changed by user
            """
            self.quiver_settings = settings
            
            #save quiver settings to config.ini:
            #convert to string suitable for configparser
            for item in ['one_view', 'three_views', 'show_scalebar']:
                self.config.set("DEFAULT QUIVER SETTINGS", option=item, value=str(self.quiver_settings[item]).lower())
            for item in ['quiver_density', 'video_length']:
                self.config.set("DEFAULT QUIVER SETTINGS", option=item, value=str(self.quiver_settings[item]))
            
            self.save_to_config()
            
            #close the settings window
            self.settingsWindow.close()
            
            #initialize MV_graphs again
            self.initialize_MV_graphs()
            
        def save_to_config(self):
            with open('config.ini', 'w') as configfile:
                self.config.write(configfile)
                
        def on_saveQuivervideo(self):
            """
                saves the quivervideo
            """
            #reset the color of success-button
            self.button_succeed_quivers.setStyleSheet("background-color: IndianRed")
            self.progressbar_quivers.setValue(0)
            
            """
            if self.quiver_settings['one_view']:
                #export one view quivers
                save_quiver1_thread = self.current_dataset.save_quiver_thread(singleframe = False, skipquivers = int(self.quiver_settings['quiver_density']), t_cut=float(self.quiver_settings['video_length']))
                save_quiver1_thread.start()
                self.progressbar_quivers.setRange(0,0)
                save_quiver1_thread.finished.connect(self.finish_saveQuivervideo)
                              
            if self.quiver_settings['three_views']:
                #export three views quivers
                save_quiver3_thread = self.current_dataset.save_quivervid3_thread(skipquivers = int(self.quiver_settings['quiver_density']), t_cut=float(self.quiver_settings['video_length']))
                save_quiver3_thread.start()
                self.progressbar_quivers.setRange(0,0)
                save_quiver3_thread.finished.connect(self.finish_saveQuivervideo)
            """
            
            save_quiver_thread = self.OHW.save_quiver3_thread(singleframe = False, skipquivers = 4)
            save_quiver_thread.start()
            self.progressbar_quivers.setRange(0,0)
            save_quiver_thread.finished.connect(self.finish_saveQuivervideo)
            
        def finish_saveQuivervideo(self):
            self.progressbar_quivers.setRange(0,1)
            self.progressbar_quivers.setValue(1)
            
            helpfunctions.msgbox(self, 'Quiver was saved successfully')

            #set succeed button to green if video creation finished
            self.button_succeed_quivers.setStyleSheet("background-color: YellowGreen")

            
        def on_saveQuiver(self):
            """
                saves either the selected frame (singleframe = framenumber)
            """     
            singleframe = int(self.slider_quiver.value())
            
            """
            #save the different views if chosen by the user
            if self.quiver_settings['one_view']:

                self.current_dataset.save_quiver(singleframe = singleframe, skipquivers = int(self.quiver_settings['quiver_density']))
            
            if self.quiver_settings['three_views']:
                self.current_dataset.save_quivervid3(singleframe = singleframe, skipquivers = int(self.quiver_settings['quiver_density']))
            """
            self.current_dataset.save_quiver3(singleframe = singleframe)
            
            #display a message
            helpfunctions.msgbox(self, 'Quiver of frame ' + str(singleframe) + ' was saved successfully')            

        def slider_heatmaps_valueChanged(self):
            frame = self.slider_heatmaps.value()
            time = round(frame / self.current_dataset.videometa["fps"], 3)
            self.updateHeatMap(frame)
            self.label_heatmap_result.setText('Heatmap of frame ' + str(frame) + ' at time ' + str(time) + 'sec')
        
        def slider_quiver_valueChanged(self): 
            frame = self.slider_quiver.value()
            time = round(frame / self.current_dataset.videometa["fps"], 3)
            self.updateQuiver(frame)
            self.label_quiver_result.setText('Quiverplot of frame ' + str(frame) + ' at time ' + str(time) + ' sec')            
                
        def initializeTimeAveragedMotion(self): 
            max_motion = self.current_dataset.max_avgMotion
            
            self.imshow_motion_total = self.ax_motion_total.imshow(self.current_dataset.avg_absMotion, vmin = 0, vmax = max_motion, cmap="jet", interpolation="bilinear")#, cmap = 'gray', vmin = self.Blackval, vmax = self.Whiteval)
            self.imshow_motion_x = self.ax_motion_x.imshow(self.current_dataset.avg_MotionX, vmin = 0, vmax = max_motion, cmap="jet", interpolation="bilinear")
            self.imshow_motion_y = self.ax_motion_y.imshow(self.current_dataset.avg_MotionY, vmin = 0, vmax = max_motion, cmap="jet", interpolation="bilinear")
            
            self.canvas_motion_total.draw()
            self.canvas_motion_x.draw()
            self.canvas_motion_y.draw()
            
            self.tab5.layout.addWidget(self.canvas_motion_total, 6,0)
            self.tab5.layout.addWidget(self.canvas_motion_x, 8,0)
            self.tab5.layout.addWidget(self.canvas_motion_y, 8,1)
            
            self.button_succeed_motion.setStyleSheet("background-color: YellowGreen")
            self.button_save_timeMotion.setEnabled(True)
            
            self.current_dataset.plot_TimeAveragedMotions('.png')
                
        def on_saveTimeAveragedMotion(self):
            
            file_ext = self.combo_avgExt.currentText()
            self.current_dataset.plot_TimeAveragedMotions(file_ext)
            
            helpfunctions.msgbox(self, 'Plots of time averaged motion were saved successfully.')
            
        def changeStatus(self):
            #handle changes of filterstatus
            if self.sender() == self.check_filter:
                self.filter_status = self.check_filter.isChecked()
            
            #handle changes of batch scaling
            elif self.sender() == self.batch_checkScaling:
                self.batch_scaling_status = self.batch_checkScaling.isChecked()
                if (self.batch_scaling_status == True):
                    self.batch_factor_scaling = 1024
                elif (self.batch_scaling_status == False): 
                    self.batch_factor_scaling = 2048
            
            #handle changes of scaling options
            elif self.sender() == self.check_scaling:
                self.scaling_status = self.check_scaling.isChecked()
                if (self.scaling_status == True):
                    self.factor_scaling = 1024
                elif (self.scaling_status == False): 
                    self.factor_scaling = 2048
            
            #handle changes of batch filter option
            elif self.sender() == self.batch_checkFilter:
                self.batch_filter_status = self.batch_checkFilter.isChecked()
                
            #handle changes of save motion vector option
            elif self.sender() == self.batch_checkSaveMotionVectors:
                self.batch_saveMotionVectors_status = self.batch_checkSaveMotionVectors.isChecked()
                
            #handle changes of batch heatmap option
            elif self.sender() == self.batch_checkHeatmaps:
                self.batch_heatmap_status = self.batch_checkHeatmaps.isChecked()
            
            #handle changes of batch quiver option
            elif self.sender() == self.batch_checkQuivers:
                self.batch_quiver_status = self.batch_checkQuivers.isChecked()