"""
Constants module for ACCEL application
Contains configurable parameters and default values
"""

# Default sampling frequency (Hz) - used as fallback when detection fails
DEFAULT_SAMPLING_FREQUENCY = 500

# Default cutoff frequency for filtering (Hz)
DEFAULT_CUTOFF_FREQUENCY = 5

# Maximum allowed cutoff frequency (Hz)
MAX_CUTOFF_FREQUENCY = 249

# Time interval for annotation calculations (seconds)
# This will be calculated dynamically as 1/sampling_frequency
def get_time_interval(sampling_frequency):
    """Calculate time interval from sampling frequency"""
    return 1.0 / sampling_frequency if sampling_frequency > 0 else 0.002