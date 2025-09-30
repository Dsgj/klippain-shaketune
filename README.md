# Klipper Shake&Tune plugin

Shake&Tune is a Klipper plugin from the [Klippain](https://github.com/Frix-x/klippain) ecosystem, designed to create insightful visualizations to help you troubleshoot your mechanical problems and give you tools to better calibrate the input shaper filters on your 3D printer. It can be installed on any Klipper machine and is not limited to those using the full Klippain.

Check out the **[detailed documentation here](./docs/README.md)**.

![logo banner](./docs/banner.png)


## Installation

Follow these steps to install Shake&Tune on your printer:
  1. Be sure to have a working accelerometer on your machine and a `[resonance_tester]` section defined. You can follow the official [Measuring Resonances Klipper documentation](https://www.klipper3d.org/Measuring_Resonances.html) to configure it.
  1. Install Shake&Tune by running over SSH on your printer:
     ```bash
     wget -O - https://raw.githubusercontent.com/Frix-x/klippain-shaketune/main/install.sh | bash
     ```
  1. Then, append the following to your `printer.cfg` file and restart Klipper:
     ```
     [shaketune]

     ### General parameters
     # result_folder: ~/printer_data/config/ShakeTune_results
     #    Path where the processed results will be stored. If the folder doesn't exist,
     #    it will be automatically created. You can change this if you'd like to store 
     #    results in a different location.
     # number_of_results_to_keep: 10
     #    This setting defines how many results you want to keep in the result folder.
     #    Once the specified number is exceeded, older results will be automatically deleted
     #    to free up space on the SD card and avoid cluttering the results folder.
     # keep_raw_data: False
     #    If set to True, Shake&Tune will store both the processed graphs and the raw accelerometer
     #    .stdata files in the results folder. This can be useful for debugging or archiving purposes.
     #    Please always attach them when reporting any issues on GitHub or Discord.
     # show_macros_in_webui: True
     #    Mainsail and Fluidd doesn't create buttons for system commands (macros that are not part
     #    of the printer.cfg file). This option allow Shake&Tune to inject them into the webui at runtime.
     #    If set to False, the macros will be hidden but still accessible from the console by typing
     #    their names manually, which can be useful if you prefer to encapsulate them into your own macros.
     # timeout: 600
     #    This defines the maximum processing time (in seconds) to allows to Shake&Tune for generating 
     #    graphs from a .stdata file. 10 minutes should be more than enough in most cases, but if you have
     #    slower hardware (e.g., older SD cards or low-performance devices), increase it to prevent timeouts.
     # measurements_chunk_size: 2
     #    Each Shake&Tune command uses the accelerometer to take multiple measurements. By default,
     #    Shake&Tune will write a chunk of data to disk every two measurements, and at the end of the
     #    command will merge these chunks into the final .stdata file for processing. "2" is a very
     #    conservative setting to avoid Klipper Timer Too Close errors on lower end devices with little
     #    RAM, and should work for everyone. However, if you are using a powerful computer, you may
     #    wish to increase this value to keep more measurements in memory (e.g., 15-20) before writing
     #    the chunk and avoid stressing the filesystem too much.
     # max_freq: 200
     #    This setting defines the maximum frequency at which the calculation of the power spectral density
     #    is cutoff. The default value should be fine for most machines and accelerometer combinations and
     #    avoid touching it unless you know what you're doing.
     # dpi: 300
     #    Controls the resolution of the generated graphs. The default value of 300 dpi was optimized
     #    and strikes a balance between performance and readability, ensuring that graphs are clear
     #    without using too much RAM to generate them. Usually, you shouldn't need to change this value.

     ### Belt tensioning tool parameters
     # belt_linear_mass: 0.007569
     #    Linear mass density of your belt in kg/m. This value is specific to your belt type
     #    and manufacturer. For GT2 belts, this is typically between 0.0075 and 0.008 kg/m.
     #    To measure it precisely, use a leftover piece of your belt, weigh it on a scale,
     #    and divide the mass by the length (the longer the piece, the more accurate).
     # belt_vibrating_length: 0.150
     #    Length of the belt section you want to observe during tensioning in meters.
     #    For example, on a Voron 2.4, this is typically the distance from the tensioning idler
     #    to the X/Y joint where you'll be looking at the belt and is around 0.150m (15cm).
     #    You must choose some spot and measure this distance on your specific machine.
     # tension_impulse_displacement: 0.5
     #    Displacement in mm for each impulse. Small values create short, sharp movements
     #    that excite belt resonance without moving the toolhead significantly.
     # tension_impulse_acceleration: 12000.0
     #    Acceleration in mm/s² for impulses. Higher values create shorter impulse duration
     #    and better broadband excitation. Adjust based on your printer's capabilities.
     # tension_impulse_interval: 0.7
     #    Time in seconds between impulses. This controls how often the belt gets excited
     #    to maintain resonance during the tensioning process.
     # tension_impulse_strategy: impulse
     #    Excitation strategy selection for the belt tensioning tool. Can be one of "impulse"
     #    or "smooth_impulse". See the documentation for more details.
     # tension_strobe_section: ""
     #    [optional] If you machine is equipped with LEDs or FCOB caselights, you can set the
     #    Klipper section name for LED strobing. If provided, the macro will strobe LEDs
     #    at the calculated target frequency for visual feedback. If left empty, the macro
     #    will not strobe any LEDs and you should use an external stroboscope set to the
     #    correct frequency (some Android/iOS apps are available to help you with this).
     #    IMPORTANT: The output_pin must use software PWM (hardware_pwm: false or omitted)
     #    for dynamic frequency changes to work. See documentation for details.
     # tension_strobe_duty_cycle: 0.05
     #    PWM duty cycle for LED strobing (0.01 to 0.5). Lower values (1-10%) create sharper
     #    stroboscopic pulses that better "freeze" the belt motion. Default is 5% (0.05).
     ```

Don't forget to check out **[Shake&Tune documentation here](./docs/README.md)** for more details and how to use the macros or the CLI.
