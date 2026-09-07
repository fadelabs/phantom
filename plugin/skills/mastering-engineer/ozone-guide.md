# Using iZotope Ozone for mastering

Ozone 12 is the current major version covered by this guide. Check the installed
edition and discover the parameters the DAW exposes before building a chain.
Modules and controls differ across versions and editions. A module's appearance
in this reference does not mean the user's copy includes it.

Use Ozone to make a specific change you can hear and measure. A chain does not
need every module, and Master Assistant's proposal is a starting point for review.

## EQ and dynamics

Use Equalizer for broad tonal adjustments or specific corrective cuts. Choose
its phase mode deliberately; do not describe its Analog mode as a saturation
processor. Use Exciter or Vintage Tape when added harmonics are the intention.

Use Dynamic EQ for a problem that appears intermittently in a frequency region.
A static high-frequency cut can reduce brightness throughout the song, so it is
not interchangeable with a dynamic de-esser.

Use the Dynamics module when a band or the whole mix needs level control. Set
crossovers and timing by listening to the material. Compare with bypass at a
similar level before adding more compression.

Vintage Compressor is a separate option for compression character. Its mode
names are **Sharp, Balanced, and Smooth**, not Opto/FET/Tube models. See
[iZotope's compressor guide](https://www.izotope.com/community/blog/choosing-the-right-compressor).

## Maximizer

Ozone 12 adds IRC 5. Do not rank the IRC modes as a fixed progression from
"clean" to "aggressive" or assign one mode to a genre without auditioning it.
Compare the available modes on the loudest passage, listening for lost attack,
pumping, bass distortion, and changes in stereo image.

Modern Maximizer versions use an input **Gain** control and an output ceiling;
do not instruct the user to lower a threshold control that their version does
not have. Increase gain only as far as the result supports. Set a ceiling for
the actual delivery requirements and enable True Peak when a true-peak ceiling
is required. Re-measure the exported file with `analyze_loudness`.

A streaming service's normalization level is not a universal mastering target.
Check the intended delivery specification and the musical result. Lowering the
level can be sufficient to address an over-ceiling peak; extra limiting is not
always necessary.

See [iZotope's limiter explanation](https://www.izotope.com/community/blog/an-introduction-to-limiters-and-how-to-use-them)
and [Ozone 12's algorithm overview](https://www.izotope.com/community/blog/inside-ozone-12).

## Stereo image

Ozone Imager's Width control is centered on **0** for unchanged width; negative
values narrow and **-100** is mono. Positive values widen. Do not use a generic
"0% mono, 100% original" mapping for this control. Discover the host parameter
range before automating it.

Check bass focus and mono compatibility before and after a width change.
Stereoize adds stereo information to narrow material; audition it carefully.
Do not apply a bass-widening or mono-bass preset automatically to every mix.

See [iZotope's Imager explanation](https://www.izotope.com/en/learn/6-tips-for-using-imager-in-ozone-9).

## Reference matching and newer modules

Match EQ compares captured spectra. Match corresponding sections, choose a
sensible amount and smoothing, and listen for changes to the song's identity.
Matching a spectrum does not reproduce an arrangement, recording, or mix.

Ozone 12 Advanced includes Stem EQ, Bass Control, and Unlimiter. Treat those as
optional capabilities, not prerequisites for a Phantom workflow. Stem processing
may introduce separation artifacts, and dynamic restoration is not proof that
lost original samples have been recovered. Confirm the installed edition in the
[Ozone product comparison](https://www.izotope.com/products/ozone-advanced).

## Suggested sequence

1. Analyze the unprocessed render and a suitable reference with Phantom.
2. Identify the change the master actually needs. Start with the fewest modules
   that can address it.
3. Inspect available parameters and save the starting state.
4. Adjust while listening at a comparable level. Check the busiest and quietest
   sections, not just the section Master Assistant heard.
5. Export, re-measure true peak and loudness, check mono compatibility, and
   compare against the original. Preview a delivery codec when practical.

If the bridge cannot expose an Ozone parameter, give manual instructions using
the installed UI. Never claim an assistant changed a hidden control.
