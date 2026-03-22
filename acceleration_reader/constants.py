"""
Constants module for Acceleration Reader application
Contains configurable parameters and default values
"""

# Default sampling frequency (Hz) - used as fallback when detection fails
DEFAULT_SAMPLING_FREQUENCY = 500

# Default cutoff frequency for filtering (Hz)
DEFAULT_CUTOFF_FREQUENCY = 5

# Maximum allowed cutoff frequency (Hz)
MAX_CUTOFF_FREQUENCY = 10

# Time interval for annotation calculations (seconds)
# This will be calculated dynamically as 1/sampling_frequency
def get_time_interval(sampling_frequency):
    """Calculate time interval from sampling frequency"""
    return 1.0 / sampling_frequency if sampling_frequency > 0 else 0.002


# Colors for plot lines
PLOT_COLORS = [
    '#FF0000', '#0000FF', '#ADD8E6', '#800080', '#FFFF00',
    '#00FF00', '#FF00FF', '#FFC0CB', '#808080', '#000000',
    '#FFA500', '#A52A2A', '#800000', '#008000', '#808000',
    '#00008B', '#7FFFD4', '#C0C0C0', '#00FFFF'
]

# ASTM restraint types
RESTRAINT_TYPES = [
    'None',
    'Individual Lower Body',
    'Upper Body',
    'Group Lower Body',
    'Convenience Restraint',
    'No Restraint'
]

# ASTM condition types
CONDITION_TYPES = [
    'Normal',
    'E-Stop',
    'Expected/Permitted Bumping'
]
