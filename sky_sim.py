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
## Setup #####################################################################
## ---------------------------------------------------------------------------



## ---------------------------------------------------------------------------
## Imports ###################################################################
## ---------------------------------------------------------------------------

import numpy as np
import matplotlib.pyplot as plt
import os
import tempfile
import shutil
from datetime import datetime, time, timedelta
from math import cos, sin, acos, asin, tan
from math import degrees as deg, radians as rad
from pathlib import Path
import subprocess
import time as xxx

## ---------------------------------------------------------------------------
## Functions #################################################################
## ---------------------------------------------------------------------------

class sun:
    """
    Calculate sunrise and sunset based on equations from NOAA
    http://www.srrb.noaa.gov/highlights/sunrise/calcdetails.html

    typical use, calculating the sunrise at the present day:

    import datetime
    import sunrise
    s = sun(lat=49,long=3)
    print('sunrise at ',s.sunrise(when=datetime.datetime.now())
    """

    def __init__(self, lat=52.37, long=4.90):  # default Amsterdam
        self.lat = lat
        self.long = long

    def sunrise(self, when):
        """
        return the time of sunrise as a datetime.time object
        when is a datetime.datetime object. If none is given
        a local time zone is assumed (including daylight saving
        if present)
        """
        self.__preptime(when)
        self.__calc()
        return sun.__timefromdecimalday(self.sunrise_t)

    def sunset(self, when=None):
        self.__preptime(when)
        self.__calc()
        return sun.__timefromdecimalday(self.sunset_t)

    def solarnoon(self, when=None):
        self.__preptime(when)
        self.__calc()
        return sun.__timefromdecimalday(self.solarnoon_t)

    @staticmethod
    def __timefromdecimalday(day):
        """
        returns a datetime.time object.

        day is a decimal day between 0.0 and 1.0, e.g. noon = 0.5
        """
        hours = 24.0 * day
        h = int(hours)
        minutes = (hours - h) * 60
        m = int(minutes)
        seconds = (minutes - m) * 60
        s = int(seconds)
        return time(hour=h, minute=m, second=s)

    def __preptime(self, when):
        """
        Extract information in a suitable format from when,
        a datetime.datetime object.
        """
        # datetime days are numbered in the Gregorian calendar
        # while the calculations from NOAA are distibuted as
        # OpenOffice spreadsheets with days numbered from
        # 1/1/1900. The difference are those numbers taken for
        # 18/12/2010
        self.day = when.toordinal() - (734124 - 40529)
        t = when.time()
        self.time = (t.hour + t.minute / 60.0 + t.second / 3600.0) / 24.0

        self.timezone = 0
        offset = when.utcoffset()
        if not offset is None:
            self.timezone = offset.seconds / 3600.0

    def __calc(self):
        """
        Perform the actual calculations for sunrise, sunset and
        a number of related quantities.

        The results are stored in the instance variables
        sunrise_t, sunset_t and solarnoon_t
        """
        timezone = self.timezone  # in hours, east is positive
        longitude = self.long  # in decimal degrees, east is positive
        latitude = self.lat  # in decimal degrees, north is positive

        time = self.time  # percentage past midnight, i.e. noon  is 0.5
        day = self.day  # daynumber 1=1/1/1900

        Jday = day + 2415018.5 + time - timezone / 24  # Julian day
        Jcent = (Jday - 2451545) / 36525  # Julian century

        Manom = 357.52911 + Jcent * (35999.05029 - 0.0001537 * Jcent)
        Mlong = 280.46646 + Jcent * (36000.76983 + Jcent * 0.0003032) % 360
        Eccent = 0.016708634 - Jcent * (0.000042037 + 0.0001537 * Jcent)
        Mobliq = 23 + (26 + ((21.448 - Jcent * (46.815 + Jcent * (0.00059 - Jcent * 0.001813)))) / 60) / 60
        obliq = Mobliq + 0.00256 * cos(rad(125.04 - 1934.136 * Jcent))
        vary = tan(rad(obliq / 2)) * tan(rad(obliq / 2))
        Seqcent = sin(rad(Manom)) * (1.914602 - Jcent * (0.004817 + 0.000014 * Jcent)) + sin(rad(2 * Manom)) * (
                    0.019993 - 0.000101 * Jcent) + sin(rad(3 * Manom)) * 0.000289
        Struelong = Mlong + Seqcent
        Sapplong = Struelong - 0.00569 - 0.00478 * sin(rad(125.04 - 1934.136 * Jcent))
        declination = deg(asin(sin(rad(obliq)) * sin(rad(Sapplong))))

        eqtime = 4 * deg(
            vary * sin(2 * rad(Mlong)) - 2 * Eccent * sin(rad(Manom)) + 4 * Eccent * vary * sin(rad(Manom)) * cos(
                2 * rad(Mlong)) - 0.5 * vary * vary * sin(4 * rad(Mlong)) - 1.25 * Eccent * Eccent * sin(
                2 * rad(Manom)))

        hourangle = deg(acos(cos(rad(90.833)) / (cos(rad(latitude)) * cos(rad(declination))) - tan(rad(latitude)) * tan(
            rad(declination))))

        self.solarnoon_t = (720 - 4 * longitude - eqtime + timezone * 60) / 1440
        self.sunrise_t = self.solarnoon_t - hourangle * 4 / 1440
        self.sunset_t = self.solarnoon_t + hourangle * 4 / 1440

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
    param_timespan = $TIMESPAN$
    param_fov = $FOV$
    param_dt=$DELTAT$
    
    function makeVideo(date, file_prefix, caption, hours, long, lat, alt, azi)
    {
        core.setDate(date, "utc");
        core.setObserverLocation(long, lat, 425, 1, "Freiberg", "Earth");
        core.wait(0.5);

        core.moveToAltAzi(alt, azi)
        core.wait(0.5);

        label = LabelMgr.labelScreen(caption, 70, 40, false, 40, "#aa0000");
        LabelMgr.setLabelShow(label, true);

        labelTime = LabelMgr.labelScreen("", 70, 90, false, 25, "#aa0000");
        LabelMgr.setLabelShow(labelTime, true);

        core.wait(0.5);

        max_sec = hours * 60 * 60
        for (var sec = 0; sec < max_sec; sec += param_dt) {
            core.setDate('+' + param_dt + ' seconds');
            LabelMgr.setLabelText(labelTime, core.getDate(""));
            core.wait(0.1);
            core.screenshot(file_prefix);
        }

        LabelMgr.deleteAllLabels();
    }

    core.setTimeRate(0); 
    core.setGuiVisible(false);
    //core.setMilkyWayVisible(true);
    //core.setMilkyWayIntensity(4);

    SolarSystem.setFlagPlanets(true);
    SolarSystem.setMoonScale(6);
    SolarSystem.setFlagMoonScale(true);
    SolarSystem.setFontSize(25);
    
    StelSkyDrawer.setAbsoluteStarScale(1.5);
    StelSkyDrawer.setRelativeStarScale(1.65);

    StarMgr.setFontSize(20);
    StarMgr.setLabelsAmount(3);

    ConstellationMgr.setFlagLines(true);
    ConstellationMgr.setFlagLabels(true);
    ConstellationMgr.setArtIntensity(0.1);
    ConstellationMgr.setFlagArt(true);
    ConstellationMgr.setFlagBoundaries(false);
    ConstellationMgr.setConstellationLineThickness(3);
    ConstellationMgr.setFontSize(18);

    //LandscapeMgr.setCurrentLandscapeName("Hurricane Ridge");
    LandscapeMgr.setFlagAtmosphere(true);

    StelMovementMgr.zoomTo(param_fov, 0);
    core.wait(0.5);

    makeVideo(param_date, "frame_", param_title, param_timespan, param_long, param_lat, param_alt, param_az)
    core.screenshot("final", invert=false, dir=param_frame_folder, overwrite=true);
    core.setGuiVisible(true);
    core.quitStellarium();"""

    def __init__(self, args):
        self.__args = args
        self.__frame_folder ="{0}/kalstar_frames".format(tempfile.gettempdir())
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
        s = sun(lat=self.__args.lat, long=self.__args.long)
        sunset_time = s.sunset(self.__args.date)
        sunset_time = self.__addSecs(sunset_time, 3600)
        sunset_date = "{0}T{1}".format(self.__args.date.strftime("%Y-%m-%d"), sunset_time.strftime("%H:%M:%S"))
        print("Sonnenuntergang: {0}".format(sunset_date))

        # Ersetzen der Skriptvariablen
        script = self.__script;
        script = script.replace("$FRAME_FOLDER$", self.__frame_folder);
        script = script.replace("$LAT$", str(self.__args.lat));
        script = script.replace("$LONG$", str(self.__args.long));
        script = script.replace("$TITLE$", str(self.__args.title));
        script = script.replace("$DATE$", sunset_date)
        script = script.replace("$TIMESPAN$", str(self.__args.timespan))
        script = script.replace("$FOV$", str(self.__args.fov))
        script = script.replace("$DELTAT$", str(self.__args.dt))
        script = script.replace("$AZ$", str(self.__args.az))
        script = script.replace("$ALT$", str(self.__args.alt))

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

sa = StellariumToMpeg(args)
sa.create_script();
sa.create_frames();

