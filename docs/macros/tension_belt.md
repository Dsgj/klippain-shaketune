# Belt tensioning tool

The `TENSION_BELT` macro is a real-time belt tensioning tool that helps you get the right tension. This macro uses the target tension as an input alongside other belt characteristics (which are set in the config) to strobe the machine lights at a calculated frequency, and at the same time excites the belt(s) to make them resonate freely.

During this phase, you can tighten the belts manually. When the belts are properly tensioned, they'll look like "frozen" under the strobed lights because their natural frequency matches and sync with the strobe frequency (which corresponds to the input target tension).

## Usage

Here are the parameters available:

| parameters | default value | description |
|-----------:|---------------|-------------|
|T|9|desired belt tension in Newtons|
|DURATION|30|duration in seconds to run the tensioning tool|
|ACCEL_PER_HZ|None (default to `[resonance_tester]` value)|acceleration per Hz value used for the test|
|AXIS|x|axis you want to move totension. Can be set to either "x", "y", "a", "b". You should use the axis where the belt is vibrating the most.|
|TRAVEL_SPEED|120|speed in mm/s used for all the travel movements|
|Z_HEIGHT|None|Z height for the test. Overrides the Z value from `[resonance_tester]` if specified|

Start the macro with your desired tension value and observe the belt section you specified as `belt_vibrating_length` config entry in `[shaketune]`. Gradually adjust the belt tension (tighten or loosen) until the belt appears "frozen" under the strobe light. When this happens, the tension is correct.

Start with slightly loose belts and gradually tighten. The effect is most visible in a darkened room with the strobe light. If you don't see the "frozen" effect, double-check your `belt_vibrating_length` configuration. For CoreXY printers, tension both belts to the same value for balanced operation. Typical tension values range from 6-15 Newtons depending on your printer design, motors, etc...

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
tension_chirp_halfband: 20
#    Frequency sweep range above the target frequency in Hz. The macro will sweep
#    frequencies from (target - halfband) to (target + halfband) to ensure the belt
#    receives energy at its natural frequency. The default value of 20 Hz should work
#    well for most cases and usually doesn't need to be changed.
tension_chirp_duration: 1.0
#    Duration of each chirp sweep in seconds. This controls how long the macro spends
#    sweeping through the frequency range. The default value of 1.0 second provides
#    a good balance between excitation effectiveness and loop duration for the test.
tension_strobe_pin: ""
#    [optional] If you machine is equipped with LEDs or FCOB caselights, you can set the
#    Klipper section name for LED strobing. If provided, the macro will strobe LEDs
#    at the calculated target frequency for visual feedback. If left empty, the macro
#    will not strobe any LEDs and you should use an external stroboscope set to the
#    correct frequency (some Android/iOS apps are available to help you with this).
```

## How it works

The tool uses the standard string formula to calculate the belt natural resonant frequency based on their tension, length and linear mass density. This frequency is then used as the target frequency to strobe the LEDs for visual feedback. The excitation is done by continuously sweeping the belt with a chirp pattern that spans around the target frequency (+-20 Hz by default).

| Target resonant frequency |
| --- |
| $$f_0 = \frac{1}{2L}\sqrt{\frac{T}{\mu}}$$ |
| `f₀` [Hz]: target resonant frequency<br />`T` [N]: desired tension<br />`L` [m]: belt vibrating length<br />`μ` [kg/m]: belt linear mass density |

Using a chirp pattern as excitation ensures the belt receives at least some energy at its natural frequency regardless of its current tension.

LEDs strobe at the exact target frequency, provide visual feedback due to the image remanent effect on the human eye. While the tool runs, you manually adjust the belt tension until the belt appears "frozen" under the strobe light meaning their natural frequency matches the strobe frequency (and thus the target tension is achieved).
