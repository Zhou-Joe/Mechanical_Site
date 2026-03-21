"""
Acceleration data processing module
Handles loading, parsing, and processing of acceleration data files
"""

import pandas as pd
import re
import numpy as np
import os
from .sci_calculation import butter_lowpass_filter, coordTransform
from .constants import DEFAULT_SAMPLING_FREQUENCY, DEFAULT_CUTOFF_FREQUENCY, get_time_interval


class AccData:
    """Main class for handling acceleration data"""
    
    def __init__(self, rawdata, path=None, is_raw=False, cutoff=5, *args, **kwargs):
        if is_raw:
            self.cutoff = cutoff
            self.rawdata = rawdata
            self.data = rawdata
            self.filename = path
            self.filtered_data = pd.DataFrame()
            self.std_data = pd.DataFrame()
            self.fs = DEFAULT_SAMPLING_FREQUENCY
            # Initialize missing attributes for raw data
            self.col_idx = 0
            self.start_idx = 0
            self.column_row_content = ''
            self.columns = list(rawdata.columns) if hasattr(rawdata, 'columns') else ['Time', 'X', 'Y', 'Z']
            self.pitch_angle = 0
            self.yaw_angle = 0
            self.roll_angle = 0
            self.seatback_angle = 0
            self.zero_x = 0
            self.zero_y = 0
            self.zero_z = 1
            self.offset_x = 0
            self.offset_y = 0
            self.offset_z = 0
            self.x_avg = 0
            self.y_avg = 0
            self.z_avg = 1
        else:
            self.cutoff = cutoff
            self.rawdata = pd.read_csv(rawdata, header=None, index_col=False, sep='\t', low_memory=False)
            self.filename = os.path.basename(rawdata)
            self.filtered_data = pd.DataFrame()
            self.std_data = pd.DataFrame()
            self.fs = DEFAULT_SAMPLING_FREQUENCY
            self.get_core_idx()
            self.init_angle()
            self.get_angle()
            self.get_colID()
            self.parsie_cols()
            self.calculate_sampling_frequency()
            self.get_offset()
            self.filter_data(cutoff=cutoff)
    
    def init_angle(self):
        """Initialize angle values"""
        self.pitch_angle = 0
        self.yaw_angle = 0
        self.roll_angle = 0
        self.seatback_angle = 0

    def get_angle(self):
        """Extract angle information from raw data"""
        for i in range(10):
            try:
                if "Initial Pitch Angle: " in str(self.rawdata.iloc[i, 0]):
                    self.pitch_angle = int(re.sub(r"Initial Pitch Angle: ", '', self.rawdata.iloc[i, 0]))
                elif "Seatback Angle: " in str(self.rawdata.iloc[i, 0]):
                    self.seatback_angle = int(re.sub(r"Seatback Angle: ", '', self.rawdata.iloc[i, 0]))
                elif "Initial Roll Angle: " in str(self.rawdata.iloc[i, 0]):
                    self.roll_angle = int(re.sub(r"Initial Roll Angle: ", '', self.rawdata.iloc[i, 0]))
                elif "Initial Yaw Angle: " in str(self.rawdata.iloc[i, 0]):
                    self.yaw_angle = int(re.sub(r"Initial Yaw Angle: ", '', self.rawdata.iloc[i, 0]))
            except Exception as e:
                print(e)

    def get_offset(self):
        """Calculate zero offset based on orientation angles"""
        [self.zero_x, self.zero_y, self.zero_z] = coordTransform(
            self.pitch_angle, self.seatback_angle, self.roll_angle, self.yaw_angle
        )

        # Calculate zero offset based on first 1 second of data
        num_points = min(self.fs, len(self.data))
        
        if num_points > 0:
            self.x_avg = self.data.iloc[:num_points, 1].mean()
            self.y_avg = self.data.iloc[:num_points, 2].mean()
            self.z_avg = self.data.iloc[:num_points, 3].mean()
        else:
            self.x_avg = self.data.iloc[:, 1].mean()
            self.y_avg = self.data.iloc[:, 2].mean()
            self.z_avg = self.data.iloc[:, 3].mean()
        
        # Get deviate value
        self.offset_x = self.x_avg - self.zero_x
        self.offset_y = self.y_avg - self.zero_y
        self.offset_z = self.z_avg - self.zero_z

    def get_core_idx(self):
        """Find core data indices in raw file"""
        for i in range(20):
            try:
                if "SARCcolumnIDs" in str(self.rawdata.iloc[i, 0]):
                    self.col_idx = i
            except Exception as e:
                print(e)

            try:
                m1 = round(float(self.rawdata.iloc[i, 0]), 3)
                m2 = round(float(self.rawdata.iloc[i + 1, 0]), 3)
            except:
                m1 = 0
                m2 = 0
            if m1 == 0 and m2 > m1:
                self.start_idx = i

        try:
            re.sub(r'time', 'Time', self.rawdata.iloc[self.col_idx, 0])
        except Exception as e:
            print(e)

    def get_colID(self, column_str=None):
        """Get column identifiers"""
        try:
            self.column_row_content = re.sub(r'SARCcolumnIDs: ', "", self.rawdata.iloc[self.col_idx, 0])
            self.columns = re.sub(r'SARCcolumnIDs: ', '', self.rawdata.iloc[self.col_idx, 0]).split(' ')
        except Exception as e:
            print(e)

    def set_colID(self, column_str):
        """Set column identifiers"""
        self.column_row_content = column_str
        self.columns = self.column_row_content.split(' ')
        self.data.columns = self.columns

    def parsie_cols(self):
        """Parse columns into data DataFrame"""
        self.data = pd.DataFrame()
        for i in range(len(self.columns)):
            self.data[self.columns[i]] = self.rawdata.iloc[self.start_idx:, i]
        self.data.reset_index(drop=True, inplace=True)
        if "Time" in self.columns:
            self.data['Time'] = pd.to_numeric(self.data['Time'], errors='ignore').round(decimals=4)
        self.data = self.data.round(decimals=4)
    
    def calculate_sampling_frequency(self):
        """Calculate actual sampling frequency from time data"""
        try:
            if len(self.data) > 1:
                time_interval = self.data.iloc[1, 0] - self.data.iloc[0, 0]
                if time_interval > 0:
                    self.fs = int(round(1.0 / time_interval))
                else:
                    self.fs = DEFAULT_SAMPLING_FREQUENCY
            else:
                self.fs = DEFAULT_SAMPLING_FREQUENCY
        except Exception as e:
            self.fs = DEFAULT_SAMPLING_FREQUENCY

    def filter_data(self, cutoff=500):
        """Apply lowpass filter to data"""
        self.filtered_data = pd.DataFrame()
        self.std_data = pd.DataFrame()
        self.filtered_data['Time'] = self.data['Time']
        self.std_data['Time'] = self.data['Time']
        cutoff = cutoff
        i = 0
        zero_list = [self.x_avg, self.y_avg, self.z_avg]
        offset_list = [self.offset_x, self.offset_y, self.offset_z]
        for cols in list(self.data.columns):
            if not "Time" in cols:
                self.std_data[cols] = butter_lowpass_filter(
                    self.data[cols], cutoff, fs=self.fs, order=4, zeropoint=zero_list[i]
                ) - offset_list[i]
                self.filtered_data[cols] = butter_lowpass_filter(
                    self.data[cols], cutoff, fs=self.fs, order=4, zeropoint=zero_list[i]
                )
                i += 1
        self.filtered_data = self.filtered_data.round(decimals=4)
        self.std_data = self.std_data.round(decimals=4)
    
    def set_angle(self, pitch_angle, seatback_angle, roll_angle, yaw_angle):
        """Set orientation angles"""
        self.pitch_angle = pitch_angle
        self.seatback_angle = seatback_angle
        self.roll_angle = roll_angle
        self.yaw_angle = yaw_angle
        self.get_offset()

    def reformat(self, overwrite=False, setting_angle=False, pitch_angle=0, seatback_angle=0, 
                 roll_angle=0, yaw_angle=0, cutoff=5):
        """Reformat data with new angle settings"""
        if setting_angle:
            self.set_angle(pitch_angle, seatback_angle, roll_angle, yaw_angle)
        self.new_data = pd.DataFrame()
        for i in self.columns:
            self.new_data[i] = self.data[i]
        self.new_data.loc[-6, 'Time'] = 'Initial Pitch Angle: {}'.format(self.pitch_angle)
        self.new_data.loc[-5, 'Time'] = 'Seatback Angle: {}'.format(self.seatback_angle)
        self.new_data.loc[-4, 'Time'] = 'Initial Roll Angle: {}'.format(self.roll_angle)
        self.new_data.loc[-3, 'Time'] = 'Initial Yaw Angle: {}'.format(self.yaw_angle)
        self.new_data.loc[-2, 'Time'] = 'SARCcolumnIDs: {}'.format(self.column_row_content)
        self.new_data.loc[-1, 'Time'] = np.nan
        self.new_data.sort_index(inplace=True)
        self.new_data.reset_index(drop=True, inplace=True)
        if overwrite == True:
            self.rawdata = self.new_data
            self.get_core_idx()
            self.get_colID()
            self.parsie_cols()
            self.get_offset()
            self.filter_data(cutoff=cutoff)

    def edit_data(self, method, value_array, cutoff):
        """Edit data by adding or multiplying values"""
        self.raw_data = pd.DataFrame()
        for i in self.columns:
            self.raw_data[i] = self.data[i]
        self.raw_data.loc[-6, 'Time'] = 'Initial Pitch Angle: {}'.format(self.pitch_angle)
        self.raw_data.loc[-5, 'Time'] = 'Seatback Angle: {}'.format(self.seatback_angle)
        self.raw_data.loc[-4, 'Time'] = 'Initial Roll Angle: {}'.format(self.roll_angle)
        self.raw_data.loc[-3, 'Time'] = 'Initial Yaw Angle: {}'.format(self.yaw_angle)
        self.raw_data.loc[-2, 'Time'] = 'SARCcolumnIDs: {}'.format(self.column_row_content)
        self.raw_data.loc[-1, 'Time'] = np.nan
        self.raw_data.sort_index(inplace=True)
        self.raw_data.reset_index(drop=True, inplace=True)
        self.rawdata = self.raw_data
        if method == 'add':
            for i in range(3):
                self.rawdata.iloc[:, i+1] = self.rawdata.iloc[:, i+1].values + value_array[i]
        if method == 'multiply':
            for i in range(3):
                self.rawdata.iloc[:, i + 1] = self.rawdata.iloc[:, i + 1].values * value_array[i]

        self.rawdata = self.rawdata.round(decimals=4)
        self.get_core_idx()
        self.get_colID()
        self.parsie_cols()
        self.get_offset()
        self.filter_data(cutoff=cutoff)

    def truncate_data(self, starttime, endtime, cutoff):
        """Truncate data to specified time range"""
        start_row = int(starttime) * self.fs
        end_row = int(endtime) * self.fs
        self.new_data = pd.DataFrame()
        for i in self.columns:
            self.new_data[i] = self.data[i][start_row:end_row]
        self.new_data['Time'] = self.new_data['Time'].values - starttime
        self.new_data.loc[-6, 'Time'] = 'Initial Pitch Angle: {}'.format(self.pitch_angle)
        self.new_data.loc[-5, 'Time'] = 'Seatback Angle: {}'.format(self.seatback_angle)
        self.new_data.loc[-4, 'Time'] = 'Initial Roll Angle: {}'.format(self.roll_angle)
        self.new_data.loc[-3, 'Time'] = 'Initial Yaw Angle: {}'.format(self.yaw_angle)
        self.new_data.loc[-2, 'Time'] = 'SARCcolumnIDs: {}'.format(self.column_row_content)
        self.new_data.loc[-1, 'Time'] = np.nan
        self.new_data.sort_index(inplace=True)
        self.new_data.reset_index(drop=True, inplace=True)
        self.rawdata = self.new_data
        self.get_core_idx()
        self.get_colID()
        self.parsie_cols()
        self.get_offset()
        self.filtered_data = pd.DataFrame()
        self.std_data = pd.DataFrame()
        self.filter_data(cutoff=cutoff)
    
    def reset_data(self):
        """Reset data to original parsed state"""
        self.parsie_cols()
    
    def get_data_stats(self, data):
        """Get statistical information about data"""
        minmax = [
            [data.iloc[:, 1].idxmax() / self.fs, data.iloc[:, 1].idxmin() / self.fs, 
             data.iloc[:, 1].max(), data.iloc[:, 1].min(), self.zero_x],
            [data.iloc[:, 2].idxmax() / self.fs, data.iloc[:, 2].idxmin() / self.fs, 
             data.iloc[:, 2].max(), data.iloc[:, 2].min(), self.zero_y],
            [data.iloc[:, 3].idxmax() / self.fs, data.iloc[:, 3].idxmin() / self.fs, 
             data.iloc[:, 3].max(), data.iloc[:, 3].min(), self.zero_z]
        ]
        return pd.DataFrame(minmax, index=['X', 'Y', 'Z'], 
                           columns=['t (Max)', 't (Min)', 'Max', 'Min', 'Zero Pos'])

    def get_angle_info(self):
        """Get angle information as string"""
        return "{}\nPitch: {}°  Seatback: {}°  Roll: {}°  Yaw: {}°".format(
            self.filename, self.pitch_angle, self.seatback_angle, 
            self.roll_angle, self.yaw_angle
        )

    def export_to_file(self, path):
        """Export data to file"""
        try:
            self.reformat(overwrite=True, setting_angle=False)
            self.rawdata.to_csv(path, sep='\t', header=False, index=False)
        except:
            pass

    def export_filter(self, path, plottype):
        """Export filtered data to file"""
        try:
            if plottype == 'Standard':
                self.std_data.to_csv(path, sep='\t', header=False, index=False)
            elif plottype == 'Filter':
                self.filtered_data.to_csv(path, sep='\t', header=False, index=False)
        except:
            pass
    
    def to_dict(self, plottype='Standard'):
        """Convert data to dictionary for JSON serialization"""
        if plottype == 'Standard':
            data = self.std_data
        elif plottype == 'Filter':
            data = self.filtered_data
        else:
            data = self.data
        
        return {
            'time': data.iloc[:, 0].values.tolist(),
            'x': data.iloc[:, 1].values.tolist(),
            'y': data.iloc[:, 2].values.tolist(),
            'z': data.iloc[:, 3].values.tolist(),
            'filename': self.filename,
            'pitch_angle': self.pitch_angle,
            'seatback_angle': self.seatback_angle,
            'roll_angle': self.roll_angle,
            'yaw_angle': self.yaw_angle,
            'fs': self.fs
        }
    
    def get_stats_dict(self, plottype='Standard'):
        """Get statistics as dictionary"""
        if plottype == 'Standard':
            data = self.std_data
        elif plottype == 'Filter':
            data = self.filtered_data
        else:
            data = self.data
        
        # Calculate duration and points
        duration = 0
        points = len(data)
        if points > 0 and self.fs > 0:
            duration = points / self.fs
        
        return {
            'filename': self.filename,
            'pitch_angle': self.pitch_angle,
            'seatback_angle': self.seatback_angle,
            'roll_angle': self.roll_angle,
            'yaw_angle': self.yaw_angle,
            'fs': self.fs,
            'duration': duration,
            'points': points,
            'x': {
                'max_time': float(data.iloc[:, 1].idxmax() / self.fs) if len(data) > 0 else 0,
                'min_time': float(data.iloc[:, 1].idxmin() / self.fs) if len(data) > 0 else 0,
                'max': float(data.iloc[:, 1].max()) if len(data) > 0 else 0,
                'min': float(data.iloc[:, 1].min()) if len(data) > 0 else 0,
                'zero_pos': float(self.zero_x)
            },
            'y': {
                'max_time': float(data.iloc[:, 2].idxmax() / self.fs) if len(data) > 0 else 0,
                'min_time': float(data.iloc[:, 2].idxmin() / self.fs) if len(data) > 0 else 0,
                'max': float(data.iloc[:, 2].max()) if len(data) > 0 else 0,
                'min': float(data.iloc[:, 2].min()) if len(data) > 0 else 0,
                'zero_pos': float(self.zero_y)
            },
            'z': {
                'max_time': float(data.iloc[:, 3].idxmax() / self.fs) if len(data) > 0 else 0,
                'min_time': float(data.iloc[:, 3].idxmin() / self.fs) if len(data) > 0 else 0,
                'max': float(data.iloc[:, 3].max()) if len(data) > 0 else 0,
                'min': float(data.iloc[:, 3].min()) if len(data) > 0 else 0,
                'zero_pos': float(self.zero_z)
            }
        }


class RawData:
    """Class for handling raw acceleration data files"""
    
    def __init__(self, path, *args, **kwargs):
        try:
            self.filename = path
            self.rawdata = pd.read_csv(path, index_col=False, sep='\t')
            if self.rawdata.shape[1] > 5:
                self.rawdata.dropna(inplace=True, axis=1)
                self.shape = self.rawdata.shape
            else:
                self.rawdata = pd.read_csv(path, index_col=False, sep=',', skiprows=23, header=None).iloc[:, 1:]
                self.rawdata.dropna(inplace=True, axis=1)
                self.shape = self.rawdata.shape
            self.init_data()
        except Exception as e:
            print(e)
    
    def init_data(self):
        """Initialize GB and ASTM data from raw file"""
        ASTM_cols_str = "Time 13inch_accel-x 13inch_accel-y 13inch_accel-z"
        GB_cols_str = "Time 60cm_accel-x 60cm_accel-y 60cm_accel-z"
        ASTM_cols = ASTM_cols_str.split(' ')
        GB_cols = GB_cols_str.split(' ')
        time_interval = get_time_interval(DEFAULT_SAMPLING_FREQUENCY)
        col_time = pd.DataFrame(
            np.arange(0, self.shape[0] * time_interval, time_interval), 
            columns=['Time']
        )
        ASTM_data = pd.DataFrame()
        ASTM_data['Time'] = col_time['Time']
        GB_data = pd.DataFrame()
        GB_data['Time'] = col_time['Time']
        for i in range(3):
            GB_data[GB_cols[i + 1]] = self.rawdata.iloc[:, i]
            ASTM_data[ASTM_cols[i + 1]] = self.rawdata.iloc[:, i + 3]
        self.GB_data = AccData(GB_data, is_raw=True, path="(GB)" + os.path.basename(self.filename))
        self.GB_data.set_colID(GB_cols_str)
        self.ASTM_data = AccData(ASTM_data, is_raw=True, path="(ASTM)" + os.path.basename(self.filename))
        self.ASTM_data.set_colID(ASTM_cols_str)
    
    def export_data(self):
        """Export GB and ASTM data"""
        return self.GB_data, self.ASTM_data


class StingData:
    """Class for handling Sting data files (obsolete)"""
    
    def __init__(self, path, *args, **kwargs):
        self.filename = path
        try:
            self.rawdata = pd.read_csv(path, index_col=False)
            self.rawdata.dropna(inplace=True, axis=1)
            self.shape = self.rawdata.shape
            self.init_data()
        except:
            self.rawdata = pd.read_csv(path, index_col=False, header=None, skiprows=np.arange(0, 8))
            self.title = pd.read_csv(path, index_col=False, header=None, skiprows=np.arange(0, 2)).iloc[0, :]
            self.rawdata.dropna(inplace=True, axis=1)
            self.shape = self.rawdata.shape
            self.init_data2()

    def init_data(self):
        """Initialize single ASTM data"""
        ASTM_cols_str = "Time 13inch_accel-x 13inch_accel-y 13inch_accel-z"
        ASTM_cols = ASTM_cols_str.split(' ')
        time_interval = get_time_interval(DEFAULT_SAMPLING_FREQUENCY)
        col_time = pd.DataFrame(
            np.arange(0, self.shape[0] * time_interval, time_interval), 
            columns=['Time']
        )
        ASTM_data = pd.DataFrame()
        ASTM_data['Time'] = col_time['Time']
        for i in range(3):
            ASTM_data[ASTM_cols[i + 1]] = self.rawdata.iloc[:, i + 2]
        self.ASTM_data = AccData(ASTM_data, is_raw=True, path="(ASTM)" + os.path.basename(self.filename))
        self.ASTM_data.set_colID(ASTM_cols_str)
        self.datalist = [self.ASTM_data]

    def init_data2(self):
        """Initialize multiple ASTM data sets"""
        ASTM_cols_str = "Time 13inch_accel-x 13inch_accel-y 13inch_accel-z"
        ASTM_cols = ASTM_cols_str.split(' ')
        time_interval = get_time_interval(DEFAULT_SAMPLING_FREQUENCY)
        col_time = pd.DataFrame(
            np.arange(0, self.shape[0] * time_interval, time_interval), 
            columns=['Time']
        )
        ASTM_16g_data = pd.DataFrame()
        ASTM_16g_data['Time'] = col_time['Time']
        ASTM_10HZ_data = pd.DataFrame()
        ASTM_10HZ_data['Time'] = col_time['Time']
        ASTM_5HZ_data = pd.DataFrame()
        ASTM_5HZ_data['Time'] = col_time['Time']

        ASTM_16g_data[ASTM_cols[1]] = self.rawdata.iloc[:, 4]
        ASTM_16g_data[ASTM_cols[2]] = self.rawdata.iloc[:, 2]
        ASTM_16g_data[ASTM_cols[3]] = self.rawdata.iloc[:, 3]

        ASTM_10HZ_data[ASTM_cols[1]] = self.rawdata.iloc[:, 7]
        ASTM_10HZ_data[ASTM_cols[2]] = self.rawdata.iloc[:, 5]
        ASTM_10HZ_data[ASTM_cols[3]] = self.rawdata.iloc[:, 6]

        ASTM_5HZ_data[ASTM_cols[1]] = self.rawdata.iloc[:, 10]
        ASTM_5HZ_data[ASTM_cols[2]] = self.rawdata.iloc[:, 8]
        ASTM_5HZ_data[ASTM_cols[3]] = self.rawdata.iloc[:, 9]

        self.ASTM_16g_data = AccData(
            ASTM_16g_data, is_raw=True, 
            path="({})".format(self.title[2])[6:] + os.path.basename(self.filename)
        )
        self.ASTM_16g_data.set_colID(ASTM_cols_str)

        self.ASTM_10HZ_data = AccData(
            ASTM_10HZ_data, is_raw=True, 
            path="({})".format(self.title[5])[6:] + os.path.basename(self.filename)
        )
        self.ASTM_10HZ_data.set_colID(ASTM_cols_str)

        self.ASTM_5HZ_data = AccData(
            ASTM_5HZ_data, is_raw=True, 
            path="({})".format(self.title[8])[6:] + os.path.basename(self.filename)
        )
        self.ASTM_5HZ_data.set_colID(ASTM_cols_str)

        self.datalist = [self.ASTM_16g_data, self.ASTM_10HZ_data, self.ASTM_5HZ_data]

    def export_data(self):
        """Export data"""
        if len(self.datalist) == 1:
            return self.ASTM_data
        else:
            return self.ASTM_16g_data, self.ASTM_10HZ_data, self.ASTM_5HZ_data