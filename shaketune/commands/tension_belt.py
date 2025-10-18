# Shake&Tune: 3D printer analysis tools
#
# Copyright (C) 2025 Félix Boisselier <felix@fboisselier.fr> (Frix_x on Discord)
# Licensed under the GNU General Public License v3.0 (GPL-3.0)
#
# File: tension_belt.py
# Description: Provide a command to help tension belts by exciting them with chirp patterns
#              while strobing LEDs at the target frequency corresponding to the desired tension.

import math

from ..helpers.common_func import AXIS_CONFIG
from ..helpers.compat import KlipperCompatibility
from ..helpers.console_output import ConsoleOutput
from ..helpers.resonance_test import vibrate_axis_at_static_freq, vibrate_axis_with_impulses
from ..helpers.strobe_controller import StrobeController


def tension_belt(gcmd, klipper_config, st_config) -> None:
    tension = gcmd.get_float('T', default=9.0, minval=1.0)
    duration = gcmd.get_int('DURATION', default=30, minval=1)
    accel_per_hz = gcmd.get_float('ACCEL_PER_HZ', default=None)
    axis = gcmd.get('AXIS', default='x').lower()
    feedrate_travel = gcmd.get_float('TRAVEL_SPEED', default=120.0, minval=20.0)
    z_height = gcmd.get_float('Z_HEIGHT', default=None, minval=1.0)
    freq_override = gcmd.get_float('FREQ', default=None, minval=1.0, maxval=500.0)

    if accel_per_hz == '':
        accel_per_hz = None

    axis_config = next((item for item in AXIS_CONFIG if item['axis'] == axis), None)
    if axis_config is None:
        raise gcmd.error('AXIS selection invalid. Should be either x, y, a or b!')

    # Calculate target frequency from tension using the string formula: f₀ = √(T/(4μL²))
    mu = st_config.belt_linear_mass
    vibrating_length = st_config.belt_vibrating_length
    calculated_freq = math.sqrt(tension / (4 * mu * vibrating_length * vibrating_length))
    strobe_freq = calculated_freq

    # Determine excitation frequency if mode is resonance (impulse does not use it)
    excitation_mode = st_config.tension_excitation_mode
    if excitation_mode == 'resonance':
        if freq_override is not None:
            excitation_freq = freq_override
        else:
            excitation_freq = st_config.tension_resonance_frequency

    # Get parameters from configuration
    strobe_config_section = st_config.tension_strobe_section
    strobe_duty_cycle = st_config.tension_strobe_duty_cycle

    ConsoleOutput.print('Belt tension tool starting...')
    ConsoleOutput.print(f'Excitation mode: {excitation_mode}')
    ConsoleOutput.print(f'Belt parameters: μ={mu:.6f} kg/m, L={vibrating_length:.3f} m')
    ConsoleOutput.print('')

    # Display frequency information
    ConsoleOutput.print(f'Target tension: {tension:.1f} N -> Strobe frequency: {strobe_freq:.1f} Hz')
    if excitation_mode == 'resonance':
        ConsoleOutput.print(f'Excitation frequency: {excitation_freq:.1f} Hz')

    ConsoleOutput.print('')
    ConsoleOutput.print('Instructions:')
    ConsoleOutput.print('  Adjust belt tension while the test is running')
    ConsoleOutput.print('  When the belt appears frozen under the strobe light, the tension is correct')

    printer = klipper_config.get_printer()
    gcode = printer.lookup_object('gcode')
    toolhead = printer.lookup_object('toolhead')
    systime = printer.get_reactor().monotonic()

    # Get the default values for the acceleration per Hz and the test points
    compat = KlipperCompatibility(klipper_config)
    res_config = compat.get_res_tester_config()
    _, _, default_accel_per_hz, test_points = res_config

    if accel_per_hz is None:
        accel_per_hz = default_accel_per_hz

    # Move to the starting point
    if len(test_points) > 1:
        raise gcmd.error('Only one test point in the [resonance_tester] section is supported by Shake&Tune.')
    if test_points[0] == (-1, -1, -1):
        if z_height is None:
            raise gcmd.error(
                'Z_HEIGHT parameter is required if the test_point in [resonance_tester] section is set to -1,-1,-1'
            )
        # Use center of bed in case the test point in [resonance_tester] is set to -1,-1,-1
        # This is useful to get something automatic and is also used in the Klippain modular config
        kin_info = toolhead.kin.get_status(systime)
        mid_x = (kin_info['axis_minimum'].x + kin_info['axis_maximum'].x) / 2
        mid_y = (kin_info['axis_minimum'].y + kin_info['axis_maximum'].y) / 2
        point = (mid_x, mid_y, z_height)
    else:
        x, y, z = test_points[0]
        if z_height is not None:
            z = z_height
        point = (x, y, z)

    toolhead.manual_move(point, feedrate_travel)
    toolhead.dwell(0.5)

    # Deactivate input shaper if it is active to get raw movements
    input_shaper = printer.lookup_object('input_shaper', None)
    if input_shaper is not None:
        input_shaper.disable_shaping()
    else:
        input_shaper = None

    # Initialize the strobe controller (always uses strobe_freq = frequency calculated from tension)
    strobe_controller = None
    if strobe_config_section:
        try:
            strobe_controller = StrobeController(printer, strobe_config_section)
            strobe_controller.start_strobe(strobe_freq, strobe_duty_cycle)
        except Exception as e:
            ConsoleOutput.print(f'Failed to initialize lights strobing: {e}')
            ConsoleOutput.print(f'You must use an external stroboscope set at {strobe_freq:.1f} Hz')
            strobe_controller = None
    else:
        ConsoleOutput.print('No strobe_section configured - integrated lights strobing is disabled')
        ConsoleOutput.print(f'You must use an external stroboscope set at {strobe_freq:.1f} Hz')

    toolhead.dwell(0.5)

    if excitation_mode == 'resonance':
        # Use standard resonance test at the excitation frequency
        vibrate_axis_at_static_freq(
            toolhead,
            gcode,
            axis_config['direction'],
            excitation_freq,
            duration,
            accel_per_hz,
            klipper_config,
        )
    else:
        # Use impulse-based excitation (impulse or smooth_impulse)
        impulse_displacement = st_config.tension_impulse_displacement
        impulse_acceleration = st_config.tension_impulse_acceleration
        impulse_interval = st_config.tension_impulse_interval

        vibrate_axis_with_impulses(
            toolhead,
            gcode,
            axis_config['direction'],
            impulse_displacement,
            impulse_acceleration,
            impulse_interval,
            duration,
            excitation_mode,
            klipper_config,
        )

    toolhead.dwell(0.5)

    # Stop the strobe controller if it was started
    if strobe_controller:
        strobe_controller.stop_strobe()

    # Re-enable the input shaper if it was active
    if input_shaper is not None:
        input_shaper.enable_shaping()
