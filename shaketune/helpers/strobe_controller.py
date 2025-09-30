# Shake&Tune: 3D printer analysis tools
#
# Copyright (C) 2025 Félix Boisselier <felix@fboisselier.fr> (Frix_x on Discord)
# Licensed under the GNU General Public License v3.0 (GPL-3.0)
#
# File: strobe_controller.py
# Description: Provides LED strobing functionality for the belt tension tool by interfacing
#              with various Klipper objects (output_pin, neopixel, etc.) using a strategy pattern.

import logging
from typing import Dict, Optional, Protocol, Type

from .console_output import ConsoleOutput


class StrobeStrategy(Protocol):
    """Protocol defining the interface for different strobing strategies"""

    def __init__(self, printer_object, original_state: float) -> None: ...
    def start_strobe(self, frequency_hz: float, duty_cycle: float = 0.05) -> None: ...
    def stop_strobe(self) -> None: ...


class OutputPinStrobeStrategy:
    """Strategy for strobing output_pin Klipper objects using PWM cycle time"""

    def __init__(self, printer_object, original_state: float) -> None:
        self.output_pin = printer_object
        self.original_state = original_state
        self.original_cycle_time = None
        self.original_cycle_time_cmd = None
        self.is_strobing = False
        self.mcu_pin = self.output_pin.mcu_pin
        self.mcu = self.mcu_pin.get_mcu()

        # Validate that this is a PWM pin for strobing
        if not hasattr(self.output_pin, 'is_pwm') or not self.output_pin.is_pwm:
            raise ValueError('Output pin must be configured with PWM for LED strobing')

        # Check if hardware PWM is being used
        if getattr(self.mcu_pin, '_hardware_pwm', False):
            raise ValueError(
                'LED strobing requires software PWM. Please set hardware_pwm: false '
                'in your output_pin configuration (or remove the hardware_pwm line entirely)'
            )

        # Look up the MCU command for changing cycle time dynamically
        try:
            self.set_cycle_cmd = self.mcu.lookup_command(
                "set_digital_out_pwm_cycle oid=%c cycle_ticks=%u"
            )
        except Exception as e:
            raise ValueError(f'Failed to lookup set_digital_out_pwm_cycle command: {e}')

    def start_strobe(self, frequency_hz: float, duty_cycle: float = 0.05) -> None:
        """
        Start PWM strobing at the specified frequency with configurable duty cycle

        Args:
            frequency_hz: Strobing frequency in Hz
            duty_cycle: PWM duty cycle (0.0 to 1.0). Lower values (1-10%) create sharper stroboscopic pulses
        """
        try:
            # Store original cycle time for restoration (only on first call)
            if self.original_cycle_time is None:
                self.original_cycle_time = getattr(self.mcu_pin, '_cycle_time', 0.100)

            # Calculate new cycle time from frequency
            new_cycle_time = 1.0 / frequency_hz

            # Get the printer's toolhead to flush moves before changing cycle time
            # This ensures the move queue is empty as required by the MCU command
            printer = self.output_pin.printer
            toolhead = printer.lookup_object('toolhead')
            toolhead.wait_moves()

            # Convert cycle time to MCU clock ticks
            cycle_ticks = self.mcu.seconds_to_clock(new_cycle_time)

            # Send the set_digital_out_pwm_cycle command to actually change the frequency
            # Note: This command will fail if move queue is not empty (which we ensured above)
            self.set_cycle_cmd.send([self.mcu_pin._oid, cycle_ticks])

            # Update the Python-side cycle time variable for consistency
            self.mcu_pin._cycle_time = new_cycle_time

            # Also update the pwm_max value which is used for duty cycle calculations
            # For software PWM, pwm_max = cycle_ticks
            self.mcu_pin._pwm_max = float(cycle_ticks)

            # Now set the duty cycle via the normal async request mechanism
            # The duty cycle value is multiplied by pwm_max in set_pwm()
            self.output_pin.gcrq.send_async_request(duty_cycle)

            self.is_strobing = True

        except Exception as e:
            logging.warning(f'PWM strobe start failed: {e}')
            raise

    def stop_strobe(self) -> None:
        """Stop PWM strobing and restore original settings"""
        if not self.is_strobing:
            return

        try:
            # Restore original cycle time if we changed it
            if self.original_cycle_time is not None:
                # Get toolhead and flush moves before changing cycle time
                printer = self.output_pin.printer
                toolhead = printer.lookup_object('toolhead')
                toolhead.wait_moves()

                # Convert original cycle time back to MCU clock ticks
                cycle_ticks = self.mcu.seconds_to_clock(self.original_cycle_time)

                # Send command to restore original frequency
                self.set_cycle_cmd.send([self.mcu_pin._oid, cycle_ticks])

                # Update Python-side variables
                self.mcu_pin._cycle_time = self.original_cycle_time
                self.mcu_pin._pwm_max = float(cycle_ticks)

            # Restore original pin state (duty cycle/value)
            self.output_pin.gcrq.send_async_request(self.original_state)

            self.is_strobing = False

        except Exception as e:
            logging.warning(f'PWM strobe stop failed: {e}')


class StrobeController:
    """Main controller for LED strobing functionality"""

    # Registry of supported strobe strategies by section type
    _strategies: Dict[str, Type[StrobeStrategy]] = {
        'output_pin': OutputPinStrobeStrategy,
    }

    def __init__(self, printer, section_name: str) -> None:
        self.printer = printer
        self.section_name = section_name.strip()
        self.strategy: Optional[StrobeStrategy] = None
        self.is_strobing = False
        self.strobe_frequency = 0.0

        if not self.section_name:
            raise ValueError('Empty strobe section name provided')

        # Initialize the strategy for the specified section
        self._initialize_strategy()

    def _initialize_strategy(self) -> None:
        """Initialize the appropriate strobing strategy based on the section type"""
        if not self.section_name:
            return

        # Parse section name to determine type
        section_type = self._get_section_type(self.section_name)

        if section_type not in self._strategies:
            raise ValueError(
                f'Unsupported strobe section type: {section_type}. Supported types: {list(self._strategies.keys())}'
            )

        # Get the printer object for this section
        printer_object = self.printer.lookup_object(self.section_name, None)
        if printer_object is None:
            raise ValueError(f"Section '{self.section_name}' not found in printer configuration")

        # Get the current state of the object
        original_state = self._get_original_state(printer_object, section_type)

        # Create the strategy instance
        strategy_class = self._strategies[section_type]
        self.strategy = strategy_class(printer_object, original_state)

        ConsoleOutput.print(f"Strobe controller initialized for {section_type} '{self.section_name}'")

    def _get_section_type(self, section_name: str) -> str:
        # For sections like "output_pin caselight", return "output_pin"
        # For simple names like "caselight" assume "output_pin" as default
        parts = section_name.split()
        if len(parts) >= 2:
            return parts[0]
        else:
            # Try to lookup with 'output_pin' prefix
            full_name = f'output_pin {section_name}'
            test_object = self.printer.lookup_object(full_name, None)
            if test_object is not None:
                # Update section_name to the full name for future use
                self.section_name = full_name
                return 'output_pin'
            else:
                raise ValueError(
                    f"Could not determine section type for '{section_name}'. Please use full section name like 'output_pin caselight'"
                )

    def _get_original_state(self, printer_object, section_type: str) -> float:
        try:
            if section_type == 'output_pin':
                # Get the last value from the output pin
                return getattr(printer_object, 'last_value', 0.0)
            else:
                return 0.0
        except Exception as e:
            logging.warning(f'Could not get original state: {e}')
            return 0.0

    def start_strobe(self, frequency_hz: float, duty_cycle: float = 0.05) -> None:
        """
        Start strobing at the specified frequency with configurable duty cycle

        Args:
            frequency_hz: Strobing frequency in Hz
            duty_cycle: PWM duty cycle (0.0 to 1.0). Default 5% for sharp stroboscopic pulses
        """
        if not self.strategy:
            ConsoleOutput.print('No strobe section configured - skipping LED strobing')
            return

        if self.is_strobing:
            self.stop_strobe()

        if frequency_hz <= 0:
            raise ValueError(f'Invalid strobe frequency: {frequency_hz} Hz')

        self.strobe_frequency = frequency_hz
        self.is_strobing = True

        # Use strategy's PWM-based strobing with specified duty cycle
        self.strategy.start_strobe(frequency_hz, duty_cycle)

    def stop_strobe(self) -> None:
        """Stop strobing and restore original state"""
        if not self.is_strobing:
            return

        self.is_strobing = False

        # Use strategy's PWM-based strobing stop
        if self.strategy:
            self.strategy.stop_strobe()

    @classmethod
    def register_strategy(cls, section_type: str, strategy_class: Type[StrobeStrategy]) -> None:
        """Register a new strobe strategy for a section type"""
        cls._strategies[section_type] = strategy_class
        ConsoleOutput.print(f'Registered strobe strategy for section type: {section_type}')
