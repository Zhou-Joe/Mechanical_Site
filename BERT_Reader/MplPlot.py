from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from sci_calculation import *
import numpy as np
from constants import get_time_interval

class GBPlot(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=18, height=12, dpi=100, data=None):
        self.fig = Figure(figsize=(width, height), dpi=dpi, layout='constrained')
        #self.fig.set_tight_layout(True)
        self.gs=self.fig.add_gridspec(2,2,left=0.1, wspace=0.1, width_ratios=[0.5,0.5])
        super(GBPlot, self).__init__(self.fig)
        self.lineay = []
        self.lineaz = []
        self.lineacomb = []
        self.initplotxyz()
        self.annots=[]
        self.annot_mode = 'Single'


    def initplotxyz(self):
        try:
            for ax in self.get_all_axe_list():
                ax.remove()
            for line in self.get_all_line_list():
                line.remove()


        except:
            pass
        self.lineay = []
        self.lineaz = []
        self.lineacomb = []
        ax1 = self.fig.add_subplot(self.gs[0,0])
        ax2 = self.fig.add_subplot(self.gs[0,1])
        ax3 = self.fig.add_subplot(self.gs[1,:])

        self.axe_ay=ax1
        self.axe_az=ax2
        self.axe_comb=ax3
        self.axe_ay.plot([0.01,0.2,1,4],[5,2,2,2],'r',linewidth=3,label='Allowable ay')
        self.axe_ay.plot([0.01, 0.2, 1, 4], [-5, -2, -2, -2], 'r', linewidth=3)
        self.axe_az.plot([0,1,2,3,4],[6,6,4,4,4],'r',linewidth=3,label='Allowable az')
        self.axe_az.plot([0,0.5,2,3,4],[-2,-1.5,-1.5,-1.5,-1.5],'r',linewidth=3)
        self.axe_comb.plot([-1.8,-1.62,-0.54,0,1.8,5.4,6],[0,0.6,1.8,2,1.8,0.6,0],'yellow',linewidth=3,label='dt=0.05s')
        self.axe_comb.plot([-1.8, -1.62, -0.54, 0, 1.8, 5.4, 6], [0, -0.6, -1.8, -2, -1.8, -0.6, 0], 'yellow', linewidth=3,
                           )
        self.axe_comb.plot([-1.9,-1.71,-0.57,0,1.8,5.4,6],[0,0.741,2.22,2.47,2.22,0.741,0],'orange',linewidth=3,label='dt=0.1s')
        self.axe_comb.plot([-1.9, -1.71, -0.57, 0, 1.8, 5.4, 6], [0, -0.741, -2.22, -2.47, -2.22, -0.741, 0], 'orange',
                           linewidth=3)
        self.axe_comb.plot([-1.95,-1.755,-0.585,0,1.8,5.4,6],[0,0.9,2.7,3,2.7,0.9,0],'r',linewidth=3,label='dt=0.2s')
        self.axe_comb.plot([-1.95, -1.755, -0.585, 0, 1.8, 5.4, 6], [0, -0.9, -2.7, -3, -2.7, -0.9, 0], 'r', linewidth=3,
                           )

        self.axe_ay.set_xlim(0,4)
        self.axe_ay.set_xlabel('dt (s)')
        self.axe_ay.set_ylim(-5,5)
        self.axe_ay.set_xlabel('|ay|')
        self.axe_az.set_xlim(0,4)
        self.axe_az.set_xlabel('dt (s)')
        self.axe_az.set_ylim(-2,6)
        self.axe_az.set_ylabel('az')
        self.axe_comb.set_xlim(-2,6)
        self.axe_comb.set_ylim(-3.2,3.2)
        self.axe_comb.set_xlabel('az')
        self.axe_comb.set_ylabel('ay')




        for ax in self.get_all_axe_list():
            ax.legend()
        self.fig.canvas.draw_idle()
    def removelines(self):

        try:
            self.lineay.pop().remove()
            self.lineay.pop().remove()
            self.lineaz.pop().remove()
            self.lineaz.pop().remove()
            self.lineacomb.pop().remove()

        except Exception as e:
            #print (self.lineay)
            pass
    def addplotxyz(self, data):
        try:
            for annot in self.annots:
                annot.remove()
        except:
            pass


        self.removelines()
        
        # Extended x_axis_gb with 2x denser sampling for accurate curve
        # Range: 0.02s to 14s, with denser points throughout
        fs = 500  # Default sampling frequency
        x_axis_gb = [
            # 0.02 to 0.1: 0.0025s increments (32 points)
            0.02, 0.0225, 0.025, 0.0275, 0.03, 0.0325, 0.035, 0.0375,
            0.04, 0.0425, 0.045, 0.0475, 0.05, 0.0525, 0.055, 0.0575,
            0.06, 0.0625, 0.065, 0.0675, 0.07, 0.0725, 0.075, 0.0775,
            0.08, 0.0825, 0.085, 0.0875, 0.09, 0.0925, 0.095, 0.0975,
            # 0.1 to 0.2: 0.005s increments (20 points)
            0.1, 0.105, 0.11, 0.115, 0.12, 0.125, 0.13, 0.135, 0.14, 0.145,
            0.15, 0.155, 0.16, 0.165, 0.17, 0.175, 0.18, 0.185, 0.19, 0.195,
            # 0.2 to 0.5: 0.01s increments (30 points)
            0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28, 0.29,
            0.3, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37, 0.38, 0.39,
            0.4, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48, 0.49,
            # 0.5 to 1: 0.025s increments (20 points)
            0.5, 0.525, 0.55, 0.575, 0.6, 0.625, 0.65, 0.675, 0.7, 0.725,
            0.75, 0.775, 0.8, 0.825, 0.85, 0.875, 0.9, 0.925, 0.95, 0.975,
            # 1 to 2: 0.05s increments (20 points)
            1, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.45,
            1.5, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85, 1.9, 1.95,
            # 2 to 5: 0.1s increments (30 points)
            2, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9,
            3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9,
            4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9,
            # 5 to 14: 0.25s increments (36 points)
            5, 5.25, 5.5, 5.75, 6, 6.25, 6.5, 6.75, 7, 7.25,
            7.5, 7.75, 8, 8.25, 8.5, 8.75, 9, 9.25, 9.5, 9.75,
            10, 10.25, 10.5, 10.75, 11, 11.25, 11.5, 11.75, 12, 12.25,
            12.5, 12.75, 13, 13.25, 13.5, 13.75, 14
        ]
        
        # Calculate window sizes in samples
        window_sizes = [int(t * fs) for t in x_axis_gb]
        
        # Get instantaneous values
        d0py = max(0, np.max(data.iloc[:, 2]))
        d0ny = min(0, np.min(data.iloc[:, 2]))
        d0pz = max(1, np.max(data.iloc[:, 3]))
        d0nz = min(1, np.min(data.iloc[:, 3]))
        
        # Calculate sustained acceleration for all window sizes
        results_p = []
        results_n = []
        
        for dt in window_sizes:
            dp, dn = ProcessGB(data, dt)
            results_p.append(dp)
            results_n.append(dn)
        
        # Extract y and z values for plotting
        p1 = [d0py] + [r[0] for r in results_p]  # ay(+)
        p2 = [d0ny] + [r[0] for r in results_n]  # ay(-)
        p3 = [d0pz] + [r[1] for r in results_p]  # az(+)
        p4 = [d0nz] + [r[1] for r in results_n]  # az(-)
        
        # Add instantaneous time (0) to x_axis
        x_axis_gb_plot = [0.002] + x_axis_gb  # 0.002s represents instantaneous
        
        z_array = data.iloc[:, 3].values
        y_array = data.iloc[:, 2].values
        
        self.lineay.append(self.axe_ay.plot(x_axis_gb_plot, p1, '-', color='b', label='Measured ay(+)')[0])
        self.lineay.append(self.axe_ay.plot(x_axis_gb_plot, p2, '-', color='k', label='Measured ay( - )')[0])
        self.lineaz.append(self.axe_az.plot(x_axis_gb_plot, p3, '-', color='b', label='Measured az(+)')[0])
        self.lineaz.append(self.axe_az.plot(x_axis_gb_plot, p4, '-', color='k', label='Measured az( - )')[0])
        self.lineacomb.append(self.axe_comb.plot(z_array, y_array, '.-', color='c', label='Measured Data')[0])
        
        try:
            for ax in self.get_all_axe_list():
                ax.legend()
        except:
            pass


        self.fig.canvas.draw_idle()
        self.fig.canvas.mpl_connect("button_press_event", self.onclick)
    def setlinewidth(self, linewidth=0.6):
        for line in self.get_all_line_list():
            line.set_linewidth(linewidth)
    def get_all_axe_list(self):
        axes_list=[self.axe_ay, self.axe_az, self.axe_comb]
        return axes_list
    def get_all_line_list(self):
        line_list = []
        for axs in [self.lineay, self.lineaz, self.lineacomb]:
            for ax in axs:
                line_list.append(ax)

        #print('line_list_num = ' + str(len(line_list)))
        return line_list
    def update_annot(self, ax, line, ind):
        try:

            x, y = line.get_data()
            annot = ax.annotate("", xy=(x[ind["ind"][0]], y[ind["ind"][0]]), xytext=(10+x[ind["ind"][0]], 10+y[ind["ind"][0]]), textcoords="offset points",
                                    bbox=dict(boxstyle="round", fc="b", alpha=0.1),
                                    arrowprops=dict(arrowstyle="->"))

            if ax == self.axe_comb:
                # Use dynamic time interval calculation (default to 0.002s for compatibility)
                time_interval = get_time_interval(500)  # Default 500 Hz for GB plot
                text = "t = {}\naz = {}\nay = {}".format(round(ind["ind"][0]*time_interval,3), x[ind["ind"][0]],y[ind["ind"][0]])
            else:
                text = "t = {}\namp = {}".format(x[ind["ind"][0]], y[ind["ind"][0]])
            annot.set_text(text)
            annot.set_visible(True)
            annot.set_fontsize(8)
            self.annots.append(annot)
        except Exception as e:
            print(e)

    def onclick(self, event):
        if self.annot_mode == "Single":
            try:
                for annot in self.annots:
                    annot.set_visible(False)
                self.annots=[]
            except:
                pass
        if event.inaxes in self.get_all_axe_list():
            for line in self.get_all_line_list():
                try:
                    cont, ind = line.contains(event)
                    if cont:
                        self.update_annot(event.inaxes, line, ind)
                        self.fig.canvas.draw_idle()
                        break

                except Exception as e:
                    pass

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=18, height=12, dpi=100):

        self.fig = Figure(figsize=(width, height), dpi=dpi, layout='constrained')
        #self.fig.set_tight_layout(True)
        super(MplCanvas, self).__init__(self.fig)
        # self.initplotxyz()

        self.linex = []
        self.liney = []
        self.linez = []
        self.annots=[]
        self.annot_mode = 'Single'
        self.initplotxyz()

    def initplotxyz(self, list_data=None):
        try:
            for ax in self.get_all_axe_list():
                ax.remove()
            for line in self.get_all_line_list():
                line.remove()
        except:
            pass

        self.linex = []
        self.liney = []
        self.linez = []
        self.axes_x = self.fig.add_subplot(311)
        self.axes_y = self.fig.add_subplot(312, sharex= self.axes_x)
        self.axes_z = self.fig.add_subplot(313, sharex = self.axes_x)

        i=0
        ylabels=['Fore/Aft', 'Lateral', 'Vertical']
        for ax in self.get_all_axe_list():
            ax.set_xlabel('time (s)')
            ax.set_ylabel(ylabels[i])
            i+=1

        self.fig.canvas.draw_idle()

    def removelines(self, plot_order):
        plot_order=plot_order
        try:
            self.linex.pop(plot_order).remove()
            self.liney.pop(plot_order).remove()
            self.linez.pop(plot_order).remove()
            self.axes_x.pop(plot_order).remove()
            self.axes_y.pop(plot_order).remove()
            self.axes_z.pop(plot_order).remove()
            self.fig.canvas.draw_idle()
            #print('line {}'.format(len(self.get_all_line_list())))
        except Exception as e:
            pass

    def addplotxyz(self, list_data, plot_order, color='b'):
        try:
            for annot in self.annots:
                annot.remove()
        except:
            pass



        line1, = self.axes_x.plot(list_data.iloc[:, 0], list_data.iloc[:, 1], color=color)
        self.linex.append(line1)

        line2, = self.axes_y.plot(list_data.iloc[:, 0], list_data.iloc[:, 2], color=color)
        self.liney.append(line2)

        line3, = self.axes_z.plot(list_data.iloc[:, 0], list_data.iloc[:, 3], color=color)
        self.linez.append(line3)
        self.setlinewidth()

        self.fig.canvas.mpl_connect("button_press_event", self.onclick)



    def addplotxyz_fitmax(self, list_data, plot_order, offset, color='b'):
        try:
            for annot in self.annots:
                annot.remove()
        except:
            pass


        # Use dynamic time interval calculation (default to 0.002s for compatibility)
        time_interval = get_time_interval(500)  # Default 500 Hz for trend plot
        t=(list_data.iloc[:, 0].values - offset*time_interval).round(decimals=4)

        line1, = self.axes_x.plot(t, list_data.iloc[:, 1], color=color)
        self.linex.append(line1)

        line2, = self.axes_y.plot(t, list_data.iloc[:, 2], color=color)
        self.liney.append(line2)

        line3, = self.axes_z.plot(t, list_data.iloc[:, 3], color=color)
        self.linez.append(line3)
        self.setlinewidth()

        self.fig.canvas.mpl_connect("button_press_event", self.onclick)




    def setlinewidth(self, linewidth=0.6):
        for line in self.get_all_line_list():
            line.set_linewidth(linewidth)

    def get_all_axe_list(self):
        return [self.axes_x, self.axes_y, self.axes_z]

    def get_all_line_list(self):
        line_list = []
        for axs in [self.linex, self.liney, self.linez]:
            for ax in axs:
                line_list.append(ax)
        return line_list



    def update_annot(self, ax, line, ind):
        x, y = line.get_data()
        annot = ax.annotate("", xy=(x[ind["ind"][0]], y[ind["ind"][0]]), xytext=(10, 10), textcoords="offset points",
                                bbox=dict(boxstyle="round", fc="b", alpha=0.1),
                                arrowprops=dict(arrowstyle="->"))

        text = "t = {}\namp = {}".format(x[ind["ind"][0]], y[ind["ind"][0]])
        annot.set_text(text)
        annot.set_fontsize(8)
        annot.set_visible(True)
        self.annots.append(annot)

    def onclick(self, event):
        if self.annot_mode == "Single":
            try:
                for annot in self.annots:
                    annot.set_visible(False)
                self.annots=[]
            except:
                pass
        if event.inaxes in self.get_all_axe_list():
            for line in self.get_all_line_list():
                try:
                    cont, ind = line.contains(event)
                    if cont:
                        self.update_annot(event.inaxes, line, ind)
                        self.fig.canvas.draw_idle()
                        break
                except Exception as e:
                    pass

class XYReversalPlot(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=18, height=12, dpi=100, data=None):
        self.fig = Figure(figsize=(width, height), dpi=dpi, layout='constrained')
        super(XYReversalPlot, self).__init__(self.fig)
        
        self.linex = []
        self.liney = []
        self.reversal_markers = []
        self.annots = []
        self.annot_mode = 'Single'
        self.reversal_info_text = None
        self.initplotxyz()
    
    def initplotxyz(self):
        try:
            for ax in self.get_all_axe_list():
                ax.remove()
            for line in self.get_all_line_list():
                line.remove()
        except:
            pass
        
        self.linex = []
        self.liney = []
        self.reversal_markers = []
        self.reversal_info_text = None
        
        self.gs = self.fig.add_gridspec(3, 1, height_ratios=[2, 2, 1], hspace=0.3)
        self.axe_x = self.fig.add_subplot(self.gs[0, 0])
        self.axe_y = self.fig.add_subplot(self.gs[1, 0], sharex=self.axe_x)
        self.info_ax = self.fig.add_subplot(self.gs[2, 0])
        self.info_ax.axis('off')
        
        self.axe_x.set_ylabel('X Acceleration (g)')
        self.axe_x.set_title('X/Y Acceleration Reversal Analysis')
        self.axe_x.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
        self.axe_x.legend(loc='upper right')
        
        self.axe_y.set_xlabel('Time (s)')
        self.axe_y.set_ylabel('Y Acceleration (g)')
        self.axe_y.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
        self.axe_y.legend(loc='upper right')
        
        self.fig.canvas.draw_idle()
    
    def get_all_axe_list(self):
        return [self.axe_x, self.axe_y, self.info_ax]
    
    def get_all_line_list(self):
        line_list = []
        for axs in [self.linex, self.liney, self.reversal_markers]:
            for line in axs:
                line_list.append(line)
        return line_list
    
    def plot_xy_data(self, time_data, x_data, y_data, reversals):
        try:
            for annot in self.annots:
                annot.remove()
        except:
            pass
        
        self.removelines()
        
        line_x, = self.axe_x.plot(time_data, x_data, 'b-', linewidth=1, label='X Acceleration')
        line_y, = self.axe_y.plot(time_data, y_data, 'g-', linewidth=1, label='Y Acceleration')
        self.linex.append(line_x)
        self.liney.append(line_y)
        
        colors = ['red', 'orange', 'purple', 'cyan', 'magenta', 'brown']
        
        x_reversals = reversals.get('x_reversals', [])
        y_reversals = reversals.get('y_reversals', [])
        
        for i, reversal in enumerate(x_reversals):
            color = colors[i % len(colors)]
            window_start = reversal['window_start']
            window_end = reversal['window_end']
            self.axe_x.axvspan(window_start, window_end, alpha=0.2, color=color)
            
            min_time = reversal['min_time']
            max_time = reversal['max_time']
            min_val = reversal['min_value']
            max_val = reversal['max_value']
            
            marker_min, = self.axe_x.plot(min_time, min_val, 'v', color=color, markersize=10, label=f'X neg peak' if i==0 else "")
            marker_max, = self.axe_x.plot(max_time, max_val, '^', color=color, markersize=10, label=f'X pos peak' if i==0 else "")
            self.reversal_markers.append(marker_min)
            self.reversal_markers.append(marker_max)
        
        for i, reversal in enumerate(y_reversals):
            color = colors[i % len(colors)]
            window_start = reversal['window_start']
            window_end = reversal['window_end']
            self.axe_y.axvspan(window_start, window_end, alpha=0.2, color=color)
            
            min_time = reversal['min_time']
            max_time = reversal['max_time']
            min_val = reversal['min_value']
            max_val = reversal['max_value']
            
            marker_min, = self.axe_y.plot(min_time, min_val, 'v', color=color, markersize=10, label=f'Y neg peak' if i==0 else "")
            marker_max, = self.axe_y.plot(max_time, max_val, '^', color=color, markersize=10, label=f'Y pos peak' if i==0 else "")
            self.reversal_markers.append(marker_min)
            self.reversal_markers.append(marker_max)
        
        info_text = "Acceleration Reversals Detected:\n"
        
        if len(x_reversals) > 0:
            info_text += "X-axis (Fore/Aft):\n"
            for i, reversal in enumerate(x_reversals):
                if reversal['min_value'] < 0:
                    info_text += f"  - Negative peak: {reversal['min_value']:.3f}g at {reversal['min_time']:.3f}s "
                    info_text += f"(window: {reversal['window_start']:.3f}s - {reversal['window_end']:.3f}s)\n"
                if reversal['max_value'] > 0:
                    info_text += f"  + Positive peak: {reversal['max_value']:.3f}g at {reversal['max_time']:.3f}s "
                    info_text += f"(window: {reversal['window_start']:.3f}s - {reversal['window_end']:.3f}s)\n"
        else:
            info_text += "X-axis: No reversals detected.\n"
        
        if len(y_reversals) > 0:
            info_text += "Y-axis (Lateral):\n"
            for i, reversal in enumerate(y_reversals):
                if reversal['min_value'] < 0:
                    info_text += f"  - Negative peak: {reversal['min_value']:.3f}g at {reversal['min_time']:.3f}s "
                    info_text += f"(window: {reversal['window_start']:.3f}s - {reversal['window_end']:.3f}s)\n"
                if reversal['max_value'] > 0:
                    info_text += f"  + Positive peak: {reversal['max_value']:.3f}g at {reversal['max_time']:.3f}s "
                    info_text += f"(window: {reversal['window_start']:.3f}s - {reversal['window_end']:.3f}s)\n"
        else:
            info_text += "Y-axis: No reversals detected.\n"
        
        self.reversal_info_text = self.info_ax.text(0.01, 0.5, info_text, transform=self.info_ax.transAxes,
                                                     fontsize=9, verticalalignment='center',
                                                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        self.fig.canvas.draw_idle()
        self.fig.canvas.mpl_connect("button_press_event", self.onclick)
    
    def removelines(self):
        try:
            for line in self.linex:
                line.remove()
            for line in self.liney:
                line.remove()
            for marker in self.reversal_markers:
                marker.remove()
            if self.reversal_info_text is not None:
                self.reversal_info_text.remove()
                self.reversal_info_text = None
            self.linex = []
            self.liney = []
            self.reversal_markers = []
        except:
            pass
    
    def update_annot(self, ax, line, ind):
        try:
            x, y = line.get_data()
            annot = ax.annotate("", xy=(x[ind["ind"][0]], y[ind["ind"][0]]), 
                              xytext=(10+x[ind["ind"][0]], 10+y[ind["ind"][0]]), 
                              textcoords="offset points",
                              bbox=dict(boxstyle="round", fc="b", alpha=0.1),
                              arrowprops=dict(arrowstyle="->"))
            
            if ax == self.axe_x:
                text = "t = {:.3f}s\nax = {:.4f}".format(x[ind["ind"][0]], y[ind["ind"][0]])
            elif ax == self.axe_y:
                text = "t = {:.3f}s\nay = {:.4f}".format(x[ind["ind"][0]], y[ind["ind"][0]])
            else:
                text = "t = {:.3f}\namp = {:.4f}".format(x[ind["ind"][0]], y[ind["ind"][0]])
            
            annot.set_text(text)
            annot.set_visible(True)
            annot.set_fontsize(8)
            self.annots.append(annot)
        except Exception as e:
            print(e)
    
    def onclick(self, event):
        if self.annot_mode == "Single":
            try:
                for annot in self.annots:
                    annot.set_visible(False)
                self.annots = []
            except:
                pass
        
        if event.inaxes in self.get_all_axe_list():
            for line in self.get_all_line_list():
                try:
                    cont, ind = line.contains(event)
                    if cont:
                        self.update_annot(event.inaxes, line, ind)
                        self.fig.canvas.draw_idle()
                        break
                except Exception as e:
                    pass


class AccZonePlot(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=18, height=14, dpi=100, data=None):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(AccZonePlot, self).__init__(self.fig)

        self.initplotxyz()
        self.annots=[]
        self.annot_mode = 'Single'


    def initplotxyz(self):
        self.removelines()
        
        # Create grid spec with 2 rows: plot (height=5) and info text (height=1)
        self.gs = self.fig.add_gridspec(2, 1, height_ratios=[5, 1], hspace=0.3)
        self.axe = self.fig.add_subplot(self.gs[0, 0])
        
        # Create a separate axes for the zone info text (below the plot)
        self.zone_info_ax = self.fig.add_subplot(self.gs[1, 0])
        self.zone_info_ax.axis('off')  # Hide axes

        # Set extended range - can be adjusted for larger data spans
        x_min, x_max = -6, 6
        y_min, y_max = -4, 4

        # Line equation: from (-0.7, 0.2) to (0, 0) and from (0, 0) to (0.7, -0.2)
        # Both have the same slope: m = -0.2/0.7 = -2/7
        # Equation: y = (-2/7) * x, or x = -3.5 * y
        def line_x_at_y(y):
            return -3.5 * y  # x coordinate on the sloping line at given y

        # Fill Zone 5 as base (everything below y = -0.2 is Zone 5)
        self.axe.fill([x_min, x_max, x_max, x_min], [y_min, y_min, -0.2, -0.2],
                     color='red', alpha=0.7, label='Zone 5')

        # Zone 5 in -0.2 < y <= 0 region (left of sloping line, x < 0.7)
        # This is the area left of the line x = -3.5y, from y=-0.2 to y=0
        # For y in [-0.2, 0], the line x = -3.5y goes from x=0.7 (at y=-0.2) to x=0 (at y=0)
        # Left of line means x < -3.5y
        # Polygon: (x_min, -0.2) -> (x_min, 0) -> (0, 0) -> along line to (0.7, -0.2) -> back to (x_min, -0.2)
        # Create line points from (0, 0) to (0.7, -0.2) - but don't include (0,0) as it's already added
        x_line_pts = np.linspace(0, 0.7, 20)  # from (0, 0) to (0.7, -0.2)
        y_line_pts = -x_line_pts / 3.5
        # Exclude the first point (0, 0) since we already add it explicitly
        x_zone5_poly = np.concatenate([[x_min, x_min, 0], x_line_pts[1:], [x_min]])
        y_zone5_poly = np.concatenate([[-0.2, 0, 0], y_line_pts[1:], [-0.2]])
        self.axe.fill(x_zone5_poly, y_zone5_poly, color='red', alpha=0.7)

        # Zone 5 in -0.2 < y <= 0 region (right of line1 AND x < 0.2)
        # This is the small triangular region between the sloping line and x=0.2, but only where x > -3.5y
        # The line x = -3.5y intersects x=0.2 at y = -0.2/3.5 ≈ -0.057
        # So this region exists for y in [-0.057, 0] where 0 < x < 0.2 and x > -3.5y
        # Polygon: (0, 0) -> (0.2, 0) -> (0.2, -0.057) -> along line back to (0, 0)
        y_intersect2 = -0.2 / 3.5  # where -3.5y = 0.2, so y = -0.2/3.5 ≈ -0.057
        x_line_mid = np.linspace(0.2, 0, 10)  # from (0.2, -0.057) to (0, 0)
        y_line_mid = -x_line_mid / 3.5
        x_zone5b_poly = np.concatenate([[0, 0.2, 0.2], x_line_mid[1:]])  # exclude first to avoid dup
        y_zone5b_poly = np.concatenate([[0, 0, y_intersect2], y_line_mid[1:]])
        self.axe.fill(x_zone5b_poly, y_zone5b_poly, color='red', alpha=0.7)

        # Zone 4 in -0.2 < y <= 0 region (right of sloping line AND x >= 0.2, OR x >= 0.7)
        # This is the area to the right of the sloping line, excluding the small Zone 5 triangle
        # Polygon: from (0.7, -0.2) to (x_max, -0.2) to (x_max, 0) to (0.2, 0) to (0.2, -0.057) along line
        x_line_pts2 = np.linspace(0.2, 0.7, 15)  # from (0.2, -0.057) to (0.7, -0.2)
        y_line_pts2 = -x_line_pts2 / 3.5
        x_zone4_poly = np.concatenate([[0.7, x_max, x_max, 0.2], x_line_pts2])
        y_zone4_poly = np.concatenate([[-0.2, -0.2, 0, 0], y_line_pts2])
        self.axe.fill(x_zone4_poly, y_zone4_poly, color='lightpink', alpha=0.7)

        # Zone 4 in 0 < y <= 0.2 region (left of sloping line, x < -0.2)
        # Polygon: (x_min, 0), (x_min, 0.2), (-0.2, 0.2), (-0.2, 0) - but bounded by sloping line
        # At y=0.2, line x = -3.5*0.2 = -0.7
        # So left of line means x < -0.7 at y=0.2
        # Zone 4 is x < -0.2 and left of sloping line
        # Actually: left of line AND x < -0.2 -> Zone 4
        # Vertices: (x_min, 0), (x_min, 0.2), (-0.2, 0.2), (-0.2, 0) intersects with left of line
        # At y=0, line is at x=0. At y=0.2, line is at x=-0.7
        # Zone 4 polygon: (x_min, 0), (x_min, 0.2), (-0.2, 0.2), (-0.2, 0) - but cut by line
        # Line goes from (0,0) to (-0.7, 0.2)
        # So Zone 4 is: (x_min, 0), (x_min, 0.2), (-0.2, 0.2), (-0.2, 0) - but we need to follow line
        # Actually the line cuts through: from (x_min, 0) along x-axis to where? No, simpler:
        # Zone 4: x < -0.2 AND left of line. Left of line at y in [0, 0.2] means x < -3.5y
        # At y=0.2, -3.5*0.2 = -0.7, which is < -0.2, so condition is x < -0.2 (since -0.7 < -0.2)
        # Wait, that's wrong. Let me reconsider.
        # At y=0.1, line is at x=-0.35. Left of line means x < -0.35.
        # But we also need x < -0.2 for Zone 4. So x < -0.35 (stricter condition)
        # At y=0.2, line is at x=-0.7. Left means x < -0.7.
        # So Zone 4 in 0<y<=0.2 is: x < max(-0.2, -3.5y) = x < -3.5y (since -3.5y <= -0.7 < -0.2 for y>=0.2)
        # Actually for y in [0, 0.2], -3.5y ranges from 0 to -0.7.
        # So left of line means x < -3.5y, which for small y means x < something close to 0.
        # But we also need x < -0.2. So the effective boundary is x < min(-0.2, -3.5y).
        # For y < 0.057, -3.5y > -0.2, so min is -0.2.
        # For y > 0.057, -3.5y < -0.2, so min is -3.5y.
        # This is getting complicated. Let me use polygon approach.

        # For 0 < y <= 0.2 region:
        # Line from (-0.7, 0.2) to (0, 0): x = -3.5y
        # At y=0.2, line is at x=-0.7. At y=0, line is at x=0.
        # For y in (0, 0.2], -3.5y ranges from -0.7 to 0.
        # y_intersect is where -3.5y = -0.2, i.e., y = 0.2/3.5 ≈ 0.057
        y_intersect = 0.2 / 3.5

        # Zone 4 in 0 < y <= 0.2: left of line AND x < -0.2
        # This is the region where x < min(-0.2, -3.5y)
        # For y < y_intersect: -3.5y > -0.2, so boundary is x < -0.2
        # For y > y_intersect: -3.5y < -0.2, so boundary is x < -3.5y (follows the line)
        # Polygon: (x_min, 0) -> (x_min, 0.2) -> (-0.7, 0.2) [line at y=0.2] -> along line to (-0.2, y_intersect) -> (-0.2, 0)
        x_line_left = np.linspace(-0.7, -0.2, 10)  # from (-0.7, 0.2) to (-0.2, y_intersect)
        y_line_left = -x_line_left / 3.5
        x_zone4_poly = np.concatenate([[x_min, x_min, -0.7], x_line_left, [-0.2]])
        y_zone4_poly = np.concatenate([[0, 0.2, 0.2], y_line_left, [0]])
        self.axe.fill(x_zone4_poly, y_zone4_poly, color='lightpink', alpha=0.7)

        # Zone 5 in 0 < y <= 0.2: left of line AND -0.2 <= x <= 0
        # This is the small triangular region between x=-0.2 and the line
        # Only exists for y < y_intersect where -3.5y > -0.2
        # Vertices: (-0.2, 0), (0, 0), and along line back to (-0.2, y_intersect)
        x_line_mid = np.linspace(0, -0.2, 10)  # from (0,0) to (-0.2, y_intersect)
        y_line_mid = -x_line_mid / 3.5
        x_zone5_poly = np.concatenate([[-0.2, 0], x_line_mid])
        y_zone5_poly = np.concatenate([[0, 0], y_line_mid])
        self.axe.fill(x_zone5_poly, y_zone5_poly, color='red', alpha=0.7)

        # Zone 3 in 0 < y <= 0.2: right of line (x > -3.5y)
        # This is everything to the right of the sloping line
        # Vertices: along line from (0,0) to (-0.7, 0.2), then to (x_min? no, x_max), wait...
        # Actually: from line at (-0.7, 0.2) to (x_max, 0.2) to (x_max, 0) to (0, 0) back along line
        x_line_right = np.linspace(-0.7, 0, 20)  # from (-0.7, 0.2) to (0, 0)
        y_line_right = -x_line_right / 3.5
        x_zone3_poly = np.concatenate([x_line_right, [x_max, x_max]])
        y_zone3_poly = np.concatenate([y_line_right, [0, 0.2]])
        self.axe.fill(x_zone3_poly, y_zone3_poly, color='orange', alpha=0.7)

        # Zone 4: x < -1.2, 0.2 < y <= 0.7
        self.axe.fill([x_min, -1.2, -1.2, x_min], [0.2, 0.2, 0.7, 0.7],
                     color='lightpink', alpha=0.7)

        # Zone 3: -1.2 <= x < -0.7, 0.2 < y <= 0.7
        self.axe.fill([-1.2, -0.7, -0.7, -1.2], [0.2, 0.2, 0.7, 0.7],
                     color='orange', alpha=0.7)

        # Zone 2: -0.7 <= x < 0.2, 0.2 < y <= 0.7
        self.axe.fill([-0.7, 0.2, 0.2, -0.7], [0.2, 0.2, 0.7, 0.7],
                     color='yellow', alpha=0.7)

        # Zone 1: x >= 0.2, 0.2 < y <= 0.7
        self.axe.fill([0.2, x_max, x_max, 0.2], [0.2, 0.2, 0.7, 0.7],
                     color='greenyellow', alpha=0.7)

        # Zone 4: x < -1.2, y > 0.7
        self.axe.fill([x_min, -1.2, -1.2, x_min], [0.7, 0.7, y_max, y_max],
                     color='lightpink', alpha=0.7, label='Zone 4')

        # Zone 3: -1.2 <= x < -0.7, y > 0.7
        self.axe.fill([-1.2, -0.7, -0.7, -1.2], [0.7, 0.7, y_max, y_max],
                     color='orange', alpha=0.7, label='Zone 3')

        # Zone 2: -0.7 <= x < -0.2, y > 0.7
        self.axe.fill([-0.7, -0.2, -0.2, -0.7], [0.7, 0.7, y_max, y_max],
                     color='yellow', alpha=0.7, label='Zone 2')

        # Zone 1: x >= -0.2, y > 0.7
        self.axe.fill([-0.2, x_max, x_max, -0.2], [0.7, 0.7, y_max, y_max],
                     color='greenyellow', alpha=0.7, label='Zone 1')

        # Draw sloping lines for zone boundaries
        # Line from (-0.7, 0.2) to (0, 0)
        x_line1 = np.array([-0.7, 0])
        y_line1 = np.array([0.2, 0])
        self.axe.plot(x_line1, y_line1, 'k-', linewidth=2)

        # Line from (0, 0) to (0.7, -0.2)
        x_line2 = np.array([0, 0.7])
        y_line2 = np.array([0, -0.2])
        self.axe.plot(x_line2, y_line2, 'k-', linewidth=2)

        # Extend sloping lines to full range (dashed)
        # Line 1 extended: y = (-2/7)x, so at y=y_max, x = -3.5*y_max
        x_line1_extend = np.array([line_x_at_y(y_max), -0.7])
        y_line1_extend = np.array([y_max, 0.2])
        self.axe.plot(x_line1_extend, y_line1_extend, 'k--', linewidth=1, alpha=0.5)

        # Line 2 extended: at y=y_min, x = -3.5*y_min
        x_line2_extend = np.array([0.7, line_x_at_y(y_min)])
        y_line2_extend = np.array([-0.2, y_min])
        self.axe.plot(x_line2_extend, y_line2_extend, 'k--', linewidth=1, alpha=0.5)

        # Draw vertical boundary lines
        self.axe.axvline(x=-1.2, color='k', linestyle='-', linewidth=1, alpha=0.5)
        self.axe.axvline(x=-0.7, color='k', linestyle='-', linewidth=1, alpha=0.5)
        self.axe.axvline(x=-0.2, color='k', linestyle='-', linewidth=1, alpha=0.5)
        self.axe.axvline(x=0.2, color='k', linestyle='-', linewidth=1, alpha=0.5)
        self.axe.axvline(x=0.7, color='k', linestyle='-', linewidth=1, alpha=0.5)

        # Draw horizontal boundary lines
        self.axe.axhline(y=0.7, color='k', linestyle='-', linewidth=1, alpha=0.5)
        self.axe.axhline(y=0.2, color='k', linestyle='-', linewidth=1, alpha=0.5)
        self.axe.axhline(y=0, color='k', linestyle='-', linewidth=1, alpha=0.5)
        self.axe.axhline(y=-0.2, color='k', linestyle='-', linewidth=1, alpha=0.5)

        self.axe.set_xlim(x_min, x_max)
        self.axe.set_ylim(y_min, y_max)
        self.axe.set_xlabel('Front <=> Back (X-acceleration)')
        self.axe.set_ylabel('Up <=> Down (Z-acceleration)')
        self.axe.set_title('Acceleration Zones')
        self.axe.set_aspect('equal', adjustable='box')

        # Add zone labels at representative positions
        self.axe.text(3, 3, 'Zone 1', fontsize=12, ha='center', fontweight='bold')
        self.axe.text(-0.45, 3, 'Zone 2', fontsize=12, ha='center', fontweight='bold')
        self.axe.text(-0.95, 3, 'Zone 3', fontsize=12, ha='center', fontweight='bold')
        self.axe.text(-3.5, 3, 'Zone 4', fontsize=12, ha='center', fontweight='bold')
        self.axe.text(0, -2, 'Zone 5', fontsize=12, ha='center', fontweight='bold')

        self.fig.canvas.draw_idle()

    def removelines(self):
        try:
            self.line.remove()
        except:
            pass


    def addplotxyz(self, data):
        self.removelines()
        try:
            for annot in self.annots:
                annot.remove()
        except Exception as e:
            pass

        self.line, = self.axe.plot(data.iloc[:, 1], data.iloc[:, 3], '.-', color='blue')
        
        # Store time interval for annotation use
        time_data = data.iloc[:, 0].values
        if len(time_data) >= 2:
            self.time_interval = time_data[1] - time_data[0]
        else:
            self.time_interval = get_time_interval(500)
        
        # Analyze zones and display results
        self.analyze_and_display_zones(data)
        
        self.fig.canvas.draw_idle()

    def analyze_and_display_zones(self, data):
        """
        Analyze which zone the data falls into and display results below the plot.
        
        Logic:
        1. Create a list of zones for each point
        2. Calculate consecutive points at same zone
        3. Check if duration >= 0.2s (based on sampling frequency)
        4. Zone 5 is most severe, Zone 1 is least
        5. If most severe zone meets duration criteria, that's the judgment
        6. Display zone information below the plot
        """
        # Extract x (front-back) and z (up-down) acceleration data
        x_data = data.iloc[:, 1].values
        z_data = data.iloc[:, 3].values
        time_data = data.iloc[:, 0].values
        
        # Calculate actual time interval from data (handle 200Hz, 500Hz, etc.)
        if len(time_data) >= 2:
            time_interval = time_data[1] - time_data[0]
        else:
            time_interval = get_time_interval(500)  # fallback to default
        
        # Minimum duration threshold (0.2 seconds)
        min_duration = 0.2
        min_points = int(min_duration / time_interval)
        
        # Step 1: Create list of zones for each point
        zone_list = []
        for x, z in zip(x_data, z_data):
            zone = self.get_zone_info(x, z)
            zone_list.append(zone)
        
        # Step 2 & 3: Find consecutive points in same zone with duration >= 0.2s
        zone_durations = {}  # zone -> list of (start_time, end_time, duration)
        
        i = 0
        n = len(zone_list)
        while i < n:
            current_zone = zone_list[i]
            start_idx = i
            
            # Count consecutive points in same zone
            while i < n and zone_list[i] == current_zone:
                i += 1
            end_idx = i
            
            # Calculate duration
            num_points = end_idx - start_idx
            if num_points >= min_points:
                start_time = time_data[start_idx]
                end_time = time_data[end_idx - 1]
                duration = end_time - start_time
                
                if current_zone not in zone_durations:
                    zone_durations[current_zone] = []
                zone_durations[current_zone].append((start_time, end_time, duration))
        
        # Step 4 & 5: Determine most severe zone that meets criteria
        # Zone severity: Zone 5 > Zone 4 > Zone 3 > Zone 2 > Zone 1
        zone_severity = {"Zone 5": 5, "Zone 4": 4, "Zone 3": 3, "Zone 2": 2, "Zone 1": 1}
        
        # Find zones that meet duration criteria, sorted by severity
        qualifying_zones = []
        for zone, durations in zone_durations.items():
            if zone in zone_severity:
                qualifying_zones.append((zone_severity[zone], zone, durations))
        
        # Sort by severity (descending)
        qualifying_zones.sort(key=lambda x: x[0], reverse=True)
        
        # Step 6: Display information below the plot
        self.display_zone_info(qualifying_zones, zone_durations)
    
    def display_zone_info(self, qualifying_zones, zone_durations):
        """Display zone analysis results in a separate row below the plot"""
        # Clear previous text from the zone info axes
        self.zone_info_ax.clear()
        self.zone_info_ax.axis('off')
        
        if not qualifying_zones:
            # No zone meets the duration criteria
            info_text = "No zone meets the 0.2s duration threshold."
        else:
            # Get the most severe zone (the classified zone)
            most_severe = qualifying_zones[0]
            zone_name = most_severe[1]
            durations = most_severe[2]
            
            # Build info text - only show the classified zone and its durations
            info_lines = [f"Classified Zone: {zone_name}"]
            
            # List all time periods for this zone
            for start_time, end_time, duration in durations:
                info_lines.append(f"  {start_time:.3f}s to {end_time:.3f}s (duration: {duration:.3f}s)")
            
            info_text = "\n".join(info_lines)
        
        # Add text to the separate zone info axes (below the plot)
        self.zone_info_ax.text(
            0.5, 0.5, info_text,
            ha='center', va='center',
            fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
            transform=self.zone_info_ax.transAxes
        )

    def get_zone_info(self, x, y):
        """Determine which zone point (x, y) falls into based on correct criteria"""
        # y-axis: up-down (z-acceleration data)
        # x-axis: front-back (x-acceleration data)

        # Line 1: from (-0.7, 0.2) to (0, 0)
        # Slope = (0 - 0.2) / (0 - (-0.7)) = -0.2 / 0.7 = -2/7
        # Equation: y - 0 = (-2/7)(x - 0) => y = (-2/7)x
        # Or: y = -0.2857... * x

        # Line 2: from (0, 0) to (0.7, -0.2)
        # Slope = (-0.2 - 0) / (0.7 - 0) = -0.2 / 0.7 = -2/7
        # Equation: y = (-2/7)x
        # Same slope, both lines have equation y = (-2/7)x

        def is_left_of_line1(x, y):
            """Check if point is to the left of line from (-0.7, 0.2) to (0, 0)"""
            # Line equation: y = (-2/7)(x - 0) = -2x/7
            # For a point to be LEFT of this line (when looking from (-0.7, 0.2) to (0,0)):
            # At a given y, the x on the line is x = -7y/2
            # Left means x < -7y/2
            line_x_at_y = -3.5 * y  # x = -7y/2 = -3.5y
            return x < line_x_at_y

        def is_left_of_line2(x, y):
            """Check if point is to the left of line from (0, 0) to (0.7, -0.2)"""
            # Same line equation: y = (-2/7)x
            # Left means x < -7y/2
            line_x_at_y = -3.5 * y
            return x < line_x_at_y

        def is_right_of_line1(x, y):
            """Check if point is to the right of line from (-0.7, 0.2) to (0, 0)"""
            line_x_at_y = -3.5 * y
            return x > line_x_at_y

        if y > 0.7:
            if x < -1.2:
                return "Zone 4"
            elif x < -0.7:
                return "Zone 3"
            elif x < -0.2:
                return "Zone 2"
            else:
                return "Zone 1"

        elif y > 0.2:
            if x < -1.2:
                return "Zone 4"
            elif x < -0.7:
                return "Zone 3"
            elif x < 0.2:
                return "Zone 2"
            else:
                return "Zone 1"

        elif y > 0:
            # Complicated region with sloping line
            # Line from (-0.7, 0.2) to (0, 0)
            if is_left_of_line1(x, y) and x < -0.2:
                return "Zone 4"
            elif is_left_of_line1(x, y) and -0.2 <= x <= 0:
                return "Zone 5"
            else:
                return "Zone 3"

        elif y > -0.2:
            # Complicated region with sloping line
            # Line from (0, 0) to (0.7, -0.2)
            # Note: line1 and line2 are the same line y = (-2/7)x
            # For this region (y < 0), left of line means x < -3.5y (positive x region)
            if is_left_of_line2(x, y) and x < 0.7:
                return "Zone 5"
            elif is_right_of_line1(x, y) and x < 0.2:
                # Right of line AND x < 0.2 -> Zone 5
                return "Zone 5"
            else:
                return "Zone 4"

        else:  # y <= -0.2
            return "Zone 5"

    def update_annot(self, ax, ind):
        x, y = self.line.get_data()
        x_val = x[ind["ind"][0]]
        y_val = y[ind["ind"][0]]
        
        # Get zone information
        zone = self.get_zone_info(x_val, y_val)
        
        annot = ax.annotate("", xy=(x_val, y_val), xytext=(10+x_val, 10+y_val), textcoords="offset points",
                                bbox=dict(boxstyle="round", fc="b", alpha=0.1),
                                arrowprops=dict(arrowstyle="->"))

        # Use stored time interval (calculated from actual data sampling frequency)
        time_interval = getattr(self, 'time_interval', get_time_interval(500))
        text = "t = {}s\nx = {}\nz = {}\n{}".format(round(ind["ind"][0]*time_interval,3), x_val, y_val, zone)
        annot.set_text(text)
        annot.set_fontsize(8)
        annot.set_visible(True)
        self.annots.append(annot)

    def onclick(self, event):
        if self.annot_mode == "Single":
            try:
                for annot in self.annots:
                    annot.set_visible(False)
                self.annots=[]
            except:
                pass
        if event.inaxes == self.axe:
            try:
                cont, ind = self.line.contains(event)
                if cont:
                    self.update_annot(event.inaxes, ind)
                    self.fig.canvas.draw_idle()

            except Exception as e:
                pass



class ASTMPlot(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=18, height=12, dpi=100, data=None):
        self.fig = Figure(figsize=(width, height), dpi=dpi, layout='constrained')
        #self.fig.set_tight_layout(True)

        super(ASTMPlot, self).__init__(self.fig)
        self.lineax = []
        self.lineay = []
        self.lineaz = []
        self.lineeggxy=[]
        self.lineeggxz=[]
        self.lineeggyz=[]
        self.annot_mode = 'Single'
        self.initplotxyz()
        self.annots=[]


    def initplotxyz(self):
        try:
            for ax in self.get_all_axe_list():
                ax.remove()
            for line in self.get_all_line_list():
                line.remove()
        except:
            pass
        self.lineax = []
        self.lineay = []
        self.lineaz = []
        self.lineeggxy=[]
        self.lineeggxz=[]
        self.lineeggyz=[]
        self.axe_ax = self.fig.add_subplot(231)
        self.axe_ay = self.fig.add_subplot(232)
        self.axe_az = self.fig.add_subplot(233)
        self.axe_eggxy = self.fig.add_subplot(234)
        self.axe_eggxz = self.fig.add_subplot(235)
        self.axe_eggyz = self.fig.add_subplot(236)

        self.axe_eggxy.set_xlabel('Front <=> Back')
        self.axe_eggxy.set_ylabel('Left <=> Right')
        self.axe_eggxz.set_xlabel('Front <=> Back')
        self.axe_eggxz.set_ylabel('Up <=> Down')
        self.axe_eggyz.set_xlabel('Left <=> Right')
        self.axe_eggyz.set_ylabel('Up <=> Down')
        self.axe_ax.set_xlabel('dt (s)')
        self.axe_ax.set_ylabel('ax')
        self.axe_ay.set_xlabel('dt (s)')
        self.axe_ay.set_ylabel('ay')
        self.axe_az.set_xlabel('dt (s)')
        self.axe_az.set_ylabel('az')

        self.axe_ax.set_xlim(0, 14)
        self.axe_ay.set_xlim(0, 14)
        self.axe_ay.set_ylim(0, 3.2)
        self.axe_az.set_xlim(0, 14)
        self.axe_eggxy.set_xlim(-2.1, 6.1)
        self.axe_eggxy.set_ylim(-3.2, 3.2)
        self.axe_eggxz.set_xlim(-2.1, 6.1)
        self.axe_eggxz.set_ylim(-2.2, 6.2)
        self.axe_eggyz.set_xlim(-3.1, 3.1)
        self.axe_eggyz.set_ylim(-2.2, 6.2)

        #for ax in self.get_all_axe_list():
            #ax.legend()

        self.fig.canvas.draw_idle()

    def removelines(self):

        try:
            self.lineax.pop().remove()
            self.lineax.pop().remove()
            self.lineay.pop().remove()
            self.lineay.pop().remove()
            self.lineaz.pop().remove()
            self.lineaz.pop().remove()
            self.lineeggxy.pop().remove()
            self.lineeggxz.pop().remove()
            self.lineeggyz.pop().remove()

        except Exception as e:
            pass

    def addplotxyz(self, data, restraint, cond, input_height):
        try:
            for annot in self.annots:
                annot.remove()
        except:
            pass

        self.removelines()
        
        # Extended x_axis with 2x denser sampling for accurate curve
        # Range: 0.02s to 14s, with denser points throughout
        fs = 500  # Default sampling frequency
        x_axis = [
            # 0.02 to 0.1: 0.0025s increments (32 points)
            0.02, 0.0225, 0.025, 0.0275, 0.03, 0.0325, 0.035, 0.0375,
            0.04, 0.0425, 0.045, 0.0475, 0.05, 0.0525, 0.055, 0.0575,
            0.06, 0.0625, 0.065, 0.0675, 0.07, 0.0725, 0.075, 0.0775,
            0.08, 0.0825, 0.085, 0.0875, 0.09, 0.0925, 0.095, 0.0975,
            # 0.1 to 0.2: 0.005s increments (20 points)
            0.1, 0.105, 0.11, 0.115, 0.12, 0.125, 0.13, 0.135, 0.14, 0.145,
            0.15, 0.155, 0.16, 0.165, 0.17, 0.175, 0.18, 0.185, 0.19, 0.195,
            # 0.2 to 0.5: 0.01s increments (30 points)
            0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28, 0.29,
            0.3, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37, 0.38, 0.39,
            0.4, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48, 0.49,
            # 0.5 to 1: 0.025s increments (20 points)
            0.5, 0.525, 0.55, 0.575, 0.6, 0.625, 0.65, 0.675, 0.7, 0.725,
            0.75, 0.775, 0.8, 0.825, 0.85, 0.875, 0.9, 0.925, 0.95, 0.975,
            # 1 to 2: 0.05s increments (20 points)
            1, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.45,
            1.5, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85, 1.9, 1.95,
            # 2 to 5: 0.1s increments (30 points)
            2, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9,
            3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9,
            4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9,
            # 5 to 14: 0.25s increments (36 points)
            5, 5.25, 5.5, 5.75, 6, 6.25, 6.5, 6.75, 7, 7.25,
            7.5, 7.75, 8, 8.25, 8.5, 8.75, 9, 9.25, 9.5, 9.75,
            10, 10.25, 10.5, 10.75, 11, 11.25, 11.5, 11.75, 12, 12.25,
            12.5, 12.75, 13, 13.25, 13.5, 13.75, 14
        ]
        
        # Calculate window sizes in samples
        window_sizes = [int(t * fs) for t in x_axis]
        
        # Calculate sustained acceleration for all window sizes
        results_p = []
        results_n = []
        
        for dt in window_sizes:
            dp, dn = ProcessASTM(data, dt)
            results_p.append(dp)
            results_n.append(dn)
        
        # Extract x, y, z values for plotting
        ax_p = [r[0] for r in results_p]
        ax_n = [r[0] for r in results_n]
        ay_p = [r[1] for r in results_p]
        ay_n = [r[1] for r in results_n]
        az_p = [r[2] for r in results_p]
        az_n = [r[2] for r in results_n]
        
        # Plot sustained acceleration curves
        self.lineax.append(self.axe_ax.plot(x_axis, ax_p, 'b-', label='Measured ax (+)')[0])
        self.lineax.append(self.axe_ax.plot(x_axis, ax_n, 'g-', label='Measured ax (-)')[0])
        self.lineay.append(self.axe_ay.plot(x_axis, ay_p, 'b-', label='Measured ay (Right)')[0])
        self.lineay.append(self.axe_ay.plot(x_axis, [-v for v in ay_n], 'g-', label='Measured ay (Left)')[0])
        self.lineaz.append(self.axe_az.plot(x_axis, az_p, 'b-', label='Measured az (Down)')[0])
        self.lineaz.append(self.axe_az.plot(x_axis, az_n, 'g-', label='Measured az ( Up )')[0])

        self.lineeggxy.append(self.axe_eggxy.plot(data.iloc[:, 1], data.iloc[:, 2], 'c.-', label='Measured')[0])
        self.lineeggxz.append(self.axe_eggxz.plot(data.iloc[:, 1], data.iloc[:, 3], 'c.-', label='Measured')[0])
        self.lineeggyz.append(self.axe_eggyz.plot(data.iloc[:, 2], data.iloc[:, 3], 'c.-', label='Measured')[0])

        try:
            for ax in self.get_all_axe_list():
                ax.legend()
        except:
            pass



        try:
            self.addDisneyStd(restype=restraint, cond=cond, height=input_height)
        except Exception as e:
            pass

        self.fig.canvas.draw_idle()
        self.fig.canvas.mpl_connect("button_press_event", self.onclick)

    def setlinewidth(self, linewidth = 0.6):
        for line in self.get_all_line_list():
            line.set_linewidth(linewidth)

    def get_all_axe_list(self):
        axes_list=[self.axe_ax, self.axe_ay, self.axe_az, self.axe_eggxy,self.axe_eggxz, self.axe_eggyz]
        return axes_list

    def get_all_line_list(self):
        line_list = []
        for axs in [self.lineax,self.lineay, self.lineaz, self.lineeggxy, self.lineeggxz, self.lineeggyz]:
            for ax in axs:
                line_list.append(ax)

        #print('line_list_num = ' + str(len(line_list)))
        return line_list


    def update_annot(self, ax, line, ind):
        x, y = line.get_data()
        annot = ax.annotate("", xy=(x[ind["ind"][0]], y[ind["ind"][0]]), xytext=(10+x[ind["ind"][0]], 10+y[ind["ind"][0]]), textcoords="offset points",
                                bbox=dict(boxstyle="round", fc="b", alpha=0.1),
                                arrowprops=dict(arrowstyle="->"))

        # Use dynamic time interval calculation (default to 0.002s for compatibility)
        time_interval = get_time_interval(500)  # Default 500 Hz for ASTM plot
        if ax == self.axe_eggxy:
            text = "t = {}\nx = {}\ny = {}".format(round(ind["ind"][0] * time_interval, 3), x[ind["ind"][0]], y[ind["ind"][0]])
        elif ax == self.axe_eggxz:
            text = "t = {}\nx = {}\nz = {}".format(round(ind["ind"][0] * time_interval, 3), x[ind["ind"][0]], y[ind["ind"][0]])
        elif ax == self.axe_eggyz:
            text = "t = {}\ny = {}\nz = {}".format(round(ind["ind"][0] * time_interval, 3), x[ind["ind"][0]], y[ind["ind"][0]])
        else:
            text = "t = {}\namp = {}".format(x[ind["ind"][0]], y[ind["ind"][0]])
        annot.set_text(text)
        annot.set_fontsize(8)
        annot.set_visible(True)
        self.annots.append(annot)

    def onclick(self, event):
        if self.annot_mode == "Single":
            try:
                for annot in self.annots:
                    annot.set_visible(False)
                self.annots=[]
            except:
                pass
        if event.inaxes in self.get_all_axe_list():
            for line in self.get_all_line_list():
                try:
                    cont, ind = line.contains(event)
                    if cont:
                        self.update_annot(event.inaxes, line, ind)
                        self.fig.canvas.draw_idle()
                        break

                except Exception as e:
                    pass

    def addDisneyStd(self,cond,restype, height):
        try:
            for lines in [self.lined1, self.lined2, self.lined3, self.lined4, self.lined5, self.lined6]:
                for line in lines:
                    line.remove()
        except:
            pass

        if cond == 'E-Stop':
            cond = 1.25
        elif cond == "Normal":
            cond = 1
        else:
            cond = 1.25


        self.lined1=[]
        self.lined2=[]
        self.lined3=[]
        self.lined4=[]
        self.lined5=[]
        self.lined6=[]
        frontASTM = [-2, -2, -1.5, -1.5]
        backASTM = [6, 6, 6, 4, 4, 3, 3, 2.5, 2.5]
        lrASTM = [3, 3, 3, 2, 2]
        upASTM = [-2, -2, -1.5, -1.5, -1.2, -1.2]
        downASTM = [6, 6, 6, 4, 4, 3, 3, 2, 2]
        ht = float(height)
        coefX, coefZ= cond * coef(ht, 'x'), cond * coef(ht, 'z')

        x3, y3 = eggXY(2 * coef(ht, 'x'), 6 * coef(ht, 'x'), 3 * coef(ht, 'x'))
        x4, y4 = eggXZ(2 * coef(ht, 'z'), 6 * coef(ht, 'z'), 2 * coef(ht, 'z'), 6 * coef(ht, 'z'))
        x5, y5 = eggYZ(3 * coef(ht, 'z'), 2 * coef(ht, 'z'), 6 * coef(ht, 'z'))
        self.lined1.append(self.axe_ax.plot([0.2, 0.5, 14], [-2,-1.5, -1.5], 'r', linewidth=3, label='Allowable ax')[0])
        self.lined1.append(self.axe_ax.plot(np.array([0.2, 1, 2, 4, 5, 11.8, 12, 14]), np.array([6, 6, 4, 4, 3, 3, 2.5, 2.5]) * coef(ht, 'x'), 'r', linewidth=3)[0])
        self.lined2.append(self.axe_ay.plot(np.array([0.2, 1, 2, 14]), np.array([3, 3, 2, 2])* coef(ht, 'x'), 'r', linewidth=3, label='Allowable ay')[0])
        self.lined3.append(self.axe_az.plot(np.array([0.2, 0.5, 4, 7, 14]), np.array([-2, -1.5, -1.5, -1.2, -1.2])* coef(ht, 'x'), 'r', linewidth=3, label='Allowable az')[0])
        self.lined3.append(self.axe_az.plot(np.array([0.2, 1, 2, 4, 5, 11.8, 12, 14]), np.array([6, 6, 4, 4, 3, 3, 2, 2]) * coef(ht, 'x'), 'r', linewidth=3)[0])
        self.lined4.append( self.axe_eggxy.plot(x3, y3, 'r--', label='ASTM (0.2s)')[0])
        self.lined4.append(self.axe_eggxy.plot([-2, 6], [0, 0], [0, 0], [3, -3], color='k', linewidth=3)[0])
        self.lined5.append(self.axe_eggxz.plot(x4, y4, 'r--', label='ASTM (0.2s)')[0])
        self.lined5.append(self.axe_eggxz.plot([-2, 6], [0, 0], [0, 0], [6, -2], color='k', linewidth=3)[0])
        self.lined6.append(self.axe_eggyz.plot(x5, y5, 'r--', label='ASTM (0.2s)')[0])
        self.lined6.append(self.axe_eggyz.plot([-3, 3], [0, 0], [0, 0], [-2, 6], color='k', linewidth=3)[0])

        try:
            for ax in self.get_all_axe_list():
                ax.legend()

        except:
            pass

        if restype == 'Upper Body':

            xa, ya = eggXY(2 * cond * coef(ht, 'x'), 3.6 * cond * coef(ht, 'x'), 3 * cond * coef(ht, 'x'))
            xaa, yaa = eggXY(1.6 * cond * coef(ht, 'x'), 3.6 * cond * coef(ht, 'x'),
                             2.4 * cond * coef(ht, 'x'))
            xb, yb = eggXZ(2 * cond * coef(ht, 'z'), 3.6 * cond * coef(ht, 'z'), 2 * cond * coef(ht, 'z'),
                           5 * cond * coef(ht, 'z'))
            xbb, ybb = eggXZ(1.6 * cond * coef(ht, 'z'), 3.6 * cond * coef(ht, 'z'),
                             1.4 * cond * coef(ht, 'z'), 4.8 * cond * coef(ht, 'z'))
            xc, yc = eggYZ(3 * cond * coef(ht, 'z'), 2 * cond * coef(ht, 'z'), 5 * cond * coef(ht, 'z'))
            xcc, ycc = eggYZ(2.4 * cond * coef(ht, 'z'), 1.4 * cond * coef(ht, 'z'),
                             4.8 * cond * coef(ht, 'z'))
            a31 = np.maximum(frontASTM, np.array([-2, -1.6, -1.2, -1.2]) * coefX)
            a32 = np.minimum(backASTM, np.array([3.6, 3.6, 3.6, 2.5, 2.5, 2, 2, 2, 2]) * coefX)
            a33 = np.minimum(lrASTM, np.array([3, 2.4, 2.4, 1.6, 1.6]) * coefX)
            a34 = np.maximum(upASTM, np.array([-2, -1.4, -1, -1, -0.7, -0.7]) * coefZ)
            a35 = np.minimum(downASTM, np.array([5, 4.8, 4.8, 3.4, 3.4, 2.6, 2.6, 1.8, 1.8]) * coefZ)
            
            self.lined4.append(self.axe_eggxy.plot(xa, ya, 'k', label='Upper Body (0s)')[0])
            self.lined4.append(self.axe_eggxy.plot(xaa, yaa, 'k--', label='Upper Body (0.2s)')[0])
            self.lined5.append(self.axe_eggxz.plot(xb, yb, 'k', label='Upper Body (0s)')[0])
            self.lined5.append(self.axe_eggxz.plot(xbb, ybb, 'k--', label='Upper Body (0.2s)')[0])
            self.lined6.append(self.axe_eggyz.plot(xc, yc, 'k', label='Upper Body (0s)')[0])
            self.lined6.append(self.axe_eggyz.plot(xcc, ycc, 'k--', label='Upper Body (0.2s)')[0])

        elif restype == 'Group Lower Body':

            xa, ya = eggXY(1.7 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'), 2.4 * cond * coef(ht, 'x'))
            xaa, yaa = eggXY(1.4 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'),
                             2.1 * cond * coef(ht, 'x'))
            xb, yb = eggXZ(1.7 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'), 2 * cond * coef(ht, 'z'),
                           3.5 * cond * coef(ht, 'z'))
            xbb, ybb = eggXZ(1.4 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'), 1 * cond * coef(ht, 'z'),
                             3 * cond * coef(ht, 'z'))
            xc, yc = eggYZ(2.4 * cond * coef(ht, 'z'), 2 * cond * coef(ht, 'z'), 3.5 * cond * coef(ht, 'z'))
            xcc, ycc = eggYZ(2.1 * cond * coef(ht, 'z'), 1 * cond * coef(ht, 'z'), 3 * cond * coef(ht, 'z'))
            a31 = np.maximum(frontASTM, np.array([-2, -1.6, -1.2, -1.2]) * coefX)
            a32 = np.minimum(backASTM, np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2, 2, 2, 2]) * coefX)
            a33 = np.minimum(lrASTM, np.array([2.4, 2.1, 2.1, 1.4, 1.4]) * coefX)
            a34 = np.maximum(upASTM, np.array([-1, 0, 0.2, 0.2, 0.2, 0.2]) * coefZ)
            a35 = np.minimum(downASTM, np.array([4.5, 4, 4, 3.1, 3.1, 2.4, 2.4, 1.7, 1.7]) * coefZ)

            self.lined4.append(self.axe_eggxy.plot(xa, ya, 'k', label='Group Lower Body (0s)')[0])
            self.lined4.append(self.axe_eggxy.plot(xaa, yaa, 'k--', label='Group Lower Body (0.2s)')[0])
            self.lined5.append(self.axe_eggxz.plot(xb, 1 + yb, 'k', label='Group Lower Body (0s)')[0])
            self.lined5.append(self.axe_eggxz.plot(xbb, 1 + ybb, 'k--', label='Group Lower Body (0.2s)')[0])
            self.lined6.append(self.axe_eggyz.plot(xc, 1 + yc, 'k', label='Group Lower Body (0s)')[0])
            self.lined6.append(self.axe_eggyz.plot(xcc, 1 + ycc, 'k--', label='Group Lower Body (0.2s)')[0])

        elif restype == 'Individual Lower Body':

            xa, ya = eggXY(1.8 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'), 2.6 * cond * coef(ht, 'x'))
            xaa, yaa = eggXY(1.5 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'),
                             2.2 * cond * coef(ht, 'x'))
            xb, yb = eggXZ(1.8 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'), 1.8 * cond * coef(ht, 'z'),
                           4.8 * cond * coef(ht, 'z'))
            xbb, ybb = eggXZ(1.5 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'),
                             1.2 * cond * coef(ht, 'z'), 4.5 * cond * coef(ht, 'z'))
            xc, yc = eggYZ(2.6 * cond * coef(ht, 'z'), 1.8 * cond * coef(ht, 'z'), 4.8 * cond * coef(ht, 'z'))
            xcc, ycc = eggYZ(2.2 * cond * coef(ht, 'z'), 1.2 * cond * coef(ht, 'z'),
                             4.5 * cond * coef(ht, 'z'))

            a31 = np.maximum(frontASTM, np.array([-1.8, -1.5, -1.1, -1.1]) * coefX)
            a32 = np.minimum(backASTM, np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2, 2, 2, 2]) * coefX)
            a33 = np.minimum(lrASTM, np.array([2.6, 2.2, 2.2, 1.5, 1.5]) * coefX)
            a34 = np.maximum(upASTM, np.array([-1.8, -1.2, -0.9, -0.9, -0.6, -0.6]) * coefZ)
            a35 = np.minimum(downASTM, np.array([4.8, 4.5, 4.5, 3.2, 3.2, 2.5, 2.5, 1.8, 1.8]) * coefZ)

            self.lined4.append(self.axe_eggxy.plot(xa, ya, 'k', label='Individual Lower Body (0s)')[0])
            self.lined4.append(self.axe_eggxy.plot(xaa, yaa, 'k--', label='Individual Lower Body (0.2s)')[0])
            self.lined5.append(self.axe_eggxz.plot(xb, yb, 'k', label='Individual Lower Body (0s)')[0])
            self.lined5.append(self.axe_eggxz.plot(xbb, ybb, 'k--', label='Individual Lower Body (0.2s)')[0])
            self.lined6.append(self.axe_eggyz.plot(xc, yc, 'k', label='Individual Lower Body (0s)')[0])
            self.lined6.append(self.axe_eggyz.plot(xcc, ycc, 'k--', label='Individual Lower Body (0.2s)')[0])



        elif restype == 'No Restraint' or restype == 'Convenience Restraint':

            xa, ya = eggXY(1.5 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'), 1.8 * cond * coef(ht, 'x'))
            xaa, yaa = eggXY(1.2 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'),
                             1.2 * cond * coef(ht, 'x'))
            xb, yb = eggXZ(1.5 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'), 1.2 * cond * coef(ht, 'z'),
                           3 * cond * coef(ht, 'z'))
            xbb, ybb = eggXZ(1.2 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'),
                             0.8 * cond * coef(ht, 'z'), 2.8 * cond * coef(ht, 'z'))
            xc, yc = eggYZ(1.8 * cond * coef(ht, 'z'), 1.2 * cond * coef(ht, 'z'), 3 * cond * coef(ht, 'z'))
            xcc, ycc = eggYZ(1.2 * cond * coef(ht, 'z'), 0.8 * cond * coef(ht, 'z'),
                             2.8 * cond * coef(ht, 'z'))

            a31 = np.maximum(frontASTM, np.array([-1.5, -1.2, -0.7, -0.7]) * coefX)
            a32 = np.minimum(backASTM, np.array([2.5, 2.5, 2.5, 2.5, 2.5, 2, 2, 2, 2]) * coefX)
            a33 = np.minimum(lrASTM, np.array([1.8, 1.2, 1.2, 0.7, 0.7]) * coefX)
            a34 = np.maximum(upASTM, np.array([-0.2, 0.2, 0.2, 0.2, 0.2, 0.2]) * coefZ)
            a35 = np.minimum(downASTM, np.array([4, 3.8, 3.8, 2.8, 2.8, 2.2, 2.2, 1.6, 1.6]) * coefZ)

            self.lined4.append(self.axe_eggxy.plot(xa, ya, 'k', label='No/Conv Restraint (0s)')[0])
            self.lined4.append(self.axe_eggxy.plot(xaa, yaa, 'k--', label='No/Conv Restraint (0.2s)')[0])
            self.lined5.append(self.axe_eggxz.plot(xb, 1 + yb, 'k', label='No/Conv Restraint (0s)')[0])
            self.lined5.append(self.axe_eggxz.plot(xbb, 1 + ybb, 'k--', label='No/Conv Restraint (0.2s)')[0])
            self.lined6.append(self.axe_eggyz.plot(xc, 1 + yc, 'k', label='No/Conv Restraint (0s)')[0])
            self.lined6.append(self.axe_eggyz.plot(xcc, 1 + ycc, 'k--', label='No/Conv Restraint (0.2s)')[0])

        self.lined1.append(self.axe_ax.plot([0, 0.2, 0.5, 14], a31, 'r', linewidth=2, label=restype)[0])
        self.lined1.append(self.axe_ax.plot([0, 0.2, 1, 2, 4, 5, 11.8, 12, 14], a32, 'r',linewidth=2,)[0])
        self.lined2.append(self.axe_ay.plot([0, 0.2, 1, 2, 14], a33, 'r',linewidth=2, label=restype)[0])
        self.lined3.append(self.axe_az.plot([0, 0.2, 0.5, 4, 7, 14], a34, 'r',linewidth=2,)[0])
        self.lined3.append(self.axe_az.plot([0, 0.2, 1, 2, 4, 5, 11.8, 12, 14], a35, 'r', linewidth=2,label=restype)[0])


        for ax in self.get_all_axe_list():
            ax.legend()


class ZReversalPlot(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=18, height=12, dpi=100, data=None):
        self.fig = Figure(figsize=(width, height), dpi=dpi, layout='constrained')
        super(ZReversalPlot, self).__init__(self.fig)
        
        self.linez = []
        self.reversal_markers = []
        self.annots = []
        self.annot_mode = 'Single'
        self.reversal_info_text = None
        self.initplotxyz()
    
    def initplotxyz(self):
        try:
            for ax in self.get_all_axe_list():
                ax.remove()
            for line in self.get_all_line_list():
                line.remove()
        except:
            pass
        
        self.linez = []
        self.reversal_markers = []
        self.reversal_info_text = None
        
        # Create grid spec: plot (height=5) and info text (height=1)
        self.gs = self.fig.add_gridspec(2, 1, height_ratios=[5, 1], hspace=0.3)
        self.axe_z = self.fig.add_subplot(self.gs[0, 0])
        
        # Create info axes below the plot
        self.info_ax = self.fig.add_subplot(self.gs[1, 0])
        self.info_ax.axis('off')
        
        self.axe_z.set_xlabel('Time (s)')
        self.axe_z.set_ylabel('Z Acceleration (g)')
        self.axe_z.set_title('Z Acceleration Reversal Analysis')
        self.axe_z.axhline(y=0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
        self.axe_z.legend(loc='upper right')
        self.fig.canvas.draw_idle()
    
    def get_all_axe_list(self):
        return [self.axe_z, self.info_ax]
    
    def get_all_line_list(self):
        line_list = []
        for axs in [self.linez, self.reversal_markers]:
            for line in axs:
                line_list.append(line)
        return line_list
    
    def plot_z_data(self, time_data, z_data, reversals):
        try:
            for annot in self.annots:
                annot.remove()
        except:
            pass
        
        self.removelines()
        
        # Plot Z acceleration data
        line, = self.axe_z.plot(time_data, z_data, 'b-', linewidth=1, label='Z Acceleration')
        self.linez.append(line)
        
        # Mark reversals
        colors = ['red', 'green', 'orange', 'purple', 'cyan', 'magenta']
        
        for i, reversal in enumerate(reversals):
            color = colors[i % len(colors)]
            
            # Highlight the 0.133s window
            window_start = reversal['window_start']
            window_end = reversal['window_end']
            self.axe_z.axvspan(window_start, window_end, alpha=0.2, color=color)
            
            # Mark min and max points
            min_time = reversal['min_time']
            max_time = reversal['max_time']
            min_val = reversal['min_value']
            max_val = reversal['max_value']
            
            marker_min, = self.axe_z.plot(min_time, min_val, 'v', color=color, markersize=10)
            marker_max, = self.axe_z.plot(max_time, max_val, '^', color=color, markersize=10)
            self.reversal_markers.append(marker_min)
            self.reversal_markers.append(marker_max)
        
        # Create info text below the plot
        if len(reversals) > 0:
            info_text = "Excessive Z-acceleration transitions found:\n"
            for i, reversal in enumerate(reversals):
                info_text += f"  {i+1}. Time {reversal['window_start']:.3f}s to {reversal['window_end']:.3f}s"
                info_text += f" (min={reversal['min_value']:.3f}g at {reversal['min_time']:.3f}s, "
                info_text += f"max={reversal['max_value']:.3f}g at {reversal['max_time']:.3f}s)\n"
        else:
            info_text = "No excessive Z-acceleration transitions found."
        
        self.reversal_info_text = self.info_ax.text(0.01, 0.5, info_text, transform=self.info_ax.transAxes,
                                                     fontsize=9, verticalalignment='center',
                                                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        self.fig.canvas.draw_idle()
        self.fig.canvas.mpl_connect("button_press_event", self.onclick)
    
    def removelines(self):
        try:
            for line in self.linez:
                line.remove()
            for marker in self.reversal_markers:
                marker.remove()
            if self.reversal_info_text is not None:
                self.reversal_info_text.remove()
                self.reversal_info_text = None
            self.linez = []
            self.reversal_markers = []
        except:
            pass
    
    def update_annot(self, ax, line, ind):
        try:
            x, y = line.get_data()
            annot = ax.annotate("", xy=(x[ind["ind"][0]], y[ind["ind"][0]]), 
                              xytext=(10+x[ind["ind"][0]], 10+y[ind["ind"][0]]), 
                              textcoords="offset points",
                              bbox=dict(boxstyle="round", fc="b", alpha=0.1),
                              arrowprops=dict(arrowstyle="->"))
            
            text = "t = {:.3f}s\naz = {:.4f}".format(x[ind["ind"][0]], y[ind["ind"][0]])
            annot.set_text(text)
            annot.set_visible(True)
            annot.set_fontsize(8)
            self.annots.append(annot)
        except Exception as e:
            print(e)
    
    def onclick(self, event):
        if self.annot_mode == "Single":
            try:
                for annot in self.annots:
                    annot.set_visible(False)
                self.annots = []
            except:
                pass
        
        if event.inaxes in self.get_all_axe_list():
            for line in self.get_all_line_list():
                try:
                    cont, ind = line.contains(event)
                    if cont:
                        self.update_annot(event.inaxes, line, ind)
                        self.fig.canvas.draw_idle()
                        break
                except Exception as e:
                    pass