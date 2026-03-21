"""
PyQtGraph-based plotting module for BERT Reader
Provides high-performance, interactive plots as alternatives to matplotlib
"""

import pyqtgraph as pg
from PyQt5 import QtWidgets, QtCore, QtGui
import numpy as np
from sci_calculation import ProcessGB, ProcessASTM
from constants import get_time_interval

# Configure pyqtgraph globally
pg.setConfigOptions(useOpenGL=True, antialias=True, foreground='k', background='w')


class BasePlotWidget(QtWidgets.QWidget):
    """Base class for all plot widgets with common functionality."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.annot_mode = 'Single'
        self.annotations = []
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI layout - override in subclasses."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.graphics_layout = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics_layout)
        
    def clear_annotations(self):
        """Clear all annotations from the plot."""
        for annot in self.annotations:
            annot.setParentItem(None)
        self.annotations = []
        
    def add_annotation(self, plot, x, y, text):
        """Add an annotation to the plot."""
        label = pg.TextItem(text, anchor=(0, 1), color='b', fill=(255, 255, 255, 200))
        label.setPos(x, y)
        plot.addItem(label)
        self.annotations.append(label)
        return label


class TrendPlot(BasePlotWidget):
    """High-performance trend plot for acceleration data (replaces MplCanvas)."""
    
    def __init__(self, parent=None):
        self.linex = []
        self.liney = []
        self.linez = []
        super().__init__(parent)
        
    def setup_ui(self):
        super().setup_ui()
        self.initplotxyz()
        
    def initplotxyz(self):
        """Initialize the three-axis trend plot."""
        self.graphics_layout.clear()
        self.linex = []
        self.liney = []
        self.linez = []
        self.annotations = []
        
        # Create three plots with shared X axis
        self.plot_x = self.graphics_layout.addPlot(row=0, col=0, name="PlotX")
        self.plot_y = self.graphics_layout.addPlot(row=1, col=0, name="PlotY")
        self.plot_z = self.graphics_layout.addPlot(row=2, col=0, name="PlotZ")
        
        # Link X axes
        self.plot_y.setXLink(self.plot_x)
        self.plot_z.setXLink(self.plot_x)
        
        # Set labels
        self.plot_x.setLabel('left', 'Fore/Aft', units='g')
        self.plot_y.setLabel('left', 'Lateral', units='g')
        self.plot_y.setLabel('bottom', 'Time', units='s')
        self.plot_z.setLabel('left', 'Vertical', units='g')
        self.plot_z.setLabel('bottom', 'Time', units='s')
        
        # Configure plot appearance
        for plot in [self.plot_x, self.plot_y, self.plot_z]:
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setMenuEnabled(False)
            plot.enableAutoRange()
            
    def addplotxyz(self, list_data, plot_order, color='b'):
        """Add a new dataset to the plot."""
        self.clear_annotations()
        
        # Convert color to Qt color
        qt_color = QtGui.QColor(color)
        pen = pg.mkPen(color=qt_color, width=1.5)
        
        # Plot data
        x_data = list_data.iloc[:, 1].values
        y_data = list_data.iloc[:, 2].values
        z_data = list_data.iloc[:, 3].values
        time_data = list_data.iloc[:, 0].values
        
        line_x = self.plot_x.plot(time_data, x_data, pen=pen, name=f'X-{plot_order}')
        line_y = self.plot_y.plot(time_data, y_data, pen=pen, name=f'Y-{plot_order}')
        line_z = self.plot_z.plot(time_data, z_data, pen=pen, name=f'Z-{plot_order}')
        
        self.linex.append(line_x)
        self.liney.append(line_y)
        self.linez.append(line_z)
        
    def removelines(self):
        """Remove all plotted lines."""
        for line in self.linex + self.liney + self.linez:
            line.clear()
        self.linex = []
        self.liney = []
        self.linez = []


class GBPlotWidget(BasePlotWidget):
    """GB Standard contour plot (replaces GBPlot)."""
    
    def __init__(self, parent=None):
        self.lineay = []
        self.lineaz = []
        self.lineacomb = []
        super().__init__(parent)
        
    def setup_ui(self):
        super().setup_ui()
        self.initplotxyz()
        
    def initplotxyz(self):
        """Initialize GB standard plot with three subplots."""
        self.graphics_layout.clear()
        self.lineay = []
        self.lineaz = []
        self.lineacomb = []
        self.annotations = []
        
        # Create three plots
        self.plot_ay = self.graphics_layout.addPlot(row=0, col=0, title="GB Standard - Lateral (ay)")
        self.plot_az = self.graphics_layout.addPlot(row=0, col=1, title="GB Standard - Vertical (az)")
        self.plot_comb = self.graphics_layout.addPlot(row=1, col=0, colspan=2, title="GB Standard - Combined (ay vs az)")
        
        # Configure plots
        for plot in [self.plot_ay, self.plot_az, self.plot_comb]:
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setMenuEnabled(False)
            plot.addLegend()
            
        self.plot_ay.setLabel('left', '|ay|', units='g')
        self.plot_ay.setLabel('bottom', 'dt', units='s')
        self.plot_ay.setXRange(0, 4)
        self.plot_ay.setYRange(0, 5)
        
        self.plot_az.setLabel('left', 'az', units='g')
        self.plot_az.setLabel('bottom', 'dt', units='s')
        self.plot_az.setXRange(0, 4)
        self.plot_az.setYRange(-2, 6)
        
        self.plot_comb.setLabel('left', 'ay', units='g')
        self.plot_comb.setLabel('bottom', 'az', units='g')
        self.plot_comb.setXRange(-2, 6)
        self.plot_comb.setYRange(-3.2, 3.2)
        
    def _plot_gb_limits(self):
        """Plot GB standard limit lines."""
        # ay limits
        x_ay = [0.01, 0.2, 1, 4]
        y_ay_pos = [5, 2, 2, 2]
        y_ay_neg = [-5, -2, -2, -2]
        
        pen_red = pg.mkPen(color='r', width=3)
        self.plot_ay.plot(x_ay, y_ay_pos, pen=pen_red, name='Allowable ay')
        self.plot_ay.plot(x_ay, y_ay_neg, pen=pen_red)
        
        # az limits
        x_az = [0, 1, 2, 3, 4]
        y_az_pos = [6, 6, 4, 4, 4]
        y_az_neg = [-2, -1.5, -1.5, -1.5, -1.5]
        
        self.plot_az.plot(x_az, y_az_pos, pen=pen_red, name='Allowable az')
        self.plot_az.plot(x_az, y_az_neg, pen=pen_red)
        
        # Combined limits (simplified)
        x_comb = [-1.8, -1.62, -0.54, 0, 1.8, 5.4, 6]
        y_comb_pos = [0, 0.6, 1.8, 2, 1.8, 0.6, 0]
        y_comb_neg = [0, -0.6, -1.8, -2, -1.8, -0.6, 0]
        
        pen_yellow = pg.mkPen(color='y', width=2)
        self.plot_comb.plot(x_comb, y_comb_pos, pen=pen_yellow, name='dt=0.05s')
        self.plot_comb.plot(x_comb, y_comb_neg, pen=pen_yellow)
        
    def addplotxyz(self, data):
        """Add measured data to GB plot."""
        self.clear_annotations()
        self.removelines()
        
        # Extended x_axis_gb with denser sampling
        fs = 500
        x_axis_gb = self._generate_gb_time_axis()
        window_sizes = [int(t * fs) for t in x_axis_gb]
        
        # Get instantaneous values
        d0py = max(0, np.max(data.iloc[:, 2]))
        d0ny = min(0, np.min(data.iloc[:, 2]))
        d0pz = max(1, np.max(data.iloc[:, 3]))
        d0nz = min(1, np.min(data.iloc[:, 3]))
        
        # Calculate sustained acceleration
        results_p = []
        results_n = []
        
        for dt in window_sizes:
            dp, dn = ProcessGB(data, dt)
            results_p.append(dp)
            results_n.append(dn)
        
        # Extract values
        x_axis_gb_plot = [0.002] + x_axis_gb
        p1 = [d0py] + [r[0] for r in results_p]
        p2 = [d0ny] + [r[0] for r in results_n]
        p3 = [d0pz] + [r[1] for r in results_p]
        p4 = [d0nz] + [r[1] for r in results_n]
        
        pen_blue = pg.mkPen(color='b', width=2)
        pen_black = pg.mkPen(color='k', width=2)
        pen_cyan = pg.mkPen(color='c', width=1.5)
        
        # Plot ay
        self.lineay.append(self.plot_ay.plot(x_axis_gb_plot, p1, pen=pen_blue, name='Measured ay(+)'))
        self.lineay.append(self.plot_ay.plot(x_axis_gb_plot, p2, pen=pen_black, name='Measured ay(-)'))
        
        # Plot az
        self.lineaz.append(self.plot_az.plot(x_axis_gb_plot, p3, pen=pen_blue, name='Measured az(+)'))
        self.lineaz.append(self.plot_az.plot(x_axis_gb_plot, p4, pen=pen_black, name='Measured az(-)'))
        
        # Plot combined
        z_array = data.iloc[:, 3].values
        y_array = data.iloc[:, 2].values
        self.lineacomb.append(self.plot_comb.plot(z_array, y_array, pen=pen_cyan, symbol='o', 
                                                   symbolSize=3, symbolBrush='c', name='Measured Data'))
        
    def _generate_gb_time_axis(self):
        """Generate time axis for GB standard calculations."""
        x_axis_gb = []
        # 0.02 to 0.1: 0.0025s increments
        x_axis_gb.extend(np.arange(0.02, 0.1, 0.0025))
        # 0.1 to 0.2: 0.005s increments
        x_axis_gb.extend(np.arange(0.1, 0.2, 0.005))
        # 0.2 to 0.5: 0.01s increments
        x_axis_gb.extend(np.arange(0.2, 0.5, 0.01))
        # 0.5 to 1: 0.025s increments
        x_axis_gb.extend(np.arange(0.5, 1, 0.025))
        # 1 to 2: 0.05s increments
        x_axis_gb.extend(np.arange(1, 2, 0.05))
        # 2 to 5: 0.1s increments
        x_axis_gb.extend(np.arange(2, 5, 0.1))
        # 5 to 14: 0.25s increments
        x_axis_gb.extend(np.arange(5, 14.25, 0.25))
        return x_axis_gb
        
    def removelines(self):
        """Remove all measured data lines."""
        for line in self.lineay + self.lineaz + self.lineacomb:
            line.clear()
        self.lineay = []
        self.lineaz = []
        self.lineacomb = []


# Helper functions for ASTM egg-shaped contours
def eggXY(a, b, c):
    """Generate egg-shaped contour for XY plane."""
    theta = np.linspace(0, 2*np.pi, 200)
    x = a * np.cos(theta)
    y = np.where(np.abs(theta - np.pi) < np.pi/2,
                 c * np.sin(theta),
                 b * np.sin(theta))
    return x, y


def eggXZ(a, b, c, d):
    """Generate egg-shaped contour for XZ plane."""
    theta = np.linspace(0, 2*np.pi, 200)
    x = np.where(np.abs(theta - np.pi) < np.pi/2,
                 a * np.cos(theta),
                 b * np.cos(theta))
    z = np.where(np.abs(theta - np.pi/2) < np.pi/2,
                 c * np.sin(theta),
                 d * np.sin(theta))
    return x, z


def eggYZ(a, b, c):
    """Generate egg-shaped contour for YZ plane."""
    theta = np.linspace(0, 2*np.pi, 200)
    y = a * np.cos(theta)
    z = np.where(np.abs(theta - np.pi/2) < np.pi/2,
                 b * np.sin(theta),
                 c * np.sin(theta))
    return y, z


def coef(ht, axis):
    """Calculate height coefficient for ASTM limits."""
    if axis == 'x':
        return 1.0  # Simplified - would use actual height-based coefficient
    else:
        return 1.0


class ASTMPlotWidget(BasePlotWidget):
    """ASTM Standard contour plot (replaces ASTMPlot)."""
    
    def __init__(self, parent=None):
        self.lineax = []
        self.lineay = []
        self.lineaz = []
        self.lineeggxy = []
        self.lineeggxz = []
        self.lineeggyz = []
        self.lined1 = []
        self.lined2 = []
        self.lined3 = []
        self.lined4 = []
        self.lined5 = []
        self.lined6 = []
        super().__init__(parent)
        
    def setup_ui(self):
        super().setup_ui()
        self.initplotxyz()
        
    def initplotxyz(self):
        """Initialize ASTM plot with 6 subplots."""
        self.graphics_layout.clear()
        self.lineax = []
        self.lineay = []
        self.lineaz = []
        self.lineeggxy = []
        self.lineeggxz = []
        self.lineeggyz = []
        self.lined1 = []
        self.lined2 = []
        self.lined3 = []
        self.lined4 = []
        self.lined5 = []
        self.lined6 = []
        self.annotations = []
        
        # Create 6 plots in 2x3 grid
        self.plot_ax = self.graphics_layout.addPlot(row=0, col=0, title="ax vs dt")
        self.plot_ay = self.graphics_layout.addPlot(row=0, col=1, title="ay vs dt")
        self.plot_az = self.graphics_layout.addPlot(row=0, col=2, title="az vs dt")
        self.plot_eggxy = self.graphics_layout.addPlot(row=1, col=0, title="Front <=> Back vs Left <=> Right")
        self.plot_eggxz = self.graphics_layout.addPlot(row=1, col=1, title="Front <=> Back vs Up <=> Down")
        self.plot_eggyz = self.graphics_layout.addPlot(row=1, col=2, title="Left <=> Right vs Up <=> Down")
        
        # Configure all plots
        for plot in [self.plot_ax, self.plot_ay, self.plot_az, self.plot_eggxy, self.plot_eggxz, self.plot_eggyz]:
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setMenuEnabled(False)
            plot.addLegend()
            
        # Set labels and ranges
        self.plot_ax.setLabel('left', 'ax', units='g')
        self.plot_ax.setLabel('bottom', 'dt', units='s')
        self.plot_ax.setXRange(0, 14)
        
        self.plot_ay.setLabel('left', 'ay', units='g')
        self.plot_ay.setLabel('bottom', 'dt', units='s')
        self.plot_ay.setXRange(0, 14)
        self.plot_ay.setYRange(0, 3.2)
        
        self.plot_az.setLabel('left', 'az', units='g')
        self.plot_az.setLabel('bottom', 'dt', units='s')
        self.plot_az.setXRange(0, 14)
        
        self.plot_eggxy.setLabel('left', 'Left <=> Right')
        self.plot_eggxy.setLabel('bottom', 'Front <=> Back')
        self.plot_eggxy.setXRange(-2.1, 6.1)
        self.plot_eggxy.setYRange(-3.2, 3.2)
        
        self.plot_eggxz.setLabel('left', 'Up <=> Down')
        self.plot_eggxz.setLabel('bottom', 'Front <=> Back')
        self.plot_eggxz.setXRange(-2.1, 6.1)
        self.plot_eggxz.setYRange(-2.2, 6.2)
        
        self.plot_eggyz.setLabel('left', 'Up <=> Down')
        self.plot_eggyz.setLabel('bottom', 'Left <=> Right')
        self.plot_eggyz.setXRange(-3.1, 3.1)
        self.plot_eggyz.setYRange(-2.2, 6.2)
        
    def removelines(self):
        """Remove measured data lines."""
        for line in self.lineax + self.lineay + self.lineaz + self.lineeggxy + self.lineeggxz + self.lineeggyz:
            line.clear()
        self.lineax = []
        self.lineay = []
        self.lineaz = []
        self.lineeggxy = []
        self.lineeggxz = []
        self.lineeggyz = []
        
    def addplotxyz(self, data, restraint, cond, input_height):
        """Add data with ASTM standard fitting."""
        self.clear_annotations()
        self.removelines()
        self._clear_std_lines()
        
        # Extended x_axis with 2x denser sampling
        fs = 500
        x_axis = [
            0.02, 0.0225, 0.025, 0.0275, 0.03, 0.0325, 0.035, 0.0375,
            0.04, 0.0425, 0.045, 0.0475, 0.05, 0.0525, 0.055, 0.0575,
            0.06, 0.0625, 0.065, 0.0675, 0.07, 0.0725, 0.075, 0.0775,
            0.08, 0.0825, 0.085, 0.0875, 0.09, 0.0925, 0.095, 0.0975,
            0.1, 0.105, 0.11, 0.115, 0.12, 0.125, 0.13, 0.135, 0.14, 0.145,
            0.15, 0.155, 0.16, 0.165, 0.17, 0.175, 0.18, 0.185, 0.19, 0.195,
            0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27, 0.28, 0.29,
            0.3, 0.31, 0.32, 0.33, 0.34, 0.35, 0.36, 0.37, 0.38, 0.39,
            0.4, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48, 0.49,
            0.5, 0.525, 0.55, 0.575, 0.6, 0.625, 0.65, 0.675, 0.7, 0.725,
            0.75, 0.775, 0.8, 0.825, 0.85, 0.875, 0.9, 0.925, 0.95, 0.975,
            1, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.45,
            1.5, 1.55, 1.6, 1.65, 1.7, 1.75, 1.8, 1.85, 1.9, 1.95,
            2, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9,
            3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9,
            4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9,
            5, 5.25, 5.5, 5.75, 6, 6.25, 6.5, 6.75, 7, 7.25,
            7.5, 7.75, 8, 8.25, 8.5, 8.75, 9, 9.25, 9.5, 9.75,
            10, 10.25, 10.5, 10.75, 11, 11.25, 11.5, 11.75, 12, 12.25,
            12.5, 12.75, 13, 13.25, 13.5, 13.75, 14
        ]
        
        window_sizes = [int(t * fs) for t in x_axis]
        
        results_p = []
        results_n = []
        
        for dt in window_sizes:
            dp, dn = ProcessASTM(data, dt)
            results_p.append(dp)
            results_n.append(dn)
        
        ax_p = [r[0] for r in results_p]
        ax_n = [r[0] for r in results_n]
        ay_p = [r[1] for r in results_p]
        ay_n = [r[1] for r in results_n]
        az_p = [r[2] for r in results_p]
        az_n = [r[2] for r in results_n]
        
        pen_blue = pg.mkPen(color='b', width=1.5)
        pen_green = pg.mkPen(color='g', width=1.5)
        pen_cyan = pg.mkPen(color='c', width=1.5)
        
        # Plot sustained acceleration curves
        self.lineax.append(self.plot_ax.plot(x_axis, ax_p, pen=pen_blue, name='Measured ax (+)'))
        self.lineax.append(self.plot_ax.plot(x_axis, ax_n, pen=pen_green, name='Measured ax (-)'))
        self.lineay.append(self.plot_ay.plot(x_axis, ay_p, pen=pen_blue, name='Measured ay (Right)'))
        self.lineay.append(self.plot_ay.plot(x_axis, [-v for v in ay_n], pen=pen_green, name='Measured ay (Left)'))
        self.lineaz.append(self.plot_az.plot(x_axis, az_p, pen=pen_blue, name='Measured az (Down)'))
        self.lineaz.append(self.plot_az.plot(x_axis, az_n, pen=pen_green, name='Measured az (Up)'))
        
        # Plot egg data
        x_data = data.iloc[:, 1].values
        y_data = data.iloc[:, 2].values
        z_data = data.iloc[:, 3].values
        
        self.lineeggxy.append(self.plot_eggxy.plot(x_data, y_data, pen=pen_cyan, symbol='o', 
                                                    symbolSize=3, symbolBrush='c', name='Measured'))
        self.lineeggxz.append(self.plot_eggxz.plot(x_data, z_data, pen=pen_cyan, symbol='o', 
                                                    symbolSize=3, symbolBrush='c', name='Measured'))
        self.lineeggyz.append(self.plot_eggyz.plot(y_data, z_data, pen=pen_cyan, symbol='o', 
                                                    symbolSize=3, symbolBrush='c', name='Measured'))
        
        # Add Disney/ASTM standard lines
        self.addDisneyStd(restraint, cond, input_height)
        
    def _clear_std_lines(self):
        """Clear standard lines."""
        for lines in [self.lined1, self.lined2, self.lined3, self.lined4, self.lined5, self.lined6]:
            for line in lines:
                line.clear()
        self.lined1 = []
        self.lined2 = []
        self.lined3 = []
        self.lined4 = []
        self.lined5 = []
        self.lined6 = []
        
    def addDisneyStd(self, restype, cond, height):
        """Add ASTM standard contour lines."""
        if cond == 'E-Stop':
            cond = 1.25
        elif cond == "Normal":
            cond = 1
        else:
            cond = 1.25
            
        ht = float(height) if height else 0
        coefX = cond * coef(ht, 'x')
        coefZ = cond * coef(ht, 'z')
        
        frontASTM = [-2, -2, -1.5, -1.5]
        backASTM = [6, 6, 6, 4, 4, 3, 3, 2.5, 2.5]
        lrASTM = [3, 3, 3, 2, 2]
        upASTM = [-2, -2, -1.5, -1.5, -1.2, -1.2]
        downASTM = [6, 6, 6, 4, 4, 3, 3, 2, 2]
        
        pen_red = pg.mkPen(color='r', width=3)
        pen_black = pg.mkPen(color='k', width=2)
        pen_red_dash = pg.mkPen(color='r', width=2, style=QtCore.Qt.PenStyle.DashLine)
        pen_black_dash = pg.mkPen(color='k', width=2, style=QtCore.Qt.PenStyle.DashLine)
        
        # Base ASTM limits
        x3, y3 = eggXY(2 * coef(ht, 'x'), 6 * coef(ht, 'x'), 3 * coef(ht, 'x'))
        x4, y4 = eggXZ(2 * coef(ht, 'z'), 6 * coef(ht, 'z'), 2 * coef(ht, 'z'), 6 * coef(ht, 'z'))
        x5, y5 = eggYZ(3 * coef(ht, 'z'), 2 * coef(ht, 'z'), 6 * coef(ht, 'z'))
        
        # Plot ax limits
        self.lined1.append(self.plot_ax.plot([0.2, 0.5, 14], [-2, -1.5, -1.5], pen=pen_red, name='Allowable ax'))
        self.lined1.append(self.plot_ax.plot([0.2, 1, 2, 4, 5, 11.8, 12, 14], 
                                              np.array([6, 6, 4, 4, 3, 3, 2.5, 2.5]) * coef(ht, 'x'), 
                                              pen=pen_red))
        
        # Plot ay limits
        self.lined2.append(self.plot_ay.plot([0.2, 1, 2, 14], np.array([3, 3, 2, 2]) * coef(ht, 'x'), 
                                              pen=pen_red, name='Allowable ay'))
        
        # Plot az limits
        self.lined3.append(self.plot_az.plot([0.2, 0.5, 4, 7, 14], np.array([-2, -1.5, -1.5, -1.2, -1.2]) * coef(ht, 'x'), 
                                              pen=pen_red, name='Allowable az'))
        self.lined3.append(self.plot_az.plot([0.2, 1, 2, 4, 5, 11.8, 12, 14], 
                                              np.array([6, 6, 4, 4, 3, 3, 2, 2]) * coef(ht, 'x'), 
                                              pen=pen_red))
        
        # Plot egg contours
        self.lined4.append(self.plot_eggxy.plot(x3, y3, pen=pen_red_dash, name='ASTM (0.2s)'))
        self.lined4.append(self.plot_eggxy.plot([-2, 6], [0, 0], pen=pg.mkPen(color='k', width=3)))
        self.lined4.append(self.plot_eggxy.plot([0, 0], [3, -3], pen=pg.mkPen(color='k', width=3)))
        
        self.lined5.append(self.plot_eggxz.plot(x4, y4, pen=pen_red_dash, name='ASTM (0.2s)'))
        self.lined5.append(self.plot_eggxz.plot([-2, 6], [0, 0], pen=pg.mkPen(color='k', width=3)))
        self.lined5.append(self.plot_eggxz.plot([0, 0], [6, -2], pen=pg.mkPen(color='k', width=3)))
        
        self.lined6.append(self.plot_eggyz.plot(x5, y5, pen=pen_red_dash, name='ASTM (0.2s)'))
        self.lined6.append(self.plot_eggyz.plot([-3, 3], [0, 0], pen=pg.mkPen(color='k', width=3)))
        self.lined6.append(self.plot_eggyz.plot([0, 0], [-2, 6], pen=pg.mkPen(color='k', width=3)))
        
        # Restraint-specific contours
        if restype == 'Upper Body':
            xa, ya = eggXY(2 * cond * coef(ht, 'x'), 3.6 * cond * coef(ht, 'x'), 3 * cond * coef(ht, 'x'))
            xaa, yaa = eggXY(1.6 * cond * coef(ht, 'x'), 3.6 * cond * coef(ht, 'x'), 2.4 * cond * coef(ht, 'x'))
            xb, yb = eggXZ(2 * cond * coef(ht, 'z'), 3.6 * cond * coef(ht, 'z'), 2 * cond * coef(ht, 'z'), 5 * cond * coef(ht, 'z'))
            xbb, ybb = eggXZ(1.6 * cond * coef(ht, 'z'), 3.6 * cond * coef(ht, 'z'), 1.4 * cond * coef(ht, 'z'), 4.8 * cond * coef(ht, 'z'))
            xc, yc = eggYZ(3 * cond * coef(ht, 'z'), 2 * cond * coef(ht, 'z'), 5 * cond * coef(ht, 'z'))
            xcc, ycc = eggYZ(2.4 * cond * coef(ht, 'z'), 1.4 * cond * coef(ht, 'z'), 4.8 * cond * coef(ht, 'z'))
            
            self.lined4.append(self.plot_eggxy.plot(xa, ya, pen=pen_black, name='Upper Body (0s)'))
            self.lined4.append(self.plot_eggxy.plot(xaa, yaa, pen=pen_black_dash, name='Upper Body (0.2s)'))
            self.lined5.append(self.plot_eggxz.plot(xb, yb, pen=pen_black, name='Upper Body (0s)'))
            self.lined5.append(self.plot_eggxz.plot(xbb, ybb, pen=pen_black_dash, name='Upper Body (0.2s)'))
            self.lined6.append(self.plot_eggyz.plot(xc, yc, pen=pen_black, name='Upper Body (0s)'))
            self.lined6.append(self.plot_eggyz.plot(xcc, ycc, pen=pen_black_dash, name='Upper Body (0.2s)'))
            
        elif restype == 'Group Lower Body':
            xa, ya = eggXY(1.7 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'), 2.4 * cond * coef(ht, 'x'))
            xaa, yaa = eggXY(1.4 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'), 2.1 * cond * coef(ht, 'x'))
            xb, yb = eggXZ(1.7 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'), 2 * cond * coef(ht, 'z'), 3.5 * cond * coef(ht, 'z'))
            xbb, ybb = eggXZ(1.4 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'), 1 * cond * coef(ht, 'z'), 3 * cond * coef(ht, 'z'))
            xc, yc = eggYZ(2.4 * cond * coef(ht, 'z'), 2 * cond * coef(ht, 'z'), 3.5 * cond * coef(ht, 'z'))
            xcc, ycc = eggYZ(2.1 * cond * coef(ht, 'z'), 1 * cond * coef(ht, 'z'), 3 * cond * coef(ht, 'z'))
            
            self.lined4.append(self.plot_eggxy.plot(xa, ya, pen=pen_black, name='Group Lower Body (0s)'))
            self.lined4.append(self.plot_eggxy.plot(xaa, yaa, pen=pen_black_dash, name='Group Lower Body (0.2s)'))
            self.lined5.append(self.plot_eggxz.plot(xb, 1 + yb, pen=pen_black, name='Group Lower Body (0s)'))
            self.lined5.append(self.plot_eggxz.plot(xbb, 1 + ybb, pen=pen_black_dash, name='Group Lower Body (0.2s)'))
            self.lined6.append(self.plot_eggyz.plot(xc, 1 + yc, pen=pen_black, name='Group Lower Body (0s)'))
            self.lined6.append(self.plot_eggyz.plot(xcc, 1 + ycc, pen=pen_black_dash, name='Group Lower Body (0.2s)'))
            
        elif restype == 'Individual Lower Body':
            xa, ya = eggXY(1.8 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'), 2.6 * cond * coef(ht, 'x'))
            xaa, yaa = eggXY(1.5 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'), 2.2 * cond * coef(ht, 'x'))
            xb, yb = eggXZ(1.8 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'), 1.8 * cond * coef(ht, 'z'), 4.8 * cond * coef(ht, 'z'))
            xbb, ybb = eggXZ(1.5 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'), 1.2 * cond * coef(ht, 'z'), 4.5 * coef(ht, 'z'))
            xc, yc = eggYZ(2.6 * cond * coef(ht, 'z'), 1.8 * cond * coef(ht, 'z'), 4.8 * cond * coef(ht, 'z'))
            xcc, ycc = eggYZ(2.2 * cond * coef(ht, 'z'), 1.2 * cond * coef(ht, 'z'), 4.5 * cond * coef(ht, 'z'))
            
            self.lined4.append(self.plot_eggxy.plot(xa, ya, pen=pen_black, name='Individual Lower Body (0s)'))
            self.lined4.append(self.plot_eggxy.plot(xaa, yaa, pen=pen_black_dash, name='Individual Lower Body (0.2s)'))
            self.lined5.append(self.plot_eggxz.plot(xb, yb, pen=pen_black, name='Individual Lower Body (0s)'))
            self.lined5.append(self.plot_eggxz.plot(xbb, ybb, pen=pen_black_dash, name='Individual Lower Body (0.2s)'))
            self.lined6.append(self.plot_eggyz.plot(xc, yc, pen=pen_black, name='Individual Lower Body (0s)'))
            self.lined6.append(self.plot_eggyz.plot(xcc, ycc, pen=pen_black_dash, name='Individual Lower Body (0.2s)'))
            
        elif restype == 'No Restraint' or restype == 'Convenience Restraint':
            xa, ya = eggXY(1.5 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'), 1.8 * cond * coef(ht, 'x'))
            xaa, yaa = eggXY(1.2 * cond * coef(ht, 'x'), 2.5 * cond * coef(ht, 'x'), 1.2 * cond * coef(ht, 'x'))
            xb, yb = eggXZ(1.5 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'), 1.2 * cond * coef(ht, 'z'), 3 * cond * coef(ht, 'z'))
            xbb, ybb = eggXZ(1.2 * cond * coef(ht, 'z'), 2.5 * cond * coef(ht, 'z'), 0.8 * cond * coef(ht, 'z'), 2.8 * cond * coef(ht, 'z'))
            xc, yc = eggYZ(1.8 * cond * coef(ht, 'z'), 1.2 * cond * coef(ht, 'z'), 3 * cond * coef(ht, 'z'))
            xcc, ycc = eggYZ(1.2 * cond * coef(ht, 'z'), 0.8 * cond * coef(ht, 'z'), 2.8 * cond * coef(ht, 'z'))
            
            self.lined4.append(self.plot_eggxy.plot(xa, ya, pen=pen_black, name='No/Conv Restraint (0s)'))
            self.lined4.append(self.plot_eggxy.plot(xaa, yaa, pen=pen_black_dash, name='No/Conv Restraint (0.2s)'))
            self.lined5.append(self.plot_eggxz.plot(xb, 1 + yb, pen=pen_black, name='No/Conv Restraint (0s)'))
            self.lined5.append(self.plot_eggxz.plot(xbb, 1 + ybb, pen=pen_black_dash, name='No/Conv Restraint (0.2s)'))
            self.lined6.append(self.plot_eggyz.plot(xc, 1 + yc, pen=pen_black, name='No/Conv Restraint (0s)'))
            self.lined6.append(self.plot_eggyz.plot(xcc, 1 + ycc, pen=pen_black_dash, name='No/Conv Restraint (0.2s)'))


class AccZonePlotWidget(BasePlotWidget):
    """Acceleration Zone plot (replaces AccZonePlot)."""
    
    def __init__(self, parent=None):
        self.data_items = []
        self.zone_info_text = None
        super().__init__(parent)
        
    def setup_ui(self):
        """Setup UI with main plot and info area below."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Main graphics layout
        self.graphics_layout = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics_layout, stretch=5)
        
        # Info text area below
        self.info_widget = QtWidgets.QWidget()
        info_layout = QtWidgets.QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(10, 5, 10, 5)
        self.zone_info_label = QtWidgets.QLabel("No zone analysis data available.")
        self.zone_info_label.setWordWrap(True)
        self.zone_info_label.setAlignment(QtCore.Qt.AlignCenter)
        self.zone_info_label.setStyleSheet("""
            QLabel {
                background-color: wheat;
                border: 1px solid #8B7355;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
        """)
        info_layout.addWidget(self.zone_info_label)
        layout.addWidget(self.info_widget, stretch=1)
        
        self.initplotxyz()
        
    def initplotxyz(self):
        """Initialize acceleration zone plot."""
        self.graphics_layout.clear()
        self.data_items = []
        self.annotations = []
        
        self.plot_zone = self.graphics_layout.addPlot(title="Acceleration Zone Analysis")
        self.plot_zone.showGrid(x=True, y=True, alpha=0.3)
        self.plot_zone.setMenuEnabled(False)
        
        self.plot_zone.setLabel('left', 'Up <=> Down (Z-acceleration)')
        self.plot_zone.setLabel('bottom', 'Front <=> Back (X-acceleration)')
        self.plot_zone.setXRange(-6, 6)
        self.plot_zone.setYRange(-4, 4)
        self.plot_zone.setAspectLocked(True)
        
        # Plot zone boundaries
        self._plot_zone_boundaries()
        
        # Add zone labels
        self.plot_zone.addItem(pg.TextItem('Zone 1', anchor=(0.5, 0.5), color='k'))
        
    def _plot_zone_boundaries(self):
        """Plot acceleration zone boundaries with proper fills."""
        # Zone 5 (red) - base fill for y <= -0.2
        zone5_base = pg.PlotDataItem([-6, 6, 6, -6], [-4, -4, -0.2, -0.2])
        zone5_top = pg.PlotDataItem([-6, 6], [-0.2, -0.2])
        fill5 = pg.FillBetweenItem(zone5_top, zone5_base, brush=pg.mkBrush(255, 0, 0, 180))
        self.plot_zone.addItem(fill5)
        
        # Sloping line from (-0.7, 0.2) to (0, 0) to (0.7, -0.2)
        # Line equation: y = (-2/7)x or x = -3.5y
        
        # Zone 5 in -0.2 < y <= 0 region (left of line, x < 0.7)
        y_vals = np.linspace(-0.2, 0, 20)
        x_line = -3.5 * y_vals
        x_zone5_left = np.concatenate([[-6, -6, 0], x_line[1:], [-6]])
        y_zone5_left = np.concatenate([[-0.2, 0, 0], y_vals[1:], [-0.2]])
        zone5_item = pg.PlotDataItem(x_zone5_left, y_zone5_left)
        fill5_left = pg.FillBetweenItem(
            pg.PlotDataItem(x_zone5_left, y_zone5_left),
            pg.PlotDataItem(x_zone5_left, [-0.2]*len(x_zone5_left)),
            brush=pg.mkBrush(255, 0, 0, 180)
        )
        # Add as polygon
        poly5 = pg.PlotDataItem(x_zone5_left, y_zone5_left, fillLevel=-0.2, 
                                 fillBrush=pg.mkBrush(255, 0, 0, 180))
        self.plot_zone.addItem(poly5)
        
        # Zone 4 (light pink) in -0.2 < y <= 0 (right of sloping line)
        x_zone4 = np.concatenate([[0.7, 6, 6, 0.2], x_line[::-1]])
        y_zone4 = np.concatenate([[-0.2, -0.2, 0, 0], y_vals[::-1]])
        poly4 = pg.PlotDataItem(x_zone4, y_zone4, fillLevel=-0.2,
                                 fillBrush=pg.mkBrush(255, 182, 193, 180))
        self.plot_zone.addItem(poly4)
        
        # Zone 4 in 0 < y <= 0.2 (left of line AND x < -0.2)
        y_vals2 = np.linspace(0, 0.2, 20)
        x_line2 = -3.5 * y_vals2
        x_zone4_left = np.concatenate([[-6, -6, -0.7], x_line2, [-0.2]])
        y_zone4_left = np.concatenate([[0, 0.2, 0.2], y_vals2, [0]])
        poly4_left = pg.PlotDataItem(x_zone4_left, y_zone4_left, fillLevel=0,
                                      fillBrush=pg.mkBrush(255, 182, 193, 180))
        self.plot_zone.addItem(poly4_left)
        
        # Zone 5 small triangle in 0 < y <= 0.2
        y_intersect = 0.2 / 3.5
        x_zone5_tri = [0, -0.2, -0.2, 0]
        y_zone5_tri = [0, 0, y_intersect, 0]
        poly5_tri = pg.PlotDataItem(x_zone5_tri, y_zone5_tri, fillLevel=0,
                                     fillBrush=pg.mkBrush(255, 0, 0, 180))
        self.plot_zone.addItem(poly5_tri)
        
        # Zone 3 (orange) in 0 < y <= 0.2 (right of line)
        x_zone3 = np.concatenate([x_line2[::-1], [6, 6, 0]])
        y_zone3 = np.concatenate([y_vals2[::-1], [0.2, 0, 0]])
        poly3 = pg.PlotDataItem(x_zone3, y_zone3, fillLevel=0,
                                 fillBrush=pg.mkBrush(255, 165, 0, 180))
        self.plot_zone.addItem(poly3)
        
        # Zone 4: x < -1.2, 0.2 < y <= 0.7
        poly4_2 = pg.PlotDataItem([-6, -1.2, -1.2, -6], [0.2, 0.2, 0.7, 0.7], 
                                   fillLevel=0.2, fillBrush=pg.mkBrush(255, 182, 193, 180))
        self.plot_zone.addItem(poly4_2)
        
        # Zone 3: -1.2 <= x < -0.7, 0.2 < y <= 0.7
        poly3_2 = pg.PlotDataItem([-1.2, -0.7, -0.7, -1.2], [0.2, 0.2, 0.7, 0.7],
                                   fillLevel=0.2, fillBrush=pg.mkBrush(255, 165, 0, 180))
        self.plot_zone.addItem(poly3_2)
        
        # Zone 2 (yellow): -0.7 <= x < 0.2, 0.2 < y <= 0.7
        poly2 = pg.PlotDataItem([-0.7, 0.2, 0.2, -0.7], [0.2, 0.2, 0.7, 0.7],
                                 fillLevel=0.2, fillBrush=pg.mkBrush(255, 255, 0, 180))
        self.plot_zone.addItem(poly2)
        
        # Zone 1 (green): x >= 0.2, 0.2 < y <= 0.7
        poly1 = pg.PlotDataItem([0.2, 6, 6, 0.2], [0.2, 0.2, 0.7, 0.7],
                                 fillLevel=0.2, fillBrush=pg.mkBrush(173, 255, 47, 180))
        self.plot_zone.addItem(poly1)
        
        # Zone 4: x < -1.2, y > 0.7
        poly4_3 = pg.PlotDataItem([-6, -1.2, -1.2, -6], [0.7, 0.7, 4, 4],
                                   fillLevel=0.7, fillBrush=pg.mkBrush(255, 182, 193, 180))
        self.plot_zone.addItem(poly4_3)
        
        # Zone 3: -1.2 <= x < -0.7, y > 0.7
        poly3_3 = pg.PlotDataItem([-1.2, -0.7, -0.7, -1.2], [0.7, 0.7, 4, 4],
                                   fillLevel=0.7, fillBrush=pg.mkBrush(255, 165, 0, 180))
        self.plot_zone.addItem(poly3_3)
        
        # Zone 2: -0.7 <= x < -0.2, y > 0.7
        poly2_2 = pg.PlotDataItem([-0.7, -0.2, -0.2, -0.7], [0.7, 0.7, 4, 4],
                                   fillLevel=0.7, fillBrush=pg.mkBrush(255, 255, 0, 180))
        self.plot_zone.addItem(poly2_2)
        
        # Zone 1: x >= -0.2, y > 0.7
        poly1_2 = pg.PlotDataItem([-0.2, 6, 6, -0.2], [0.7, 0.7, 4, 4],
                                   fillLevel=0.7, fillBrush=pg.mkBrush(173, 255, 47, 180))
        self.plot_zone.addItem(poly1_2)
        
        # Draw boundary lines
        pen_black = pg.mkPen(color='k', width=2)
        pen_black_thin = pg.mkPen(color='k', width=1, style=QtCore.Qt.PenStyle.DotLine)
        
        # Sloping lines
        self.plot_zone.plot([-0.7, 0], [0.2, 0], pen=pen_black)
        self.plot_zone.plot([0, 0.7], [0, -0.2], pen=pen_black)
        
        # Extended sloping lines (dashed)
        self.plot_zone.plot([-3.5*4, -0.7], [4, 0.2], pen=pen_black_thin)
        self.plot_zone.plot([0.7, -3.5*(-4)], [-0.2, -4], pen=pen_black_thin)
        
        # Vertical lines
        for x in [-1.2, -0.7, -0.2, 0.2, 0.7]:
            self.plot_zone.addLine(x=x, pen=pen_black_thin)
            
        # Horizontal lines
        for y in [0.7, 0.2, 0, -0.2]:
            self.plot_zone.addLine(y=y, pen=pen_black_thin)
            
        # Zone labels
        self.plot_zone.addItem(pg.TextItem('Zone 1', anchor=(0.5, 0.5), color='k', 
                                           fill=pg.mkBrush(173, 255, 47, 200)))
        t1 = pg.TextItem('Zone 1', anchor=(0.5, 0.5))
        t1.setPos(3, 3)
        self.plot_zone.addItem(t1)
        
        t2 = pg.TextItem('Zone 2', anchor=(0.5, 0.5))
        t2.setPos(-0.45, 3)
        self.plot_zone.addItem(t2)
        
        t3 = pg.TextItem('Zone 3', anchor=(0.5, 0.5))
        t3.setPos(-0.95, 3)
        self.plot_zone.addItem(t3)
        
        t4 = pg.TextItem('Zone 4', anchor=(0.5, 0.5))
        t4.setPos(-3.5, 3)
        self.plot_zone.addItem(t4)
        
        t5 = pg.TextItem('Zone 5', anchor=(0.5, 0.5))
        t5.setPos(0, -2)
        self.plot_zone.addItem(t5)
        
    def addplotxyz(self, data):
        """Add data to zone plot with analysis."""
        self.clear_annotations()
        
        # Remove previous data
        for item in self.data_items:
            self.plot_zone.removeItem(item)
        self.data_items = []
        
        # Plot data
        x_data = data.iloc[:, 1].values  # Front-back (X)
        z_data = data.iloc[:, 3].values  # Up-down (Z)
        time_data = data.iloc[:, 0].values
        
        pen_blue = pg.mkPen(color='b', width=1.5)
        line = self.plot_zone.plot(x_data, z_data, pen=pen_blue, symbol='o',
                                    symbolSize=3, symbolBrush='b')
        self.data_items.append(line)
        
        # Analyze zones
        self._analyze_zones(data, time_data, x_data, z_data)
        
    def _analyze_zones(self, data, time_data, x_data, z_data):
        """Analyze which zones the data falls into."""
        if len(time_data) >= 2:
            time_interval = time_data[1] - time_data[0]
        else:
            time_interval = get_time_interval(500)
            
        min_duration = 0.2
        min_points = int(min_duration / time_interval)
        
        # Determine zone for each point
        zone_list = []
        for x, z in zip(x_data, z_data):
            zone = self._get_zone(x, z)
            zone_list.append(zone)
            
        # Find consecutive zones
        zone_durations = {}
        i = 0
        n = len(zone_list)
        
        while i < n:
            current_zone = zone_list[i]
            start_idx = i
            
            while i < n and zone_list[i] == current_zone:
                i += 1
            end_idx = i
            
            num_points = end_idx - start_idx
            if num_points >= min_points:
                start_time = time_data[start_idx]
                end_time = time_data[end_idx - 1]
                duration = end_time - start_time
                
                if current_zone not in zone_durations:
                    zone_durations[current_zone] = []
                zone_durations[current_zone].append((start_time, end_time, duration))
                
        # Find most severe zone
        zone_severity = {"Zone 5": 5, "Zone 4": 4, "Zone 3": 3, "Zone 2": 2, "Zone 1": 1}
        qualifying_zones = []
        
        for zone, durations in zone_durations.items():
            if zone in zone_severity:
                qualifying_zones.append((zone_severity[zone], zone, durations))
                
        qualifying_zones.sort(key=lambda x: x[0], reverse=True)
        
        # Display info
        self._display_zone_info(qualifying_zones)
        
    def _get_zone(self, x, y):
        """Determine which zone a point falls into."""
        def is_left_of_line(x, y):
            line_x_at_y = -3.5 * y
            return x < line_x_at_y
            
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
            if is_left_of_line(x, y) and x < -0.2:
                return "Zone 4"
            elif is_left_of_line(x, y) and -0.2 <= x <= 0:
                return "Zone 5"
            else:
                return "Zone 3"
        elif y > -0.2:
            if is_left_of_line(x, y) and x < 0.7:
                return "Zone 5"
            elif not is_left_of_line(x, y) and x < 0.2:
                return "Zone 5"
            else:
                return "Zone 4"
        else:
            return "Zone 5"
            
    def _display_zone_info(self, qualifying_zones):
        """Display zone analysis results."""
        if not qualifying_zones:
            info_text = "No zone meets the 0.2s duration threshold."
        else:
            most_severe = qualifying_zones[0]
            zone_name = most_severe[1]
            durations = most_severe[2]
            
            info_lines = [f"Classified Zone: {zone_name}"]
            for start_time, end_time, duration in durations:
                info_lines.append(f"  {start_time:.3f}s to {end_time:.3f}s (duration: {duration:.3f}s)")
            info_text = "\n".join(info_lines)
            
        self.zone_info_label.setText(info_text)
        
    def removelines(self):
        """Remove data lines."""
        for item in self.data_items:
            self.plot_zone.removeItem(item)
        self.data_items = []
        self.zone_info_label.setText("No zone analysis data available.")


class ZReversalPlotWidget(BasePlotWidget):
    """Z-axis reversal analysis plot (replaces ZReversalPlot)."""
    
    def __init__(self, parent=None):
        self.linez = []
        self.markers = []
        super().__init__(parent)
        
    def setup_ui(self):
        super().setup_ui()
        self.initplotxyz()
        
    def initplotxyz(self):
        """Initialize Z reversal plot."""
        self.graphics_layout.clear()
        self.linez = []
        self.markers = []
        self.annotations = []
        
        self.plot_z = self.graphics_layout.addPlot(title="Z-Axis Acceleration Reversal Analysis")
        self.plot_z.showGrid(x=True, y=True, alpha=0.3)
        self.plot_z.setMenuEnabled(False)
        
        self.plot_z.setLabel('left', 'Z Acceleration', units='g')
        self.plot_z.setLabel('bottom', 'Time', units='s')
        
        # Add zero line
        self.plot_z.addLine(y=0, pen=pg.mkPen(color='k', width=1, style=QtCore.Qt.PenStyle.DashLine))
        
    def plot_z_data(self, time_data, z_data, reversals):
        """Plot Z-axis data with reversal markers."""
        self.clear_annotations()
        self.removelines()
        
        # Plot Z data
        pen_blue = pg.mkPen(color='b', width=1.5)
        line = self.plot_z.plot(time_data, z_data, pen=pen_blue, name='Z Acceleration')
        self.linez.append(line)
        
        # Plot reversal markers
        colors = ['red', 'orange', 'purple', 'cyan', 'magenta', 'brown']
        
        for i, reversal in enumerate(reversals):
            color = colors[i % len(colors)]
            
            # Add region highlight
            lr = pg.LinearRegionItem([reversal['window_start'], reversal['window_end']], 
                                     brush=pg.mkBrush(color), movable=False)
            self.plot_z.addItem(lr)
            self.markers.append(lr)
            
            # Add peak markers
            min_marker = pg.ScatterPlotItem([reversal['min_time']], [reversal['min_value']], 
                                            symbol='v', size=12, brush=color)
            max_marker = pg.ScatterPlotItem([reversal['max_time']], [reversal['max_value']], 
                                            symbol='^', size=12, brush=color)
            self.plot_z.addItem(min_marker)
            self.plot_z.addItem(max_marker)
            self.markers.extend([min_marker, max_marker])
            
    def removelines(self):
        """Remove all lines and markers."""
        for line in self.linez:
            line.clear()
        for marker in self.markers:
            self.plot_z.removeItem(marker)
        self.linez = []
        self.markers = []


class XYReversalPlotWidget(BasePlotWidget):
    """X/Y-axis reversal analysis plot (replaces XYReversalPlot)."""
    
    def __init__(self, parent=None):
        self.linex = []
        self.liney = []
        self.markers = []
        super().__init__(parent)
        
    def setup_ui(self):
        super().setup_ui()
        self.initplotxyz()
        
    def initplotxyz(self):
        """Initialize X/Y reversal plot."""
        self.graphics_layout.clear()
        self.linex = []
        self.liney = []
        self.markers = []
        self.annotations = []
        
        # Create linked plots
        self.plot_x = self.graphics_layout.addPlot(row=0, col=0, title="X Acceleration")
        self.plot_y = self.graphics_layout.addPlot(row=1, col=0, title="Y Acceleration")
        self.plot_y.setXLink(self.plot_x)
        
        for plot in [self.plot_x, self.plot_y]:
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.setMenuEnabled(False)
            plot.addLine(y=0, pen=pg.mkPen(color='k', width=1, style=QtCore.Qt.PenStyle.DashLine))
            
        self.plot_x.setLabel('left', 'X Accel', units='g')
        self.plot_y.setLabel('left', 'Y Accel', units='g')
        self.plot_y.setLabel('bottom', 'Time', units='s')
        
    def plot_xy_data(self, time_data, x_data, y_data, reversals):
        """Plot X/Y data with reversal markers."""
        self.clear_annotations()
        self.removelines()
        
        # Plot data
        pen_x = pg.mkPen(color='b', width=1.5)
        pen_y = pg.mkPen(color='g', width=1.5)
        
        line_x = self.plot_x.plot(time_data, x_data, pen=pen_x, name='X Acceleration')
        line_y = self.plot_y.plot(time_data, y_data, pen=pen_y, name='Y Acceleration')
        
        self.linex.append(line_x)
        self.liney.append(line_y)
        
        # Plot reversal markers
        colors = ['red', 'orange', 'purple', 'cyan', 'magenta', 'brown']
        
        x_reversals = reversals.get('x_reversals', [])
        y_reversals = reversals.get('y_reversals', [])
        
        for i, reversal in enumerate(x_reversals):
            color = colors[i % len(colors)]
            lr = pg.LinearRegionItem([reversal['window_start'], reversal['window_end']], 
                                     brush=pg.mkBrush(color), movable=False)
            self.plot_x.addItem(lr)
            self.markers.append(lr)
            
        for i, reversal in enumerate(y_reversals):
            color = colors[i % len(colors)]
            lr = pg.LinearRegionItem([reversal['window_start'], reversal['window_end']], 
                                     brush=pg.mkBrush(color), movable=False)
            self.plot_y.addItem(lr)
            self.markers.append(lr)
            
    def removelines(self):
        """Remove all lines and markers."""
        for line in self.linex + self.liney:
            line.clear()
        for marker in self.markers:
            if marker in self.plot_x.items:
                self.plot_x.removeItem(marker)
            if marker in self.plot_y.items:
                self.plot_y.removeItem(marker)
        self.linex = []
        self.liney = []
        self.markers = []


# Navigation toolbar replacement for PyQtGraph
class PyQtGraphNavigation(QtWidgets.QWidget):
    """Simple navigation toolbar for PyQtGraph plots."""
    
    def __init__(self, plot_widget, parent=None):
        super().__init__(parent)
        self.plot_widget = plot_widget
        
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Home button
        home_btn = QtWidgets.QPushButton("Home")
        home_btn.clicked.connect(self.reset_view)
        layout.addWidget(home_btn)
        
        # Pan button
        pan_btn = QtWidgets.QPushButton("Pan")
        pan_btn.setCheckable(True)
        pan_btn.clicked.connect(self.toggle_pan)
        layout.addWidget(pan_btn)
        
        # Zoom button
        zoom_btn = QtWidgets.QPushButton("Zoom")
        zoom_btn.setCheckable(True)
        zoom_btn.clicked.connect(self.toggle_zoom)
        layout.addWidget(zoom_btn)
        
        layout.addStretch()
        
    def reset_view(self):
        """Reset view to default."""
        if hasattr(self.plot_widget, 'graphics_layout'):
            for item in self.plot_widget.graphics_layout.items():
                if isinstance(item, pg.PlotItem):
                    item.enableAutoRange()
                    
    def toggle_pan(self, checked):
        """Toggle pan mode."""
        if hasattr(self.plot_widget, 'graphics_layout'):
            for item in self.plot_widget.graphics_layout.items():
                if isinstance(item, pg.PlotItem):
                    item.vb.setMouseMode(pg.ViewBox.PanMode if checked else pg.ViewBox.RectMode)
                    
    def toggle_zoom(self, checked):
        """Toggle zoom mode."""
        if hasattr(self.plot_widget, 'graphics_layout'):
            for item in self.plot_widget.graphics_layout.items():
                if isinstance(item, pg.PlotItem):
                    item.vb.setMouseMode(pg.ViewBox.RectMode if checked else pg.ViewBox.PanMode)