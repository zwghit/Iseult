#!/usr/bin/env pythonw
import Tkinter as Tk
import ttk as ttk
import matplotlib
import numpy as np
import numpy.ma as ma
import new_cmaps
import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
import matplotlib.patheffects as PathEffects

class EnergyPanel:
    # A dictionary of all of the parameters for this plot with the default parameters

    plot_param_dict = {'twoD' : 1,
                       'masked': 1,
                       'cnorm_type': 'Log',
                       'prtl_type': 0,
                       'show_cbar': True,
                       'weighted': False,
                       'show_shock': False,
                       'show_int_region': True,
                       'set_color_limits': False,
                       'xbins' : 200,
                       'ebins' : 200,
                       'v_min': -2.0,
                       'v_max' : 0,
                       'set_v_min': False,
                       'set_v_max': False,
                       'set_E_min' : False,
                       'E_min': 1.0,
                       'set_E_max': False,
                       'E_max': 200.0,
                       'spatial_x': True,
                       'spatial_y': False,
                       'interpolation': 'hermite'}
    prtl_opts = ['proton', 'electron']
    gradient =  np.linspace(0, 1, 256)# A way to make the colorbar display better
    gradient = np.vstack((gradient, gradient))

    def __init__(self, parent, figwrapper):

        self.settings_window = None
        self.FigWrap = figwrapper
        self.parent = parent
        self.ChartTypes = self.FigWrap.PlotTypeDict.keys()
        self.chartType = self.FigWrap.chartType
        self.figure = self.FigWrap.figure
        self.InterpolationMethods = ['nearest', 'bilinear', 'bicubic', 'spline16',
            'spline36', 'hanning', 'hamming', 'hermite', 'kaiser', 'quadric',
            'catrom', 'gaussian', 'bessel', 'mitchell', 'sinc', 'lanczos']


    def ChangePlotType(self, str_arg):
        self.FigWrap.ChangeGraph(str_arg)

    def norm(self, vmin=None,vmax=None):
        if self.GetPlotParam('cnorm_type') == 'Log':
            return  mcolors.LogNorm(vmin, vmax)
        else:
            return mcolors.Normalize(vmin, vmax)


    def set_plot_keys(self):
        '''A helper function that will insure that each hdf5 file will only be
        opened once per time step'''
        self.arrs_needed = ['c_omp', 'bx', 'istep', 'me', 'mi']
        # First see if we will need to know the energy of the particle
        # (requied for lorentz boosts and setting e_min and e_max)
        if self.GetPlotParam('prtl_type') == 0:
            self.arrs_needed.append('xi')
            if self.GetPlotParam('weighted'):
                self.arrs_needed.append('chi')
            self.arrs_needed.append('ui')
            self.arrs_needed.append('vi')
            self.arrs_needed.append('wi')

        if self.GetPlotParam('prtl_type') == 1:
            self.arrs_needed.append('xe')
            if self.GetPlotParam('weighted'):
                self.arrs_needed.append('che')
            self.arrs_needed.append('ue')
            self.arrs_needed.append('ve')
            self.arrs_needed.append('we')

        return self.arrs_needed

    def LoadData(self):
        ''' A helper function that checks if the histogram has
        already been calculated and if it hasn't, it calculates
        it then stores it.'''
        self.key_name = 'Energy_'
        if self.GetPlotParam('masked'):
            self.key_name += 'masked_'

        if self.GetPlotParam('weighted'):
            self.key_name += 'weighted_'

        self.key_name += self.prtl_opts[self.GetPlotParam('prtl_type')]

        if self.key_name in self.parent.DataDict.keys():
            self.hist2d = self.parent.DataDict[self.key_name]

        else:
            # Generate the X-axis values
            self.c_omp = self.FigWrap.LoadKey('c_omp')[0]
            self.istep = self.FigWrap.LoadKey('istep')[0]
            self.weights = None
            self.x_values = None
            self.y_values = None

            # Choose the particle type and px, py, or pz
            if self.GetPlotParam('prtl_type') == 0: #protons
                self.energy_color = self.parent.ion_color
                self.x_values = self.FigWrap.LoadKey('xi')/self.c_omp
                if self.GetPlotParam('weighted'):
                    self.weights = self.FigWrap.LoadKey('chi')

                u = self.FigWrap.LoadKey('ui')
                v = self.FigWrap.LoadKey('vi')
                w = self.FigWrap.LoadKey('wi')

            if self.GetPlotParam('prtl_type') == 1: #electons
                self.energy_color = self.parent.electron_color
                self.x_values = self.FigWrap.LoadKey('xe')/self.c_omp

                if self.GetPlotParam('weighted'):
                    self.weights = self.FigWrap.LoadKey('che')
                u = self.FigWrap.LoadKey('ue')
                v = self.FigWrap.LoadKey('ve')
                w = self.FigWrap.LoadKey('we')

            self.y_values = np.sqrt(u**2+v**2+w**2+1)
            if self.GetPlotParam('prtl_type') == 1:
                self.y_values *= self.FigWrap.LoadKey('me')[0]/self.FigWrap.LoadKey('mi')[0]
            self.pmin = min(self.y_values)
            self.pmax = max(self.y_values)


            self.xmin = 0
            self.xmax = self.FigWrap.LoadKey('bx').shape[2]/self.c_omp*self.istep

            self.hist2d = np.histogram2d(self.y_values, self.x_values,
                            bins = [self.GetPlotParam('ebins'), self.GetPlotParam('xbins')],
                            range = [[self.pmin,self.pmax],[0,self.xmax]],
                            weights = self.weights)

            if self.GetPlotParam('masked'):
                zval = ma.masked_array(self.hist2d[0])
                zval[zval == 0] = ma.masked
                zval *= float(zval.max())**(-1)
                tmplist = [zval[~zval.mask].min(), zval.max()]
            else:
                zval = np.copy(self.hist2d[0])
                zval[zval==0] = 0.5
                zval *= float(zval.max())**(-1)
                tmplist = [zval.min(), zval.max()]

            self.hist2d = zval, self.hist2d[1], self.hist2d[2], tmplist
            self.parent.DataDict[self.key_name] = self.hist2d

    def UpdateLabelsandColors(self):
        '''
        if self.parent.DoLorentzBoost and np.abs(self.parent.GammaBoost)>1E-8:
            self.x_label = r'$x\prime\ [c/\omega_{\rm pe}]$'
            if self.GetPlotParam('prtl_type') == 0: #protons
                self.energy_color = self.parent.ion_color
                if self.GetPlotParam('mom_dim') == 0:
                    self.y_label  = r'$P\prime_{px}\ [m_i c]$'
                if self.GetPlotParam('mom_dim') == 1:
                    self.y_label  = r'$P\prime_{py}\ [m_i c]$'
                if self.GetPlotParam('mom_dim') == 2:
                    self.y_label  = r'$P\prime_{pz}\ [m_i c]$'

            if self.GetPlotParam('prtl_type') == 1: #electons
                self.energy_color = self.parent.electron_color
                if self.GetPlotParam('mom_dim') == 0:
                    self.y_label  = r'$P\prime_{ex}\ [m_e c]$'
                if self.GetPlotParam('mom_dim') == 1:
                    self.y_label  = r'$P\prime_{ey}\ [m_e c]$'
                if self.GetPlotParam('mom_dim') == 2:
                    self.y_label  = r'$P\prime_{ez}\ [m_e c]$'

        else:
        '''
        self.x_label = r'$x\ [c/\omega_{\rm pe}]$'

        if self.GetPlotParam('prtl_type') == 0: #protons
            self.energy_color = self.parent.ion_color
            self.y_label  = r'$E_p\ [m_i c]$'

        if self.GetPlotParam('prtl_type') == 1: #electons
            self.energy_color = self.parent.electron_color
            self.y_label  = r'$E_{e}\ [m_i c]$'

    def draw(self):
        # In order to speed up the plotting, we only recalculate everything
        # if necessary.

        # Figure out the color and ylabel
        # Choose the particle type and px, py, or pz
        self.UpdateLabelsandColors()

        self.xmin = self.hist2d[2][0]
        self.xmax = self.hist2d[2][-1]

        self.ymin = self.hist2d[1][0]
        self.ymax = self.hist2d[1][-1]


        if self.GetPlotParam('masked'):
            self.tick_color = 'k'
        else:
            self.tick_color = 'white'


        self.clim = list(self.hist2d[3])
        print self.clim
        if self.GetPlotParam('set_v_min'):
            self.clim[0] = 10**self.GetPlotParam('v_min')
        if self.GetPlotParam('set_v_max'):
            self.clim[1] = 10**self.GetPlotParam('v_max')


        self.gs = gridspec.GridSpecFromSubplotSpec(100,100, subplot_spec = self.parent.gs0[self.FigWrap.pos])#, bottom=0.2,left=0.1,right=0.95, top = 0.95)

        if self.parent.LinkSpatial == 1:
            if self.FigWrap.pos == self.parent.first_x:
                self.axes = self.figure.add_subplot(self.gs[self.parent.axes_extent[0]:self.parent.axes_extent[1], self.parent.axes_extent[2]:self.parent.axes_extent[3]])
            else:
                self.axes = self.figure.add_subplot(self.gs[self.parent.axes_extent[0]:self.parent.axes_extent[1], self.parent.axes_extent[2]:self.parent.axes_extent[3]], sharex = self.parent.SubPlotList[self.parent.first_x[0]][self.parent.first_x[1]].graph.axes)
        else:
            self.axes = self.figure.add_subplot(self.gs[self.parent.axes_extent[0]:self.parent.axes_extent[1], self.parent.axes_extent[2]:self.parent.axes_extent[3]])
        self.cax = self.axes.imshow(self.hist2d[0],
                                    cmap = new_cmaps.cmaps[self.parent.cmap],
                                    norm = self.norm(), origin = 'lower',
                                    aspect = 'auto',
                                    interpolation=self.GetPlotParam('interpolation'))

        self.cax.set_extent([self.xmin, self.xmax, self.ymin, self.ymax])

        self.cax.set_clim(self.clim)

        self.shock_line = self.axes.axvline(self.parent.shock_loc, linewidth = 1.5, linestyle = '--', color = self.parent.shock_color, path_effects=[PathEffects.Stroke(linewidth=2, foreground='k'),
                   PathEffects.Normal()])
        if not self.GetPlotParam('show_shock'):
            self.shock_line.set_visible(False)

        # a placeholder
        self.lineleft = self.axes.axvline(0, linewidth = 1.5, linestyle = '-', color = self.energy_color)
        self.lineright = self.axes.axvline(0, linewidth = 1.5, linestyle = '-', color = self.energy_color)

        if not self.GetPlotParam('show_int_region'):
            self.lineleft.set_visible(False)
            self.lineright.set_visible(False)


        self.axC = self.figure.add_subplot(self.gs[self.parent.cbar_extent[0]:self.parent.cbar_extent[1], self.parent.cbar_extent[2]:self.parent.cbar_extent[3]])
        # Technically I should use the colorbar class here,
        # but I found it annoying in some of it's limitations.
        if self.parent.HorizontalCbars:
            self.cbar = self.axC.imshow(self.gradient, aspect='auto',
                                    cmap=new_cmaps.cmaps[self.parent.cmap])
            # Make the colobar axis more like the real colorbar
            self.axC.tick_params(axis='x',
                                which = 'both', # bothe major and minor ticks
                                top = 'off', # turn off top ticks
                                labelsize=self.parent.num_font_size)

            self.axC.tick_params(axis='y',          # changes apply to the y-axis
                                which='both',      # both major and minor ticks are affected
                                left='off',      # ticks along the bottom edge are off
                                right='off',         # ticks along the top edge are off
                                labelleft='off')

        else:
            self.cbar = self.axC.imshow(np.transpose(self.gradient)[::-1], aspect='auto',
                                    cmap=new_cmaps.cmaps[self.parent.cmap])
            # Make the colobar axis more like the real colorbar
            self.axC.tick_params(axis='x',
                                which = 'both', # bothe major and minor ticks
                                top = 'off', # turn off top ticks
                                bottom = 'off',
                                labelbottom = 'off',
                                labelsize=self.parent.num_font_size)

            self.axC.tick_params(axis='y',          # changes apply to the y-axis
                                which='both',      # both major and minor ticks are affected
                                left='off',      # ticks along the bottom edge are off
                                right='on',         # ticks along the top edge are off
                                labelleft='off',
                                labelright='on',
                                labelsize=self.parent.num_font_size)


        if not self.GetPlotParam('show_cbar'):
            self.axC.set_visible(False)


        self.axes.set_axis_bgcolor('lightgrey')
        self.axes.tick_params(labelsize = self.parent.num_font_size, color=self.tick_color)

        self.axes.set_xlabel(self.x_label, labelpad = self.parent.xlabel_pad, color = 'black')
        self.axes.set_ylabel(self.y_label, labelpad = self.parent.ylabel_pad, color = 'black')

        self.refresh()

    def refresh(self):
        '''This is a function that will be called only if self.axes already
        holds a density type plot. We only update things that have shown. If
        hasn't changed, or isn't viewed, don't touch it. The difference between this and last
        time, is that we won't actually do any drawing in the plot. The plot
        will be redrawn after all subplots data is changed. '''


        # Main goal, only change what is showing..


        self.xmin = self.hist2d[2][0]
        self.xmax = self.hist2d[2][-1]
        self.ymin = self.hist2d[1][0]
        self.ymax = self.hist2d[1][-1]
        self.clim = list(self.hist2d[3])


        self.cax.set_data(self.hist2d[0])

        self.cax.set_extent([self.xmin,self.xmax, self.ymin, self.ymax])



        if self.GetPlotParam('set_v_min'):
            self.clim[0] =  10**self.GetPlotParam('v_min')
        if self.GetPlotParam('set_v_max'):
            self.clim[1] =  10**self.GetPlotParam('v_max')

        self.cax.set_clim(self.clim)

        if self.GetPlotParam('show_cbar'):
            self.CbarTickFormatter()
        if self.GetPlotParam('show_shock'):
            self.shock_line.set_xdata([self.parent.shock_loc,self.parent.shock_loc])

        if self.GetPlotParam('show_int_region'):
            if self.GetPlotParam('prtl_type') ==0 and self.parent.e_relative:
                self.left_loc = self.parent.shock_loc+self.parent.i_L.get()
                self.right_loc = self.parent.shock_loc+self.parent.i_R.get()

            elif self.GetPlotParam('prtl_type') == 0:
                self.left_loc = self.parent.i_L.get()
                self.right_loc = self.parent.i_R.get()

            elif self.GetPlotParam('prtl_type') == 1 and self.parent.e_relative:
                self.left_loc = self.parent.shock_loc+self.parent.e_L.get()
                self.right_loc = self.parent.shock_loc+self.parent.e_R.get()

            else:
                self.left_loc = self.parent.e_L.get()
                self.right_loc = self.parent.e_R.get()

            self.left_loc = max(self.left_loc, self.xmin+1)
            self.lineleft.set_xdata([self.left_loc,self.left_loc])

            self.right_loc = min(self.right_loc, self.xmax-1)
            self.lineright.set_xdata([self.right_loc,self.right_loc])

        self.UpdateLabelsandColors()
        self.axes.set_xlabel(self.x_label, labelpad = self.parent.xlabel_pad, color = 'black')
        self.axes.set_ylabel(self.y_label, labelpad = self.parent.ylabel_pad, color = 'black')

#        if self.GetPlotParam('set_p_min'):
#            self.ymin = self.GetPlotParam('p_min')
#        if self.GetPlotParam('set_p_max'):
#            self.ymax = self.GetPlotParam('p_max')
#        self.axes.set_ylim(self.ymin, self.ymax)

        if self.parent.xlim[0] and self.parent.LinkSpatial == 1:
            self.axes.set_xlim(self.parent.xlim[1],self.parent.xlim[2])
        else:
            self.axes.set_xlim(self.xmin,self.xmax)

    def CbarTickFormatter(self):
        ''' A helper function that sets the cbar ticks & labels. This used to be
        easier, but because I am no longer using the colorbar class i have to do
        stuff manually.'''
        clim = np.copy(self.cax.get_clim())
        print clim
        if self.GetPlotParam('show_cbar'):
            if self.GetPlotParam('cnorm_type') == "Log":
                if self.parent.HorizontalCbars:
                    self.cbar.set_extent([np.log10(clim[0]),np.log10(clim[1]),0,1])
                    self.axC.set_xlim(np.log10(clim[0]),np.log10(clim[1]))
                else:
                    self.cbar.set_extent([0,1,np.log10(clim[0]),np.log10(clim[1])])
                    self.axC.set_ylim(np.log10(clim[0]),np.log10(clim[1]))
                    self.axC.locator_params(axis='y',nbins=6)
            else:# self.GetPlotParam('cnorm_type') == "Linear":
                if self.parent.HorizontalCbars:
                    self.cbar.set_extent([clim[0], clim[1], 0, 1])
                    self.axC.set_xlim(clim[0], clim[1])
                else:
                    self.cbar.set_extent([0, 1, clim[0], clim[1]])
                    self.axC.set_ylim(clim[0], clim[1])
                    self.axC.locator_params(axis='y', nbins=6)

    def GetPlotParam(self, keyname):
        return self.FigWrap.GetPlotParam(keyname)

    def SetPlotParam(self, keyname, value,  update_plot = True):
        self.FigWrap.SetPlotParam(keyname, value,  update_plot = update_plot)

    def OpenSettings(self):
        if self.settings_window is None:
            self.settings_window = EnergySettings(self)
        else:
            self.settings_window.destroy()
            self.settings_window = EnergySettings(self)


class EnergySettings(Tk.Toplevel):
    def __init__(self, parent):
        self.parent = parent
        Tk.Toplevel.__init__(self)

        self.wm_title('Phase Plot (%d,%d) Settings' % self.parent.FigWrap.pos)
        self.parent = parent
        frm = ttk.Frame(self)
        frm.pack(fill=Tk.BOTH, expand=True)
        self.protocol('WM_DELETE_WINDOW', self.OnClosing)
        self.bind('<Return>', self.TxtEnter)

        # Create the OptionMenu to chooses the Chart Type:
        self.InterpolVar = Tk.StringVar(self)
        self.InterpolVar.set(self.parent.GetPlotParam('interpolation')) # default value
        self.InterpolVar.trace('w', self.InterpolChanged)

        ttk.Label(frm, text="Interpolation Method:").grid(row=0, column = 2)
        InterplChooser = apply(ttk.OptionMenu, (frm, self.InterpolVar, self.parent.GetPlotParam('interpolation')) + tuple(self.parent.InterpolationMethods))
        InterplChooser.grid(row =0, column = 3, sticky = Tk.W + Tk.E)

        # Create the OptionMenu to chooses the Chart Type:
        self.ctypevar = Tk.StringVar(self)
        self.ctypevar.set(self.parent.chartType) # default value
        self.ctypevar.trace('w', self.ctypeChanged)

        ttk.Label(frm, text="Choose Chart Type:").grid(row=0, column = 0)
        cmapChooser = apply(ttk.OptionMenu, (frm, self.ctypevar, self.parent.chartType) + tuple(self.parent.ChartTypes))
        cmapChooser.grid(row =0, column = 1, sticky = Tk.W + Tk.E)


        # the Radiobox Control to choose the particle
        self.prtlList = ['ion', 'electron']
        self.pvar = Tk.IntVar()
        self.pvar.set(self.parent.GetPlotParam('prtl_type'))

        ttk.Label(frm, text='Particle:').grid(row = 1, sticky = Tk.W)

        for i in range(len(self.prtlList)):
            ttk.Radiobutton(frm,
                text=self.prtlList[i],
                variable=self.pvar,
                command = self.RadioPrtl,
                value=i).grid(row = 2+i, sticky =Tk.W)

        # the Radiobox Control to choose the momentum dim
        self.dimList = ['x-px', 'x-py', 'x-pz']
        self.dimvar = Tk.IntVar()
        self.dimvar.set(self.parent.GetPlotParam('mom_dim'))

        ttk.Label(frm, text='Dimenison:').grid(row = 1, column = 1, sticky = Tk.W)

        for i in range(len(self.dimList)):
            ttk.Radiobutton(frm,
                text=self.dimList[i],
                variable=self.dimvar,
                command = self.RadioDim,
                value=i).grid(row = 2+i, column = 1, sticky = Tk.W)


        # Control whether or not Cbar is shown
        self.CbarVar = Tk.IntVar()
        self.CbarVar.set(self.parent.GetPlotParam('show_cbar'))
        cb = ttk.Checkbutton(frm, text = "Show Color bar",
                        variable = self.CbarVar,
                        command = self.CbarHandler)
        cb.grid(row = 6, sticky = Tk.W)

        # show shock
        self.ShockVar = Tk.IntVar()
        self.ShockVar.set(self.parent.GetPlotParam('show_shock'))
        cb = ttk.Checkbutton(frm, text = "Show Shock",
                        variable = self.ShockVar,
                        command = self.ShockVarHandler)
        cb.grid(row = 6, column = 1, sticky = Tk.W)


        # Control if the plot is weightedd
        self.WeightVar = Tk.IntVar()
        self.WeightVar.set(self.parent.GetPlotParam('weighted'))
        cb = ttk.Checkbutton(frm, text = "Weight by charge",
                        variable = self.WeightVar,
                        command = lambda:
                        self.parent.SetPlotParam('weighted', self.WeightVar.get()))
        cb.grid(row = 7, sticky = Tk.W)

        # Show energy integration region
        self.IntRegVar = Tk.IntVar()
        self.IntRegVar.set(self.parent.GetPlotParam('show_int_region'))
        cb = ttk.Checkbutton(frm, text = "Show Energy Region",
                        variable = self.IntRegVar,
                        command = self.ShowIntRegionHandler)
        cb.grid(row = 7, column = 1, sticky = Tk.W)

        # control mask
        self.MaskVar = Tk.IntVar()
        self.MaskVar.set(self.parent.GetPlotParam('masked'))
        cb = ttk.Checkbutton(frm, text = "Mask Zeros",
                        variable = self.MaskVar,
                        command = lambda:
                        self.parent.SetPlotParam('masked', self.MaskVar.get()))
        cb.grid(row = 8, sticky = Tk.W)


#        ttk.Label(frm, text = 'If the zero values are not masked they are set to z_min/2').grid(row =9, columnspan =2)
    # Define functions for the events
        # Now the field lim
        self.setVminVar = Tk.IntVar()
        self.setVminVar.set(self.parent.GetPlotParam('set_v_min'))
        self.setVminVar.trace('w', self.setVminChanged)

        self.setVmaxVar = Tk.IntVar()
        self.setVmaxVar.set(self.parent.GetPlotParam('set_v_max'))
        self.setVmaxVar.trace('w', self.setVmaxChanged)



        self.Vmin = Tk.StringVar()
        self.Vmin.set(str(self.parent.GetPlotParam('v_min')))

        self.Vmax = Tk.StringVar()
        self.Vmax.set(str(self.parent.GetPlotParam('v_max')))


        cb = ttk.Checkbutton(frm, text ='Set log(f) min',
                        variable = self.setVminVar)
        cb.grid(row = 3, column = 2, sticky = Tk.W)
        self.VminEnter = ttk.Entry(frm, textvariable=self.Vmin, width=7)
        self.VminEnter.grid(row = 3, column = 3)

        cb = ttk.Checkbutton(frm, text ='Set log(f) max',
                        variable = self.setVmaxVar)
        cb.grid(row = 4, column = 2, sticky = Tk.W)

        self.VmaxEnter = ttk.Entry(frm, textvariable=self.Vmax, width=7)
        self.VmaxEnter.grid(row = 4, column = 3)

        # Now the y lim
        self.setPminVar = Tk.IntVar()
        self.setPminVar.set(self.parent.GetPlotParam('set_p_min'))
        self.setPminVar.trace('w', self.setPminChanged)

        self.setPmaxVar = Tk.IntVar()
        self.setPmaxVar.set(self.parent.GetPlotParam('set_p_max'))
        self.setPmaxVar.trace('w', self.setPmaxChanged)



        self.Pmin = Tk.StringVar()
        self.Pmin.set(str(self.parent.GetPlotParam('p_min')))

        self.Pmax = Tk.StringVar()
        self.Pmax.set(str(self.parent.GetPlotParam('p_max')))


        cb = ttk.Checkbutton(frm, text ='Set y_axis min',
                        variable = self.setPminVar)
        cb.grid(row = 5, column = 2, sticky = Tk.W)
        self.PminEnter = ttk.Entry(frm, textvariable=self.Pmin, width=7)
        self.PminEnter.grid(row = 5, column = 3)

        cb = ttk.Checkbutton(frm, text ='Set y_axis max',
                        variable = self.setPmaxVar)
        cb.grid(row = 6, column = 2, sticky = Tk.W)

        self.PmaxEnter = ttk.Entry(frm, textvariable=self.Pmax, width=7)
        self.PmaxEnter.grid(row = 6, column = 3)

        # Now the E lim
        self.setEminVar = Tk.IntVar()
        self.setEminVar.set(self.parent.GetPlotParam('set_E_min'))
        self.setEminVar.trace('w', self.setEminChanged)

        self.setEmaxVar = Tk.IntVar()
        self.setEmaxVar.set(self.parent.GetPlotParam('set_E_max'))
        self.setEmaxVar.trace('w', self.setEmaxChanged)


        self.Emin = Tk.StringVar()
        self.Emin.set(str(self.parent.GetPlotParam('E_min')))

        self.Emax = Tk.StringVar()
        self.Emax.set(str(self.parent.GetPlotParam('E_max')))


        cb = ttk.Checkbutton(frm, text ='Set E_min (m_e c^2)',
                        variable = self.setEminVar)
        cb.grid(row = 7, column = 2, sticky = Tk.W)
        self.EminEnter = ttk.Entry(frm, textvariable=self.Emin, width=7)
        self.EminEnter.grid(row = 7, column = 3)

        cb = ttk.Checkbutton(frm, text ='Set E_max (m_e c^2)',
                        variable = self.setEmaxVar)
        cb.grid(row = 8, column = 2, sticky = Tk.W)

        self.EmaxEnter = ttk.Entry(frm, textvariable=self.Emax, width=7)
        self.EmaxEnter.grid(row = 8, column = 3)


    def ShockVarHandler(self, *args):
        if self.parent.GetPlotParam('show_shock')== self.ShockVar.get():
            pass
        else:
            self.parent.shock_line.set_visible(self.ShockVar.get())
            self.parent.SetPlotParam('show_shock', self.ShockVar.get())

    def ShowIntRegionHandler(self, *args):
        if self.parent.GetPlotParam('show_int_region')== self.IntRegVar.get():
            pass
        else:
            self.parent.lineleft.set_visible(self.IntRegVar.get())
            self.parent.lineright.set_visible(self.IntRegVar.get())
            self.parent.SetPlotParam('show_int_region', self.IntRegVar.get())

    def CbarHandler(self, *args):
        if self.parent.GetPlotParam('show_cbar')== self.CbarVar.get():
            pass
        else:
            self.parent.axC.set_visible(self.CbarVar.get())
            self.parent.SetPlotParam('show_cbar', self.CbarVar.get(), update_plot =self.parent.GetPlotParam('twoD'))


    def ctypeChanged(self, *args):
        if self.ctypevar.get() == self.parent.chartType:
            pass
        else:
            self.parent.ChangePlotType(self.ctypevar.get())
            self.destroy()

    def InterpolChanged(self, *args):
        if self.InterpolVar.get() == self.parent.GetPlotParam('interpolation'):
            pass
        else:
            self.parent.cax.set_interpolation(self.InterpolVar.get())
            self.parent.SetPlotParam('interpolation', self.InterpolVar.get())

    def RadioPrtl(self):
        if self.pvar.get() == self.parent.GetPlotParam('prtl_type'):
            pass
        else:

            self.parent.SetPlotParam('prtl_type', self.pvar.get(), update_plot =  False)
            self.parent.UpdateLabelsandColors()
            self.parent.axes.set_ylabel(self.parent.y_label, labelpad = self.parent.parent.ylabel_pad, color = 'black')
            self.parent.lineleft.set_color(self.parent.energy_color)
            self.parent.lineright.set_color(self.parent.energy_color)
            self.parent.SetPlotParam('prtl_type', self.pvar.get())

    def RadioDim(self):
        if self.dimvar.get() == self.parent.GetPlotParam('mom_dim'):
            pass
        else:
            self.parent.SetPlotParam('mom_dim', self.dimvar.get(), update_plot = False)
            self.parent.UpdateLabelsandColors()
            self.parent.axes.set_ylabel(self.parent.y_label, labelpad = self.parent.parent.ylabel_pad, color = 'black')
            self.parent.SetPlotParam('mom_dim', self.dimvar.get())



    def setVminChanged(self, *args):
        if self.setVminVar.get() == self.parent.GetPlotParam('set_v_min'):
            pass
        else:
            self.parent.SetPlotParam('set_v_min', self.setVminVar.get())

    def setVmaxChanged(self, *args):
        if self.setVmaxVar.get() == self.parent.GetPlotParam('set_v_max'):
            pass
        else:
            self.parent.SetPlotParam('set_v_max', self.setVmaxVar.get())

    def setPminChanged(self, *args):
        if self.setPminVar.get() == self.parent.GetPlotParam('set_p_min'):
            pass
        else:
            self.parent.SetPlotParam('set_p_min', self.setPminVar.get())

    def setPmaxChanged(self, *args):
        if self.setPmaxVar.get() == self.parent.GetPlotParam('set_p_max'):
            pass
        else:
            self.parent.SetPlotParam('set_p_max', self.setPmaxVar.get())

    def setEminChanged(self, *args):
        if self.setEminVar.get() == self.parent.GetPlotParam('set_E_min'):
            pass
        else:
            self.parent.SetPlotParam('set_E_min', self.setEminVar.get())

    def setEmaxChanged(self, *args):
        if self.setEmaxVar.get() == self.parent.GetPlotParam('set_E_max'):
            pass
        else:
            self.parent.SetPlotParam('set_E_max', self.setEmaxVar.get())


    def TxtEnter(self, e):
        self.FieldsCallback()

    def FieldsCallback(self):
        tkvarLimList = [self.Vmin, self.Vmax, self.Pmin, self.Pmax, self.Emin, self.Emax]
        plot_param_List = ['v_min', 'v_max', 'p_min', 'p_max', 'E_min', 'E_max']
        tkvarSetList = [self.setVminVar, self.setVmaxVar, self.setPminVar, self.setPmaxVar, self.setEminVar, self.setEmaxVar]
        to_reload = False
        for j in range(len(tkvarLimList)):
            try:
            #make sure the user types in a float
                if np.abs(float(tkvarLimList[j].get()) - self.parent.GetPlotParam(plot_param_List[j])) > 1E-4:
                    self.parent.SetPlotParam(plot_param_List[j], float(tkvarLimList[j].get()), update_plot = False)
                    to_reload += True*tkvarSetList[j].get()

            except ValueError:
                #if they type in random stuff, just set it ot the param value
                tkvarLimList[j].set(str(self.parent.GetPlotParam(plot_param_List[j])))
        if to_reload:
            self.parent.SetPlotParam('v_min', self.parent.GetPlotParam('v_min'))

    def OnClosing(self):
        self.parent.settings_window = None
        self.destroy()