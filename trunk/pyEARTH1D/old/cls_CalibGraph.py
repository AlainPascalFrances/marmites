# -*- coding: iso-8859-1 -*-
# generated by wxGlade 0.5 on Tue May 08 00:19:51 2007 from C:\_alf\MOD9_GEOPROC\ReSo\GUI\ReSo_dialogv1.wxg

import matplotlib
matplotlib.use('WX')
from matplotlib.backends.backend_wx import Toolbar, FigureCanvasWx,\
     FigureManager

from matplotlib.figure import Figure
from matplotlib.axes import Subplot
#import matplotlib.numerix as numpy
import wx



from pylab import *
from matplotlib.dates import MonthLocator, DateFormatter
from matplotlib.ticker import FormatStrFormatter
from sys import *
import os
import datetime

# begin wxGlade: dependencies
# end wxGlade

class cls_CalibGraph(wx.Frame):
    def __init__(self, *args, **kwds):

        wx.Frame.__init__(self, None, -1, "Test ReSo - Calibration graphs")

#        self.fig = Figure((9,8), 75)
        self.fig = Figure()
        self.canvas = FigureCanvasWx(self, -1, self.fig)
        self.toolbar = Toolbar(self.canvas)
        self.toolbar.Realize()

        # On Windows, default frame size behaviour is incorrect
        # you don't need this under Linux
        tw, th = self.toolbar.GetSizeTuple()
        fw, fh = self.canvas.GetSizeTuple()
        self.toolbar.SetSize(wx.Size(fw, th))

        # Create a figure manager to manage things
        self.figmgr = FigureManager(self.canvas, 1, self)
        # Now put all into a sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        # This way of adding to sizer allows resizing
        sizer.Add(self.canvas, 1, wx.LEFT|wx.TOP|wx.GROW)
        # Best to allow the toolbar to resize!
        sizer.Add(self.toolbar, 0, wx.GROW)
        self.SetSizer(sizer)
        self.Fit()

##    def plot_data(self):
##        # Use ths line if using a toolbar
##        a = self.fig.add_subplot(111)
##        
##        # Or this one if there is no toolbar
##        #a = Subplot(self.fig, 111)
##        
##        t = numpy.arange(0.0,3.0,0.01)
##        s = numpy.sin(2*numpy.pi*t)
##        c = numpy.cos(2*numpy.pi*t)
##        a.plot(t,s)
##        a.plot(t,c)
##        self.toolbar.update()

    def calibGRAPH(self, DateInput, S, h, hmeas, Smeas, Sm, Sr):
        """
        calibGRAPH: GRAPH the computed data and the calibration one, that it h and S
        Use Matplotlib
        _______________________________________________________________________________

        INPUTS
                STATE VARIABLES
                    TS              Time step
                    S               Daily soil moisture
                    Smeas           Daily measured soil moisture
                    h               Daily water level
                    hmeas           Daily measured water level
        ______________________________________________________________________________
        ______________________________________________________________________________
        """

        months=MonthLocator()
        monthsFmt=DateFormatter('%y-%m')

    #__________________Create outputs plots______________________#

#        figCalib=figure()
#        figCalib.Title='Calibration graphs'

        ax2=self.fig.add_subplot(212)
        setp( ax2.get_xticklabels(), fontsize=8)
        setp( ax2.get_yticklabels(), fontsize=8)
        ax2.plot_date(DateInput,h,'-')
        ax2.yaxis.set_major_formatter(FormatStrFormatter('%1.1f'))
        labels=ax2.get_yticklabels()
        setp(labels, 'rotation', 90)
        ax2.xaxis.set_major_locator(months)
        ax2.xaxis.set_major_formatter(monthsFmt)
        xlim((DateInput[0],DateInput[len(S)-1]))
        hmax=hmin=h[0]
        labels=ax2.get_xticklabels()
        setp(labels, 'rotation', 90)
        for i in range(0,len(DateInput)):
            if h[i]>hmax:
                hmax=h[i]
            elif h[i]<hmin:
                hmin=h[i]
        ax2.plot_date(DateInput,hmeas,'mo', markersize=4)
        if hmeas[0]==-999:
            hmmax=-999
            hmmin=999
        else:
            hmmax=hmmin=hmeas[0]
        for i in range(0,len(DateInput)):
            if hmeas[i]!=-999:
                if hmeas[i]>hmmax:
                    hmmax=h[i]
                if hmeas[i]<hmmin:
                    hmmin=h[i]
        if hmin>hmmin:
            hmin=hmmin
        if hmax<hmmax:
            hmax=hmmax
        ybuffer=0.1*(hmax-hmin)
        ylim((hmin - ybuffer, hmax + ybuffer))
        ax2yaxis.set_major_formatter(FormatStrFormatter('%.1f'))
        ylabel('m') 
        legend((r'h',r'hmeas'), loc=0)
        leg = gca().get_legend()
        ltext  = leg.get_texts()  # all the text.Text instance in the legend
        setp(ltext, fontsize='small')    # the legend text fontsize
        xlabel(r'Date')
        grid(True)

        ax1=self.fig.add_subplot(211, sharex=ax2)
        setp( ax1.get_xticklabels(), visible=False)
        setp( ax1.get_yticklabels(), fontsize=8)
        ax1.plot_date(DateInput,S, '-')
        ax1.plot_date(DateInput, Smeas, 'mo', markersize=4)
        legend((r'S',r'Smeas'), loc=0)
        leg = gca().get_legend()
        ltext  = leg.get_texts()  # all the text.Text instance in the legend
        setp(ltext, fontsize='small')    # the legend text fontsize
#        ybuffer=0.1*(float(Sm)-float(Sr))
#        ylim((float(Sr) - ybuffer,float(Sm) + ybuffer))
        ylim(0,1)
        ylabel('mm') 
        ax1.yaxis.set_major_formatter(FormatStrFormatter('%1.2f'))
        labels=ax1.get_yticklabels()
        setp(labels, 'rotation', 90)
        grid(True)

#        subplots_adjust(left=0.05, bottom=0.1, right=0.95, top=0.95, wspace=0.1, hspace=0.05)

    def GetToolBar(self):
        # You will need to override GetToolBar if you are using an 
        # unmanaged toolbar in your frame
        return self.toolbar

# end of class cls_CalibGraph

def calibGRAPH(DateInput, S, h, hmeas, Smeas, Sm, Sr):
#    app = wxPySimpleApp(0)
    frame = cls_CalibGraph()
    frame.calibGRAPH(DateInput, S, h, hmeas, Smeas, Sm, Sr)
    frame.Show()
#    app.MainLoop()
