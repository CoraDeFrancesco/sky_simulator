#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  9 15:07:00 2023

@author: cdefran

Sky Simulator based on kalstar.py
Use Stellarium to create an image of the sky at a given 
    date, time, and location.
"""

## ---------------------------------------------------------------------------
## Imports ###################################################################
## ---------------------------------------------------------------------------

import numpy as np
import matplotlib.pyplot as plt
import os
import tempfile
import shutil
from datetime import datetime, time, timedelta
#from math import cos, sin, acos, asin, tan
#from math import degrees as deg, radians as rad
from pathlib import Path
import subprocess
import time as xxx

## ---------------------------------------------------------------------------
## Setup #####################################################################
## ---------------------------------------------------------------------------

frame_folder = 'sky_out'
lat = 35.2226
long = -97.4395
title = '20230213'
year = 2023 
month = 2
day = 13
hour = 23 # time in local time for given coordinates
            # (be smart... pick sometime at night...)
minute = 00
second = 00
fov = 33.6 # degrees
az = 30 # Azimuth in degrees (View direction)
alt = 90 # Altitude of the center of the field of view


## ---------------------------------------------------------------------------
## Functions #################################################################
## ---------------------------------------------------------------------------


class StellariumToPng:
    __args = None
    __frame_folder = '/Applications/Stellarium.app/Contents/Resources/save_frames'
    __script = """
    // Author: Ingo Berg
    // Version: 1.0
    // License: Public Domain
    // Name: Kaleidoskop Sternenhimmel
    // Description: Berechnung des Sternenhimmels

    param_frame_folder = "$FRAME_FOLDER$"
    param_az = $AZ$
    param_alt = $ALT$
    param_lat = $LAT$
    param_long = $LONG$
    param_title = "$TITLE$"
    param_date = "$DATE$"
    param_fov = $FOV$
    
    function get_frame(date, file_prefix, caption, long, lat, alt, azi)
    {
        core.setDate(date, "local");
        core.setObserverLocation(long, lat, 425, 1, "Freiberg", "Earth");
        core.wait(0.5);

        core.moveToAltAzi(alt, azi)
        core.wait(0.5);

        label = LabelMgr.labelScreen(caption, 70, 40, false, 40, "#aa0000");
        LabelMgr.setLabelShow(label, true);

        labelTime = LabelMgr.labelScreen("", 70, 90, false, 25, "#aa0000");
        LabelMgr.setLabelShow(labelTime, true);

        core.wait(0.5);
        
        //LabelMgr.setLabelText(labelTime, core.getDate(""));
        core.wait(0.5);
        
        LabelMgr.deleteAllLabels();
        
        core.wait(0.5);
        
        core.screenshot("invert_", invert=true)
        core.screenshot(file_prefix, invert=false);
        
        core.wait(0.5);
        
        
    }

    core.setTimeRate(0); 
    core.setGuiVisible(false);
    //core.setMilkyWayVisible(true);
    //core.setMilkyWayIntensity(4);

    SolarSystem.setFlagPlanets(false);
    SolarSystem.setMoonScale(6);
    SolarSystem.setFlagMoonScale(true);
    SolarSystem.setFontSize(25);
    
    StelSkyDrawer.setFlagStarMagnitudeLimit(true);
    StelSkyDrawer.setCustomStarMagnitudeLimit(4);
    StelSkyDrawer.setAbsoluteStarScale(1);
    StelSkyDrawer.setRelativeStarScale(1);

    StarMgr.setFontSize(20);
    StarMgr.setLabelsAmount(0);

    ConstellationMgr.setFlagLines(false);
    ConstellationMgr.setFlagLabels(false);
    ConstellationMgr.setArtIntensity(0.0);
    ConstellationMgr.setFlagArt(false);
    ConstellationMgr.setFlagBoundaries(false);
    ConstellationMgr.setConstellationLineThickness(0);
    ConstellationMgr.setFontSize(18);

    //LandscapeMgr.setCurrentLandscapeName("Hurricane Ridge");
    LandscapeMgr.setFlagAtmosphere(false);

    StelMovementMgr.zoomTo(param_fov, 0);
    core.wait(0.5);

    get_frame(param_date, "frame_", param_title, param_long, param_lat, param_alt, param_az)
    core.screenshot("final", invert=false, dir=param_frame_folder, overwrite=true);
    // core.setGuiVisible(true);
    core.quitStellarium();"""

    def __init__(self, args_dict):
        self.__args = args_dict
        self.__frame_folder =args_dict['frame_folder'].format(tempfile.gettempdir())
        self.__final_file = self.__frame_folder + "/final.png";

        # Create frame folder if it not already exists
        if os.path.exists(self.__frame_folder):
            shutil.rmtree(self.__frame_folder)

        os.mkdir(self.__frame_folder);

    def __addSecs(self, tm, secs):
        fulldate = datetime(100, 1, 1, tm.hour, tm.minute, tm.second)
        fulldate = fulldate + timedelta(seconds=secs)
        return fulldate.time()

    def create_script(self):

        # Sonnenuntergangszeit berechnen:
        # s = sun(lat=self.__args["lat"], long=self.__args["long"])
        # sunset_time = s.sunset(self.__args["date"])
        # sunset_time = self.__addSecs(sunset_time, 3600)
        # sunset_date = "{0}T{1}".format(self.__args['date'].strftime("%Y-%m-%d"), sunset_time.strftime("%H:%M:%S"))
        # print("Sonnenuntergang: {0}".format(sunset_date))

        # Ersetzen der Skriptvariablen
        script = self.__script;
        script = script.replace("$FRAME_FOLDER$", self.__frame_folder);
        script = script.replace("$LAT$", str(self.__args['lat']));
        script = script.replace("$LONG$", str(self.__args['long']));
        script = script.replace("$TITLE$", str(self.__args['title']));
        script = script.replace("$DATE$", str(self.__args['date']))
        script = script.replace("$FOV$", str(self.__args['fov']))
        script = script.replace("$AZ$", str(self.__args['az']))
        script = script.replace("$ALT$", str(self.__args['alt']))

        # erzeugen des Sciptes im Stellarium scriptverzeichnis
        # Cora's Edit
        scripts_dir_path = '/Applications/Stellarium.app/Contents/Resources/scripts'
        save_path = scripts_dir_path+'/kalstar.ssc'
        file=open(save_path.format(Path.home()), "w")
        #
        #file = open("{0}/.stellarium/scripts/kalstar.ssc".format(Path.home()), "w")
        file.write(script)
        file.close()

    def create_frames(self):
        proc_stellarium = subprocess.Popen(['/Applications/Stellarium.app/Contents/MacOS/stellarium', '--startup-script', 'kalstar.ssc', '--screenshot-dir', self.__frame_folder], stdout=subprocess.PIPE)
        # proc_stellarium = subprocess.Popen(['stellarium', '--startup-script', 'kalstar.ssc', '--screenshot-dir', self.__frame_folder], stdout=subprocess.PIPE);

        # wait for script finish
        s = 0
        timeout = 600
        while not os.path.exists(self.__final_file) and s < timeout:
            xxx.sleep(1)
            s = s + 1

        proc_stellarium.kill()

## ---------------------------------------------------------------------------
## Execution Section #########################################################
## ---------------------------------------------------------------------------

# Check if there is a local stellarium folder
if not os.path.isdir('/Applications/Stellarium.app/Contents/Resources/'.format(Path.home())):
        print("Stellarium does not seem to be installed!")
# if not os.path.isdir("{0}/.stellarium".format(Path.home())):
#     print("Stellarium does not seem to be installed!")

# if there is no local scripts folder, create one
if not os.path.isdir('/Applications/Stellarium.app/Contents/Resources/'.format(Path.home())):
    os.mkdir('/Applications/Stellarium.app/Contents/Resources/scripts'.format(Path.home()))
# if not os.path.isdir("{0}/.stellarium/scripts".format(Path.home())):
#     os.mkdir("{0}/.stellarium/scripts".format(Path.home()));

args_dict = dict(frame_folder = frame_folder, \
    lat = lat, \
    long = long, \
    title = title, \
    date = datetime(year, month, day, hour, minute, second).isoformat(),  \
    fov = fov, \
    az = az, \
    alt = alt)

sa = StellariumToPng(args_dict)
sa.create_script();
sa.create_frames();

