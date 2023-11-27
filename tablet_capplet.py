from __future__ import division
from __future__ import print_function
############################################################################
##
## Copyright (C) 2007 Alexander Macdonald. All rights reserved.
##
## Modified by QB89Dragon 2009 for inclusion to pen tablet utility
##
## This program is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License version 2
##
## Graphics Tablet Applet
##
############################################################################

from builtins import str
from builtins import range
from builtins import object
from past.utils import old_div
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GObject
import cairo
import subprocess
import math


def GetPressCurve(devicename):
    command = ["xsetwacom", "get", devicename, "PressureCurve"]
    output = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0]
    bits = output.strip().split()
    return [float(x) for x in bits]


def SetPressCurve(devicename, points):
    command = ["xsetwacom", "set", devicename, "PressureCurve", str(points[0]), str(points[1]), str(points[2]), str(points[3])]
    output = subprocess.Popen(command)


def GetClickForce(devicename):
    command = ["xsetwacom", "get", devicename, "Threshold"]
    output = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0]
    return float(output.strip())


def SetClickForce(devicename, force):
    command = ["xsetwacom", "set", devicename, "Threshold", str(force)]
    output = subprocess.Popen(command)


def GetMode(devicename):
    command = ["xsetwacom", "get", devicename, "Mode"]
    output = subprocess.Popen(command, stdout=subprocess.PIPE).communicate()[0]
    return output.strip()


def SetMode(devicename, m):
    command = ["xsetwacom", "set", devicename, "Mode", str(m)]
    output = subprocess.Popen(command)


class PressureCurveWidget(Gtk.DrawingArea):
    def __init__(self):
        GObject.GObject.__init__(self)

        self.Points = [0,100,100,0]
        self.Pressure = 0.0

        self.Radius = 5.0
        self.ControlPointStroke = 2.0
        self.ControlPointDiameter = (self.Radius * 2) + self.ControlPointStroke
        self.WindowSize = None
        self.Scale = None

        self.ClickForce = None

        self.DeviceName = ""

        self.DraggingCP1 = False
        self.DraggingCP2 = False
        self.DraggingCF = False

        self.set_events(Gdk.EventMask.POINTER_MOTION_MASK  | Gdk.EventMask.BUTTON_MOTION_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK | Gdk.EventMask.BUTTON2_MOTION_MASK | Gdk.EventMask.BUTTON3_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)

        self.connect("configure-event", self.ConfigureEvent)
        self.connect("expose-event", self.ExposeEvent)
        self.connect("motion-notify-event", self.MotionEvent)
        self.connect("button-press-event", self.ButtonPress)
        self.connect("button-release-event", self.ButtonRelease)
        self.set_size_request(100,100)

    def SetDevice(self, name):
        self.DeviceName = name
        self.ClickForce = GetClickForce(name)

        if self.ClickForce:
            self.ClickForce *= (100.0 / 19.0)

        points = GetPressCurve(name)
        if not points:
            self.Points = None
        else:
            self.Points = [points[0], 100.0 - points[1], points[2], 100.0 - points[3]]

    def Update(self):
        if not isinstance(self.window, Gdk.Window):
            return
        self.window.invalidate_region(self.window.get_clip_region(), True)

    def ClampValue(self, v):
        if v < 0.0:
            return 0.0
        elif v > 100.0:
            return 100.0
        else:
            return v

    def ConfigureEvent(self, widget, event):
        self.WindowSize = self.window.get_size()
        self.Scale = ((self.WindowSize[0] - self.ControlPointDiameter)/ 100.0, (self.WindowSize[1] - self.ControlPointDiameter) / 100.0)

    def MotionEvent(self, widget, event):
        pos = event.get_coords()
        pos = (old_div(pos[0], self.Scale[0]), old_div(pos[1], self.Scale[1]))

        if not self.Points:
            return

        if self.DraggingCP1:
            self.Points[0] = self.ClampValue(pos[0])
            self.Points[1] = self.ClampValue(pos[1])

        elif self.DraggingCP2:
            self.Points[2] = self.ClampValue(pos[0])
            self.Points[3] = self.ClampValue(pos[1])

        elif self.DraggingCF:
            self.ClickForce = int(old_div(self.ClampValue(pos[0]), (100.0 / 19))) * (100.0 / 19)

    def ButtonPress(self, widget, event):
        if not self.Points:
            return

        if self.DraggingCP1 or self.DraggingCP2 or self.DraggingCF:
            self.DragFinished()
        else:
            pos = event.get_coords()
            pos = (old_div(pos[0], self.Scale[0]), old_div(pos[1], self.Scale[1]))

            if (self.Points[0] - self.ControlPointDiameter) < pos[0] < (self.Points[0] + self.ControlPointDiameter):
                if (self.Points[1] - self.ControlPointDiameter) < pos[1] < (self.Points[1] + self.ControlPointDiameter):
                    self.DraggingCP1 = True
                    return

            if self.Points[2] - self.ControlPointDiameter < pos[0] < self.Points[2] + self.ControlPointDiameter:
                if self.Points[3] - self.ControlPointDiameter < pos[1] < self.Points[3] + self.ControlPointDiameter:
                    self.DraggingCP2 = True
                    return

            if self.ClickForce - self.ControlPointDiameter < pos[0] < self.ClickForce + self.ControlPointDiameter:
                self.DraggingCF = True
                return

    def ButtonRelease(self, widget, event):
        self.DragFinished()

    def DragFinished(self):
        if self.Points:
            if self.DraggingCP1:	# Update to new curve constraints
                self.Points[3] = self.Points[0]
                self.Points[2] = self.Points[1]
            elif self.DraggingCP2:
                self.Points[0] = self.Points[3]
                self.Points[1] = self.Points[2]
            print((int(self.Points[0]), int(100.5 - self.Points[1]), int(self.Points[2]), int(100.5 - self.Points[3])))

            SetPressCurve(self.DeviceName, [int(self.Points[0]+.5), int(100.5 - self.Points[1]), int(self.Points[2]+.5), int(100.5 - self.Points[3])])
        if self.ClickForce:
            SetClickForce(self.DeviceName, int(old_div(self.ClickForce, (100.0 / 19.0))) + 1)
        self.DraggingCP1 = self.DraggingCP2 = self.DraggingCF = False

    def ExposeEvent(self, widget, event):
        cr = widget.window.cairo_create()
        cr.set_line_cap(cairo.LINE_CAP_ROUND);

        cr.save()
        cr.translate(self.ControlPointDiameter / 2.0, self.ControlPointDiameter / 2.0)

        # Grid
        cr.set_line_width(0.5)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.25)
        cr.save()
        cr.scale(self.Scale[0], self.Scale[1])
        cr.new_path()
        for x in range(11):
            cr.move_to(x * 10.0, 0.0)
            cr.line_to(x * 10.0, 100.0)
        for y in range(11):
            cr.move_to(0.0, y * 10.0)
            cr.line_to(100.0, y * 10.0)
        cr.restore()
        cr.stroke()

        if self.Pressure:
            # Linear Line
            cr.set_line_width(1.0)

            cr.save()
            cr.scale(self.Scale[0], self.Scale[1])
            cr.new_path()
            cr.move_to(0.0, 100.0)
            cr.line_to(100.0, 0.0)
            cr.restore()
            cr.stroke()

            # Click Force
            if self.ClickForce:
                cr.set_line_width(1.0)
                cr.set_source_rgba(1.0, 0.0, 0.0, 0.25)
                cr.save()
                cr.scale(self.Scale[0], self.Scale[1])
                cr.new_path()
                cr.move_to(self.ClickForce, 0.0)
                cr.line_to(self.ClickForce, 100.0)
                cr.restore()
                cr.stroke()

            if self.Points:
                points = [0.0, 100.0, 100.0, 0.0]
            else:
                points = self.Points

            # Pressure
            cr.save()
            cr.scale(self.Scale[0], self.Scale[1])
            cr.rectangle(0.0, 0.0, self.Pressure * 100.0, 100.0)
            cr.clip()
            cr.new_path()
            cr.set_source_rgba(114.0 / 255.0, 159.0 / 255.0, 207.0 / 255.0, 0.5)
            cr.move_to(0.0,100.0)
            cr.curve_to(points[0], points[1], points[2], points[3], 100.0, 0.0)
            cr.line_to(100.0, 100.0)
            cr.fill()
            cr.restore()

            # Pressure Curve
            cr.set_line_width(2.0)
            cr.set_source_rgba(32.0 / 255.0, 74.0 / 255.0, 135.0 / 255.0, 1.0)
            cr.save()
            cr.scale(self.Scale[0], self.Scale[1])
            cr.new_path()
            cr.move_to(0.0,100.0)
            cr.curve_to(points[0], points[1], points[2], points[3], 100.0, 0.0)
            cr.restore()
            cr.stroke()

            if self.Points:
                # Control Lines
                cr.set_line_width(2.0)
                cr.set_source_rgba(0.0, 0.0, 0.0, 0.5)
                cr.save()
                cr.scale(self.Scale[0], self.Scale[1])
                cr.move_to(0.0,100.0)
                cr.line_to(self.Points[0], self.Points[1])
                cr.move_to(100.0,0.0)
                cr.line_to(self.Points[2], self.Points[3])
                cr.restore()
                cr.stroke()

                # Control Points
                cr.set_line_width(2.0)
                cr.save()
                cr.arc(self.Points[0] * self.Scale[0], self.Points[1] * self.Scale[1], self.Radius, 0.0, 2.0 * math.pi)
                cr.set_source_rgba(237.0 / 255.0, 212.0 / 255.0, 0.0, 0.5)
                cr.fill_preserve()
                cr.set_source_rgba(239.0 / 255.0, 41.0 / 255.0, 41.0 / 255.0, 1.0)
                cr.stroke()
                cr.arc(self.Points[2] * self.Scale[0], self.Points[3] * self.Scale[1], self.Radius, 0.0, 2.0 * math.pi)
                cr.set_source_rgba(237.0 / 255.0, 212.0 / 255.0, 0.0, 0.5)
                cr.fill_preserve()
                cr.set_source_rgba(239.0 / 255.0, 41.0 / 255.0, 41.0 / 255.0, 1.0)
                cr.stroke()
                cr.restore()
        cr.restore()


class DrawingTestWidget(Gtk.DrawingArea):
    def __init__(self):
        GObject.GObject.__init__(self)

        self.Device = 0
        self.Radius = 5.0
        self.Drawing = False
        self.WindowSize = None
        self.Raster = None
        self.RasterCr = None

        self.set_events(Gdk.EventMask.POINTER_MOTION_MASK  | Gdk.EventMask.BUTTON_MOTION_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK | Gdk.EventMask.BUTTON2_MOTION_MASK | Gdk.EventMask.BUTTON3_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)

        self.connect("configure-event", self.ConfigureEvent)
        self.connect("expose-event", self.ExposeEvent)
        self.connect("motion-notify-event", self.MotionEvent)
        self.connect("button-press-event", self.ButtonPress)
        self.connect("button-release-event", self.ButtonRelease)
        self.set_size_request(100,100)

    def ConfigureEvent(self, widget, event):
        self.WindowSize = self.window.get_size()
        self.Raster = self.window.cairo_create().get_target().create_similar(cairo.CONTENT_COLOR, self.WindowSize[0], self.WindowSize[1])
        self.RasterCr = cairo.Context(self.Raster)
        self.RasterCr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        self.RasterCr.rectangle(0.0, 0.0, self.WindowSize[0], self.WindowSize[1])
        self.RasterCr.fill()

    def GetPressure(self):
        dev = Gdk.devices_list()[self.Device]
        state = dev.get_state(self.window)
        return dev.get_axis(state[0], Gdk.AXIS_PRESSURE)

    def MotionEvent(self, widget, event):
        if self.Drawing:
            pos = event.get_coords()
            p = self.GetPressure()
            if not p:
                p = 0.0
            r = p * 50 + 5
            self.RasterCr.set_line_width(2)
            self.RasterCr.set_source_rgba(p, 1.0, 0.0, 0.5)
            self.RasterCr.arc(pos[0], pos[1], r, 0.0, 2 * math.pi)
            self.RasterCr.fill_preserve()
            self.RasterCr.set_source_rgba(0.5, 0.2, p, 0.5)
            self.RasterCr.stroke()
            reg = Gdk.Region()
            reg.union_with_rect((int(pos[0] - r - 2), int(pos[1] - r - 2), int(2 * (r + 2)), int(2 * (r + 2))))
            self.window.invalidate_region(reg, False)

    def ButtonPress(self, widget, event):
        self.Drawing = True

    def ButtonRelease(self, widget, event):
        self.Drawing = False

    def ExposeEvent(self, widget, event):
        cr = widget.window.cairo_create()
        cr.set_source_surface(self.Raster, 0.0, 0.0)
        cr.paint()
        cr.set_line_width(2)
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.25)
        cr.rectangle(0.0, 0.0, self.WindowSize[0], self.WindowSize[1])
        cr.stroke()


class GraphicsTabletApplet(object):
    def __init__(self, window, wTree, Device):
        self.Active = 0  # Control
        self.InLoop = 0  # Flag
        self.WidgetTree = wTree
        self.MainWindow = window
        self.DrawingTestFrame = self.WidgetTree.get_object("drawingalignment")
        self.PressureVBox = self.WidgetTree.get_object("pressurevbox")
        self.DeviceModeCombo = self.WidgetTree.get_object("devicemodecombo")
        self.XTilt = self.WidgetTree.get_object("xtilt")
        self.YTilt = self.WidgetTree.get_object("ytilt")

        self.Curve = PressureCurveWidget()
        self.Curve.show()
        self.PressureVBox.add(self.Curve)

        self.DrawingArea = DrawingTestWidget()
        self.DrawingArea.show()
        self.DrawingTestFrame.add(self.DrawingArea)

        devices = Gdk.devices_list()

        for i in range(0,len(devices)):
            item = devices[i].name
            if item in Device:
                self.Device = i
        self.DeviceMode = None
        self.DeviceName = Device

        self.DrawingArea.Device = self.Device
        self.DeviceName = Gdk.devices_list()[self.Device].name
        self.Curve.SetDevice(self.DeviceName)
        self.UpdateDeviceMode()

        self.DeviceModeCombo.connect("changed", self.ModeChanged)

        self.DrawingArea.set_extension_events(Gdk.EXTENSION_EVENTS_ALL)

    def Run(self):
        self.Active = 1
        self.InLoop = 1
        self.DeviceName = Gdk.devices_list()[self.Device].name
        self.UpdateDeviceMode()
        GObject.timeout_add(20, self.Update)

    def Stop(self):
        self.Active = 0

    def GetPressure(self):
        dev = Gdk.devices_list()[self.Device]
        if not isinstance(self.DrawingArea.window, Gdk.Window):
            return 0.0, 0.0
        state = dev.get_state(self.DrawingArea.window)
        return dev.get_axis(state[0], Gdk.AXIS_PRESSURE)

    def GetTilt(self):
        dev = Gdk.devices_list()[self.Device]
        state = dev.get_state(self.MainWindow.window)
        try:
            x = float(dev.get_axis(state[0], Gdk.AXIS_XTILT))
            y = float(dev.get_axis(state[0], Gdk.AXIS_YTILT))
            return x, y
        except:
            return 0.0, 0.0

    def ModeChanged(self, widget):
        SetMode(self.DeviceName, widget.get_active_text())

    def UpdateDeviceMode(self):
        self.DeviceMode = GetMode(self.DeviceName)
        if not self.DeviceMode:
            self.DeviceModeCombo.set_sensitive(False)
        else:
            self.DeviceModeCombo.set_sensitive(True)
            if self.DeviceMode == "Relative":
                self.DeviceModeCombo.set_active(0)
            elif self.DeviceMode == "Absolute":
                self.DeviceModeCombo.set_active(1)

    def DeviceSelected(self, widget):
        self.Device = widget.get_active()
        self.DrawingArea.Device = self.Device
        self.DeviceName = Gdk.devices_list()[self.Device].name
        self.Curve.SetDevice(self.DeviceName)
        self.UpdateDeviceMode()

    def Update(self):
        p = self.GetPressure()
        if not p:
            self.Curve.Pressure = None
            self.Curve.Update()
        else:
            self.Curve.Pressure = p
            self.Curve.Update()

        t = self.GetTilt()

        self.XTilt.set_adjustment(Gtk.Adjustment(t[0], -1.0, 1.0))
        self.YTilt.set_adjustment(Gtk.Adjustment(t[1], -1.0, 1.0))
        if self.Active:
            return True
        else:
            self.InLoop = 0

