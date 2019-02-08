# -*- coding: utf-8 -*-

import pathlib # change to pathlib from Python 3.4 instead of os
import tifffile
import cv2
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import argrelextrema

from libraries import OFlowCalc, Filters, plotfunctions, helpfunctions, PeakDetection

import moviepy.editor as mpy
from moviepy.video.io.bindings import mplfig_to_npimage

class OHW():
    """
        main class of OpenHeartWare
        bundles MVs + parameters 
    """
    def __init__(self):
        
        self.inputpath = None #
        self.rawImageStack = None       # array for raw imported imagestack
        self.scaledImageStack = None
        self.rawMVs = None              # array for raw motion vectors (MVs)
        self.videoMeta = {"microns_per_pixel":1,"fps":1,"blackval":0,"whiteval":None}   # dict of video metadata: microns_per_pixel, fps, blackval, whiteval, 
        self.unitMVs = None             # MVs in correct unit (microns)
        self.scalingfactor = None
        self.MV_parameters = None       # dict for MV parameters
        self.results_folder = None      # folder for saving results
        self.absMotions = None
        self.mean_absMotions = None     # for 1D-representation
        self.avg_absMotion = None       # time averaged absolute motion
        self.avg_MotionX = None         # time averaged x-motion
        self.avg_MotionY = None         # time averaged y-motion
        self.max_avgMotion = None       # maximum of time averaged motions
        self.timeindex = None           # time index for 1D-representation
        self.PeakDetection = PeakDetection.PeakDetection()    # class which detects + saves peaks
       
    def read_imagestack(self, inputfolder, *args, **kwargs):
        """
            reads desired inputvideo as np.array
            choose inputmethod based on file extension
            --> populate self.rawImageStack
        """
        print("Reading images from path ", inputfolder)
        
        self.inputpath = pathlib.Path(inputfolder)
        
        if self.inputpath.is_file():
            print("... which is a single file")
            
            self.rawImageStack, self.videoMeta["fps"] = self.read_videofile(str(self.inputpath))
            
            dtype = self.rawImageStack[0,0,0].dtype

            
            self.videoMeta["microns_per_pixel"] = 1
            
            self.videoMeta["Blackval"], self.videoMeta["Whiteval"] = np.percentile(self.rawImageStack[0], (0.1, 99.9))

            self.results_folder = self.inputpath.parent / ("results_" + str(self.inputpath.stem) )
            
        elif self.inputpath.is_dir():
            # directory with .tifs
            print("... which is a folder")
            inputtifs = list(self.inputpath.glob('*.tif'))  # or use sorted instead of list
            
            self.rawImageStack = tifffile.imread(inputtifs, pattern = "")
            self.rawImageStack = self.rawImageStack.astype(np.float32)    #convert as cv2 needs float32 for templateMatching
            
            self.videoMeta["Blackval"], self.videoMeta["Whiteval"] = np.percentile(self.rawImageStack[0], (0.1, 99.9))  #set default values, will be overwritten by all values in videoinfos file
            
            #get_tif_meta (from first and second image, stored in imagej tag)
            if (self.inputpath / "videoinfos.txt").is_file():
                # set metadata from file if videoinfos.txt exists
                print("videoinfos.txt exists in inputfolder, reading parameters.")
                self.get_videoinfos_file()
            
            self.results_folder = self.inputpath / "results"
            
        """
        # folder with imageseries (tif-only at the moment), read with tifffile
        if folder:
            if videoinfos file
                read videoinfos from file
                set non-specified values to default values (easier: set all to default and change new ones) (auto-adj. black-white)
            elif info in tiftag
                read infos from tag
                set non-specified values to default values (auto-adj. black-white)
            else 
                use default values
                auto-adj. black-white
    
        # single movie file, use cv2 as reader
        if file:
        """
    
    def read_imagestack_thread(self, inputfolder):
        self.thread_read_imagestack = helpfunctions.turn_function_into_thread(self.read_imagestack, emit_progSignal = True, inputfolder = inputfolder)
        return self.thread_read_imagestack
    
    def read_videofile(self, inputpath):
        cap = cv2.VideoCapture(inputpath)

        frameCount = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frameWidth = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frameHeight = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        videofps = cap.get(cv2.CAP_PROP_FPS)

        rawImageStack = np.empty((frameCount, frameHeight, frameWidth), np.dtype('uint8'))

        fc = 0
        ret = True

        while (fc < frameCount  and ret):
            ret, frame = cap.read()
            rawImageStack[fc] = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fc += 1

        cap.release()
        return rawImageStack, videofps
    
    def get_videoinfos_file(self):
        """
            reads dict from file videoinfos.txt and sets values in videoMeta
        """
        filereader = (self.inputpath / "videoinfos.txt").open("r")
        videoinfos_file = eval(filereader.read())
        filereader.close()
        for key, value in videoinfos_file.items():
            self.videoMeta[key] = value
    
    def scale_ImageStack(self, max_size = 1024):
        """
            rescales input ImageStack
        """
        print ("rescaling images to max. size of", max_size)
        scaledImages = []
        for image in self.rawImageStack:   #rawImageStack[:-2]
            scaledImages.append(cv2.resize(image,(max_size,max_size)))
        
        self.scaledImageStack = np.array(scaledImages)
        self.scalingfactor = self.scaledImageStack[0].shape[0] / self.rawImageStack[0].shape[0]
        print("shape of scaled down image stack: ", self.scaledImageStack.shape)
        print("scalingfactor: ", self.scalingfactor)
    
    def plot_scalebar(self):
        """
            plots scalebar onto np-array
        """
        # move to other module
        sizeX = self.scaledImageStack.shape[1]
        resolution_units = self.videoMeta["microns_per_pixel"] / self.scalingfactor
        scalebar = helpfunctions.create_scalebar(sizeX,resolution_units)*(self.videoMeta["Whiteval"]/255)    #Oli
        scale_width_px = scalebar.shape[0]
        scale_height_px = scalebar.shape[1]
        self.scaledImageStack[:,-1-scale_width_px:-1,-1-scale_height_px:-1] = scalebar        
    
    def calculate_MVs_thread(self, **parameters):
        self.thread_calculate_MVs = helpfunctions.turn_function_into_thread(self.calculate_MVs, emit_progSignal=True, **parameters)
        return self.thread_calculate_MVs            
    
    def initialize_calculatedMVs(self):
        #self.rawMVs = self.thread_BM_stack.MotionVectorsAll
        
        self.unitMVs = (self.rawMVs / self.scalingfactor) * self.videoMeta["microns_per_pixel"] * (self.videoMeta["fps"] / self.MV_parameters["delay"])
        self.absMotions = np.sqrt(self.unitMVs[:,0]*self.unitMVs[:,0] + self.unitMVs[:,1]*self.unitMVs[:,1])# get absolute motions per frame
        
        self.get_mean_absMotion()
        self.calc_TimeAveragedMotion()
        
        self.results_folder.mkdir(parents = True, exist_ok = True) #create folder for results
    
    def calculate_MVs(self, method = 'BM', progressSignal = None, **parameters):
        """
            calculates motionvectors MVs of imagestack based on method and parameters
        """
    
        """
            switch method:
            
            -blockmatch
            -gunnar farnbäck
            -lucas-kanade
            
            self.rawMVs = ...
        """
        
        self.MV_parameters = parameters   #store parameters which were used for the calculation of MVs
        
        if method == 'BM':          
            self.rawMVs = OFlowCalc.BM_stack(self.scaledImageStack, progressSignal = progressSignal, **parameters)
    
        self.unitMVs = (self.rawMVs / self.scalingfactor) * self.videoMeta["microns_per_pixel"] * (self.videoMeta["fps"] / self.MV_parameters["delay"])
        self.absMotions = np.sqrt(self.unitMVs[:,0]*self.unitMVs[:,0] + self.unitMVs[:,1]*self.unitMVs[:,1])# get absolute motions per frame
        
        self.get_mean_absMotion()
        self.calc_TimeAveragedMotion()
        
        self.results_folder.mkdir(parents = True, exist_ok = True) #create folder for results
    
    def save_heatmap(self, singleframe = False, *args, **kwargs):
        """
            saves either the selected frame (singleframe = framenumber) or the whole heatmap video (=False)
        """
        
        #prepare figure
        savefig_heatmaps, saveax_heatmaps = plt.subplots(1,1)
        savefig_heatmaps.set_size_inches(16, 12)
        saveax_heatmaps.axis('off')   
        
        scale_max = self.get_scale_maxMotion()
        imshow_heatmaps = saveax_heatmaps.imshow(self.absMotions[0], vmin = 0, vmax = scale_max, cmap = "jet", interpolation="bilinear")#  cmap="inferno"
        
        cbar_heatmaps = savefig_heatmaps.colorbar(imshow_heatmaps)
        cbar_heatmaps.ax.tick_params(labelsize=20)
        for l in cbar_heatmaps.ax.yaxis.get_ticklabels():
            l.set_weight("bold")
        saveax_heatmaps.set_title('Motion [µm/s]', fontsize = 16, fontweight = 'bold')

        path_heatmaps = self.results_folder / "heatmap_results"
        path_heatmaps.mkdir(parents = True, exist_ok = True) #create folder for results
        
        if singleframe != False:
        # save only specified frame
            imshow_heatmaps.set_data(self.absMotions[singleframe])
            
            heatmap_filename = str(path_heatmaps / ('heatmap_frame' + str(singleframe) + '.png'))
            savefig_heatmaps.savefig(heatmap_filename,bbox_inches ="tight",pad_inches =0)
        
        else:
        # save video
            def make_frame_mpl(t):

                frame = int(round(t*self.videoMeta["fps"]))
                imshow_heatmaps.set_data(self.absMotions[frame])

                return mplfig_to_npimage(savefig_heatmaps) # RGB image of the figure
            
            heatmap_filename = str(path_heatmaps / 'heatmapvideo.mp4')
            duration = 1/self.videoMeta["fps"] * self.absMotions.shape[0]
            animation = mpy.VideoClip(make_frame_mpl, duration=duration)
            animation.write_videofile(heatmap_filename, fps=self.videoMeta["fps"])    

    def save_heatmap_thread(self, singleframe):
        self.thread_save_heatmap = helpfunctions.turn_function_into_thread(self.save_heatmap, singleframe=False)
        return self.thread_save_heatmap
            
    def save_quiver(self, singleframe = False, *args, **kwargs):
        """
            saves either the selected frame (singleframe = framenumber) or the whole heatmap video (= False)
            # todo: add option to clip arrows + adjust density of arrows
            # todo: maybe move to helpfunctions?
        """

        # prepare MVs... needs refactoring as it's done twice!
        self.MV_zerofiltered = Filters.zeromotion_to_nan(self.unitMVs, copy=True)
        self.MotionX = self.MV_zerofiltered[:,0,:,:]
        self.MotionY = self.MV_zerofiltered[:,1,:,:]

        blockwidth = self.MV_parameters["blockwidth"]
        self.MotionCoordinatesX, self.MotionCoordinatesY = np.meshgrid(np.arange(blockwidth/2, self.scaledImageStack.shape[1], blockwidth), np.arange(blockwidth/2, self.scaledImageStack.shape[2], blockwidth))        
           
        #prepare figure
        savefig_quivers, saveax_quivers = plt.subplots(1,1)
        savefig_quivers.set_size_inches(16, 12)
        saveax_quivers.axis('off')   

        scale_max = self.get_scale_maxMotion()       
        arrowscale = scale_max / (self.MV_parameters["blockwidth"] * self.videoMeta["microns_per_pixel"] / self.scalingfactor) #0.07 previously
        
        imshow_quivers = saveax_quivers.imshow(self.scaledImageStack[0], vmin = self.videoMeta["Blackval"], vmax = self.videoMeta["Whiteval"], cmap = "gray")
        quiver_quivers = saveax_quivers.quiver(self.MotionCoordinatesX, self.MotionCoordinatesY, self.MotionX[0], self.MotionY[0], pivot='mid', color='r', units ="xy", scale = arrowscale)
        
        #saveax_quivers.set_title('Motion [µm/s]', fontsize = 16, fontweight = 'bold')

        path_quivers = self.results_folder / "quiver_results"
        path_quivers.mkdir(parents = True, exist_ok = True) #create folder for results
        
        if singleframe != False:
            # save only specified frame

            imshow_quivers.set_data(self.scaledImageStack[singleframe])
            quiver_quivers.set_UVC(self.MotionX[singleframe], self.MotionY[singleframe])
            
            quivers_filename = str(path_quivers / ('quiver_frame' + str(singleframe) + '.png'))
            savefig_quivers.savefig(quivers_filename,bbox_inches ="tight",pad_inches =0, dpi = 200)
        
        else:
        # save video
            def make_frame_mpl(t):

                frame = int(round(t*self.videoMeta["fps"]))
                imshow_quivers.set_data(self.scaledImageStack[frame])
                quiver_quivers.set_UVC(self.MotionX[frame], self.MotionY[frame])

                return mplfig_to_npimage(savefig_quivers) # RGB image of the figure
            
            quivers_filename = str(path_quivers / 'quivervideo.mp4')
            duration = 1/self.videoMeta["fps"] * self.MotionX.shape[0]
            animation = mpy.VideoClip(make_frame_mpl, duration=duration)
            animation.write_videofile(quivers_filename, fps=self.videoMeta["fps"])

    def save_quiver_thread(self, singleframe):
        self.thread_save_quiver = helpfunctions.turn_function_into_thread(self.save_quiver, singleframe=False)
        return self.thread_save_quiver            
            
    def save_MVs(self):
        """
            saves raw MVs as npy file
        """
        save_file = str(self.results_folder / 'rawMVs.npy')
        np.save(save_file, self.rawMVs)   #MotionVectorsAll
        save_file_units = str(self.results_folder / 'absMotions.npy')
        np.save(save_file_units, self.absMotions)
    
    def get_mean_absMotion(self):
        """
            calculates movement mask (eliminates all pixels where no movement occurs through all frames)
            applies mask to absMotions and calculate mean motion per frame
        """
        # move into filter module in future?
        summed_absMotions = np.sum(self.absMotions, axis = 0)  # select only points in array with nonzero movement
        movement_mask = summed_absMotions == 0
        
        filtered_absMotions = np.copy(self.absMotions)
        filtered_absMotions[:,movement_mask] = np.nan
        self.mean_absMotions = np.nanmean(filtered_absMotions, axis=(1,2))
        self.timeindex = (np.arange(self.mean_absMotions.shape[0]) / self.videoMeta["fps"]).round(2)
    
    def get_scale_maxMotion(self):
        """
            returns maximum for scaling of heatmap + arrows in quiver
        """
        
        max_motion_framenr = np.argmax(self.mean_absMotions)
        max_motion_frame = self.absMotions[max_motion_framenr]
        scale_min, scale_maxMotion = np.percentile(max_motion_frame, (0.1, 95))
        return scale_maxMotion
        
    def detect_peaks(self, ratio, number_of_neighbours):
        """
            peak detection in mean_absMotions
        """
        
        self.PeakDetection.set_data(self.timeindex,self.mean_absMotions)
        
        self.PeakDetection.detectPeaks(ratio, number_of_neighbours)
        self.PeakDetection.analyzePeaks()
        self.PeakDetection.calculateTimeIntervals()
                
    def get_peaks(self):
        return self.PeakDetection.sorted_peaks
        
    def get_peakstatistics(self):
        return self.PeakDetection.peakstatistics
        
    def get_peaktime_intervals(self):
        return self.PeakDetection.time_intervals
    
    def get_bpm(self):
        return self.PeakDetection.bpm
    
    def export_peaks(self):
        self.PeakDetection.export_peaks(self.results_folder)
    
    def exportEKG_CSV(self):
        self.PeakDetection.exportEKG_CSV(self.results_folder)
    
    def exportStatistics(self):
        self.PeakDetection.exportStatistics(self.results_folder, self.inputpath, self.MV_parameters["blockwidth"], self.MV_parameters["delay"], self.videoMeta["fps"], self.MV_parameters["max_shift"], self.scalingfactor)#results_folder, inputpath, blockwidth, delay, fps, maxShift, scalingfactor):
    
    def plot_beatingKinetics(self, mark_peaks = False, filename=None):
        if filename is None:
            filename=self.results_folder + 'beating_kinetics.png'
        plotfunctions.plot_Kinetics(self.timeindex, self.mean_absMotions, self.PeakDetection.sorted_peaks, mark_peaks, filename)
    
    def calc_TimeAveragedMotion(self):
        """
            calculates time averaged motion for abs. motion x- and y-motion
        """
        
        self.avg_absMotion = np.nanmean(self.absMotions, axis = 0)
        MotionX = self.unitMVs[:,0,:,:]
        MotionY = self.unitMVs[:,1,:,:]    #squeeze not necessary anymore, dimension reduced
        
        absMotionX = np.abs(MotionX)    #calculate mean of absolute values!
        self.avg_MotionX = np.nanmean(absMotionX, axis = 0)

        absMotionY = np.abs(MotionY)
        self.avg_MotionY = np.nanmean(absMotionY, axis = 0)

        self.max_avgMotion = np.max ([self.avg_absMotion, self.avg_MotionX, self.avg_MotionY])    
    
    def plot_TimeAveragedMotions(self, file_ext):
        plotfunctions.plot_TimeAveragedMotions(self.avg_absMotion, self.avg_MotionX, self.avg_MotionY, self.max_avgMotion, self.results_folder, file_ext)
               
            
if __name__ == "__main__":
    OHW = OHW()
    #OHW.read_imagestack("..//sampleinput")
    #OHW.read_imagestack("..//sampleinput//samplemov.mov")
    OHW.read_imagestack("..//sampleinput//sampleavi.avi")
    OHW.scale_ImageStack()
    OHW.calculate_MVs(blockwidth = 16, delay = 2, max_shift = 7)