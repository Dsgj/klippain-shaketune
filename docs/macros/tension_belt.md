# Belt tensioning tool

The `TENSION_BELT` macro is a real-time belt tensioning tool that helps you achieve the correct belt tension using stroboscopic visualization.

During this phase, you can tighten the belts manually. When the belts are properly tensioned, they'll look like "frozen" under the strobed lights because their natural frequency matches and sync with the strobe frequency (which corresponds to the input target tension).

## Usage

Here are the parameters available:

| parameters | default value | description |
|-----------:|---------------|-------------|
|T|9|desired belt tension in Newtons|
|DURATION|30|duration in seconds to run the tensioning tool|
|FREQ|None|manually specify excitation frequency in Hz (overrides frequency from config)|
|ACCEL_PER_HZ|None (default to `[resonance_tester]` value)|acceleration per Hz value used for the test|
|AXIS|x|axis you want to move totension. Can be set to either "x", "y", "a", "b". You should use the axis where the belt is vibrating the most.|
|TRAVEL_SPEED|120|speed in mm/s used for all the travel movements|
|Z_HEIGHT|None|Z height for the test. Overrides the Z value from `[resonance_tester]` if specified|

The tool uses the standard string formula to calculate the belt natural resonant frequency based on their tension, length and linear mass density. Typical tension values range from 6-15 Newtons depending on your printer design, motors, etc...

| Target resonant frequency |
| --- |
| $$f_0 = \frac{1}{2L}\sqrt{\frac{T}{\mu}}$$ |
| `f₀` [Hz]: target resonant frequency<br />`T` [N]: desired tension<br />`L` [m]: belt vibrating length<br />`μ` [kg/m]: belt linear mass density |

This frequency is then used to strobe the machine lights for visual feedback when the belt is correctly tensioned. Indeed, we excitate the belt to make it resonate at its natural frequency and when it's properly tensioned, it'll resonate at the same frequency in sync with the strobed light and appear "frozen" to your eyes.

So, just start the macro and while it's running, observe the belt section you specified as `belt_vibrating_length` config entry in `[shaketune]`. Gradually adjust the belt tension (tighten or loosen) until the correct tension is reached.

  > **Note**:
  >
  > If you don't have strobe compatible lights in your machine (any output_pin lights that are PWM drivable), you can instead use an external stroboscope set at the correct frequency and pointed at the machine. Even some mobile phones are known to be able to do it using a dedicated strobe app. 


## Configuration

Before using this tool, you must configure the belt parameters in your `[shaketune]` config section:

```ini
[shaketune]
# ... other Shake&Tune parameters ...

# Belt tension tool parameters
belt_linear_mass: 0.007569
#    Linear mass density of your belt in kg/m. This value is specific to your belt type
#    and manufacturer. For GT2 belts, this is typically between 0.0075 and 0.008 kg/m.
#    To measure it precisely, use a leftover piece of your belt, weigh it on a scale,
#    and divide the mass by the length (the longer the piece, the more accurate).
belt_vibrating_length: 0.150
#    Length of the belt section you want to observe during tensioning in meters.
#    For example, on a Voron 2.4, this is typically the distance from the tensioning idler
#    to the X/Y joint where you'll be looking at the belt and is around 0.150m (15cm).
#    You must choose some spot and measure this distance on your specific machine.
tension_excitation_mode: impulse
#    Excitation mode for belt tensioning. Options: "impulse", "smooth_impulse", or "resonance".
#    See documentation for more info on which mode to choose.
tension_impulse_displacement: 0.5
#    [impulse modes only] Displacement in mm for each impulse. Small values create short,
#    sharp movements that excite belt resonance without moving the toolhead significantly.
tension_impulse_acceleration: 12000.0
#    [impulse modes only] Acceleration in mm/s² for impulses. Higher values create shorter
#    impulse duration and better broadband excitation. Adjust based on your printer's capabilities.
tension_impulse_interval: 0.7
#    [impulse modes only] Time in seconds between impulses. This controls how often the belt
#    gets excited to maintain resonance during the tensioning process.
tension_resonance_frequency: 55.0
#    [resonance mode only] Default frequency in Hz for resonance mode excitation. This value
#    will be used when tension_excitation_mode is set to "resonance" unless overridden by
#    the FREQ parameter. Set this to the frequency you found works best for your belts.
tension_strobe_section: ""
#    [optional] If you machine is equipped with LEDs or FCOB caselights, you can set the
#    Klipper section name for LED strobing. If provided, the macro will strobe LEDs
#    at the calculated target frequency for visual feedback. If left empty, the macro
#    will not strobe any LEDs and you should use an external stroboscope set to the
#    correct frequency (some Android/iOS apps are available to help you with this).
tension_strobe_duty_cycle: 0.05
#    PWM duty cycle for LED strobing (0.01 to 0.5). Lower values (1-10%) create sharper
#    stroboscopic pulses that better "freeze" the belt motion. Default is 5% (0.05).
#    If the belt doesn't appear frozen, try lowering this value to 0.02-0.03.
```

## Excitation Mode Selection

The tool offers three different ways to try to excite your belts at their natural frequency. Each strategy works differently and some printers might work better with one than the other.

### Impulse (Default)

This mode is the easiest as the most universal and easiest to set up. It should be the most effective at making belts vibrate because the sharp edges create a wide range of frequencies that can excite the belt at its natural resonance. However, these instant acceleration changes can be tough on your stepper motors. If your printer has weak motors or drivers, you might experience skipped steps or motor noise without the expected belt vibration... Use this mode first to see if it's effective for your printer.

### Smooth Impulse
This mode does the same thing as the impulse mode but uses smoother acceleration curves shaped like half-sine waves. Instead of jumping instantly to maximum acceleration, it ramps up smoothly, reaches the peak impulse, then ramps back down to zero in a more progressive way.

The smooth transitions are much gentler on your motors and reduce the risk of skipped steps or motor noise. You still get short pulses that are good for belt excitation, just with less harsh mechanical stress on your printer. The downside is that smooth edges don't create quite as much frequency content, so it's a bit less effective than sharp impulses. Switch to this mode if you're experiencing problems with the standard impulse mode like skipped steps.

### Resonance

This mode works very differently from the other two and needs a bit more manual setup: instead of creating pulses on the axis, it just run the standard input shaper test at one fixed frequency, which is perfect if you already know the one that works best for your belts. If the other modes don’t give good results on your printer, give this one a try.
To figure out the right frequency, run the standard input shaper test and watch (and listen to) your belts closely. Note the moment when they visibly "slap" or resonate the most: that’s the frequency you want to use for the resonance mode.

## LED Strobing and Stroboscopic Effect

The belt tension tool uses the **stroboscopic principle** to visualize belt vibration. When the LED blinks at exactly the belt's resonant frequency, the belt appears "frozen" in place.

### Configuration Requirements

For LED strobing to work correctly with this tool, your output_pin **must use software PWM**, not hardware PWM. This is because the strobing needs to dynamically change the PWM frequency, which Klipper hardware PWM doesn't support.
Example of a correct lights configuration, usable with Shake&Tune:

```ini
[output_pin caselight]
pin: PB10
pwm: true
# hardware_pwm: false  # Must be false or omitted!
cycle_time: 0.01       # Initial value, will be changed dynamically during strobing
value: 0
shutdown_value: 0
```
