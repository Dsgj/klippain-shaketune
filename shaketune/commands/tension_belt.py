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
from ..helpers.resonance_test import vibrate_axis_with_impulses
from ..helpers.strobe_controller import StrobeController


def tension_belt(gcmd, klipper_config, st_config) -> None:
    tension = gcmd.get_float('T', default=9.0, minval=1.0)
    duration = gcmd.get_int('DURATION', default=30, minval=1)
    accel_per_hz = gcmd.get_float('ACCEL_PER_HZ', default=None)
    axis = gcmd.get('AXIS', default='x').lower()
    feedrate_travel = gcmd.get_float('TRAVEL_SPEED', default=120.0, minval=20.0)
    z_height = gcmd.get_float('Z_HEIGHT', default=None, minval=1.0)
    # TODO: Remove this TEST_FREQ parameter when everything is working fine
    test_freq = gcmd.get_float('TEST_FREQ', default=None, minval=1.0, maxval=500.0)

    if accel_per_hz == '':
        accel_per_hz = None

    axis_config = next((item for item in AXIS_CONFIG if item['axis'] == axis), None)
    if axis_config is None:
        raise gcmd.error('AXIS selection invalid. Should be either x, y, a or b!')

    # Calculate target frequency from tension using the string formula: f₀ = √(T/(4μL²))
    # Or use TEST_FREQ if provided for strobe validation
    mu = st_config.belt_linear_mass
    vibrating_length = st_config.belt_vibrating_length
    calculated_freq = math.sqrt(tension / (4 * mu * vibrating_length * vibrating_length))
    target_freq = test_freq if test_freq is not None else calculated_freq

    # Get impulse parameters from configuration
    impulse_displacement = st_config.tension_impulse_displacement
    impulse_acceleration = st_config.tension_impulse_acceleration
    impulse_interval = st_config.tension_impulse_interval
    impulse_strategy = st_config.tension_impulse_strategy
    strobe_config_section = st_config.tension_strobe_section
    strobe_duty_cycle = st_config.tension_strobe_duty_cycle

    ConsoleOutput.print('Belt tension tool starting...')
    ConsoleOutput.print(f'Belt parameters: μ={mu:.6f} kg/m, L={vibrating_length:.3f} m')
    if test_freq is not None:
        ConsoleOutput.print(f'TEST MODE: Using test frequency of {target_freq:.1f} Hz for strobe validation')
        ConsoleOutput.print(f'(Calculated frequency for {tension:.1f} N tension would be {calculated_freq:.1f} Hz)')
    else:
        ConsoleOutput.print(
            f'Target tension: {tension:.1f} N -> This corresponds to a target belt resonant frequency of {target_freq:.1f} Hz'
        )
    ConsoleOutput.print(
        f'Impulse excitation: {impulse_displacement:.1f}mm displacement, {impulse_acceleration:.0f}mm/s² acceleration'
    )
    ConsoleOutput.print(f'Impulse strategy: {impulse_strategy}, interval: {impulse_interval:.1f}s')
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

    # Initialize the strobe controller
    strobe_controller = None
    if strobe_config_section:
        try:
            strobe_controller = StrobeController(printer, strobe_config_section)
            strobe_controller.start_strobe(target_freq, strobe_duty_cycle)
            ConsoleOutput.print(
                f'Started light strobe at {target_freq:.1f} Hz with {strobe_duty_cycle*100:.1f}% duty cycle (strobed lights: {strobe_config_section})'
            )
        except Exception as e:
            ConsoleOutput.print(f'Failed to initialize LED strobing: {e}')
            ConsoleOutput.print(f'You must use an external stroboscope set at {target_freq:.1f} Hz')
            strobe_controller = None
    else:
        ConsoleOutput.print('No strobe_section configured - integrated LED strobing is disabled')
        ConsoleOutput.print(f'You must use an external stroboscope set at {target_freq:.1f} Hz')

    ConsoleOutput.print('Starting belt excitation...')
    toolhead.dwell(0.5)

    # Start the impulse excitation
    vibrate_axis_with_impulses(
        toolhead,
        gcode,
        axis_config['direction'],
        impulse_displacement,
        impulse_acceleration,
        impulse_interval,
        duration,
        impulse_strategy,
        klipper_config,
    )

    toolhead.dwell(0.5)

    # Stop the strobe controller if it was started
    if strobe_controller:
        strobe_controller.stop_strobe()

    # Re-enable the input shaper if it was active
    if input_shaper is not None:
        input_shaper.enable_shaping()
