# Changelog

## 0.13.0 - December 2, 2023

### 💥 Breaking changes

* As part of [#46](https://github.com/sdss/archon/issues/46) `ExposureDelegate.post_process()` is now called once for each controller CCD with a `FetchDataDict` as the only argument. The function must modify the input dictionary in place and return `None`.

### 🚀 New

* [#47](https://github.com/sdss/archon/issues/47) Added a framework for recovering images when they fail to be written to disk. A lockfile is created when the buffer is read which can be used to recover the original image and header. Recovery happens automatically when the actor starts or via the `recover` command.

### ⚙️ Engineering

* [#46](https://github.com/sdss/archon/issues/46) Significant clean-up of the `ExposureDelegate` code.


## 0.12.0 - November 30, 2023

### 💥 Breaking changes

* Support for Python 3.8 has been deprecated.

### 🚀 New

* [#45](https://github.com/sdss/archon/issues/45) Added a new option `files.write_engine` that can be set to `astropy` or `fitsio`. In the latter case it will use fitsio to write images to disk. This requires installing `sdss-archon` with the `fitsio` extra (e.g., `pip install sdss-archon[fitsio]`).

### 🔧 Fixed

* Fix broken tests in 3.12.


## 0.11.6 - November 24, 2023

### 🏷️ Changed

* If `write_async=False` do not use an executor to write images to disk.


## 0.11.5 - November 18, 2023

### ✨ Improved

* Buffer is written to temporary file (usually in `/tmp`) before it's moved to the final permanent location.


## 0.11.4 - November 5, 2023

### 🔧 Fixed

* Reduce length of long header comment.


## 0.11.3 - November 5, 2023

### 🚀 New

* Added a configuration option `files.write_async` (defaults to `true`) that determines whether all the camera files for a controller are written to disk concurrently or sequentially.


## 0.11.2 - September 14, 2023

### ✨ Improved

* `wait-until-idle` won't return until the exposure has been saved to disk.

### 🔧 Fixed

* Ensure that the exposure delegate is always unlocked when `abort` or `reset` are called.


## 0.11.1 - August 14, 2023

### ✨ Improved

* Extra header values do not overwrite the existing header comments.

### ⚙️ Engineering

* Lint using `ruff`.


## 0.11.0 - July 18, 2023

### 💥 Breaking changes

[#44](https://github.com/sdss/archon/issues/44) Allow exposure times longer than 1,000 seconds. This requires a change in how the ACF timing scripts are written to support setting the exposure time in centiseconds. See the PR description for details. Do not update to this version without updating the ACF file as well!


## 0.10.0 - July 13, 2023

### ✨ Improved

* Added `expose --async-readout` flag that finishes the expose command as soon as readout begins.
* Added `wait-until-idle` command that returns once the spectrographs are idle.

### 🏷️ Changed

* Do not set the `ERROR` status in the controller if `ArchonController.get_device_status()` or `ArchonController.get_system()` time out.
* `ExposureDelegate.readout()` will fail is any controller is still exposing.

### 🔧 Fixed

* Prevent controller state to briefly go to `IDLE` before changing to a non-idle status.


## 0.9.0 - April 13, 2023

### 🚀 New

* [DT-4](https://jira.sdss.org/browse/DT-4) Allow to create checksum files for each newly written images. To enable, add a `checksum` section to the configuration file with `checksum.write: true`. The mode of the checksum can be set with `checksum.mode` to `md5` (default) or `sha1`. The file to which the checksum is appended can be defined with `checksum.file`, which default to the SJD with extension `.sha1sum` or `.md5sum` depending on the checksum mode.


## 0.9.0b1 - March 10, 2023

### 🚀 New

* Upgrade `CLU` to `2.0.0b2` and add the `get-command-model` command.


## 0.8.0 - March 3, 2023

### ✨ Improved

* Allow to run `LOADTIMING` without `APPLYALL` after an init.
* Output filenames as a single keyword.
* Add `ArchonController.send_and_wait()`.
* Allow choosing what `APPLYXXX` commands to send on init.

### 🔧 Fixed

* Fix overwriting of images when readout done independently. The `nextExposureFile` was not being increased in that case.

### ⚙️ Engineering

* Support Python 3.11.
* Update test and docker workflows. The docker image now uses `python:3.11-slim-bullseye`.


## 0.7.0 - December 2, 2022

### 🚀 New

* `RESETTIMING` is no longer user, which should prevent race conditions in some circumstances.
* Add a `pre_exposure` hook to the delegate.
* Added `--no-write` flag to `expose`.

### ✨ Improved

* HDUs are now written to a temporary file first which is then renamed to the final file name.
* It is now possible to defined the controller class in the actor and to pass the configuration to use to the controller.


## 0.6.2 - September 15, 2022

### ✨ Improved

* Add backplane ID and version to header.
* Allow to exclude some cameras from writing.
* Allow to use SJD for path.
* Add status `--debug` flag to change message level.

### 🔧 Fixed

* Deal with controller without Lines or Pixels params.


## 0.6.1 - May 28, 2022

### 🚀 New

* [#40](https://github.com/sdss/archon/issues/40) `ArchonController.write_config()` now acccepts an `overrides` dictionary with keywords to be replaced in the ACF file. The format is similar to `ArchonController.write_line()`. If a section `archon.acf_overrides` is present in the configuration file, those overrides will be applied when the `init` command is called. This allows to define a single ACF file but tweak some parameters depending on the controller to which it is sent. `archon.acf_overrides` must be a dictionary with either a `global` section (overrides sent to all controllers) or sections for each controller name.
* Add `ExposureDelegate.expose_cotasks()` for tasks that should be run during integration. This is useful to grab sensor data that could change as readout begins, for example lamp status, but there is no promise that the `expose_cotasks()` will be waited or that will complete before readout begins.

### ✨ Improved

* `ExposureDelegate.expose()` always blocks, even if `readout=False`, and closes the shutter at the end of the exposure time.
* The Archon buffer read is saved to the header of the images.


## 0.6.0 - May 14, 2022

### 💥 Breaking changes

* `expose start|finish|abort` are not `expose --no-readout`, `readout`, and `abort` respectively. `expose` without `--no-readout` will expose and readout all in the same command.
* Removed `lvm` submodule. Use `lvmscp` instead.

### 🚀 New

* [#38](https://github.com/sdss/archon/issues/38) `ArchonController.write_line()` allows to set and apply a line in the configuration file without reloading it completely.
* [#39](https://github.com/sdss/archon/issues/39) Support windowing.
* Archon power status is now reported as part of the status and overall better handled.
* Some refactoring to support `yao` and more generally to implement external packages that use the library and the actor.
* Added `power on|off` and `disconnect` commands.
* Support `enabled_controllers` config keyword

### ✨ Improved

* `expose finish --header` now accepts a JSON-like dictionary in which a keyword can be the name of a detector. In that case the contents of that keyword are only added to the detector with that name.
* The `init` command does a better job at understanding relative paths.
* `acf_file` in the configuration can be a dictionary of controller to file.


## 0.5.1 - September 18, 2021

### ✨ Improved

* [#32](https://github.com/sdss/archon/issues/32) Expand the default header with information about gain, readout noise, bias section, etc.
* [#24](https://github.com/sdss/archon/issues/24) Added `ExposureDelegate.readout_cotasks()` that can be overridden to execute tasks concurrently during readout. The LVM delegate now reads temperatures and IEB data at this point.
* [#34](https://github.com/sdss/archon/issues/34) The path to the last ACF file written to the controller is stored in the user configuration file (usually at `~/.config/sdss/archon.yaml`) from where it's read when the controller starts. This prevents having to initialise the controller every time `archon` is restarted (with the corresponding power cycling of the CCDs) just to update the ACF path, but it introduces a certain risk that the ACF stored in the configuration file and the one loaded are actually different. In general it's still recommended to do an `archon init` when the daemon is restarted.
* Added script for ~800MHz readout.
* Use `framemode=split` and rearrange taplines to allow proper display in the GUI.


## 0.5.0 - September 6, 2021

### 🚀 New

* [#29](https://github.com/sdss/archon/pull/29) Support binning.
* [#30](https://github.com/sdss/archon/pull/30) HDR (32-bit sampling) mode can be enabled when loading the script by running `archon init --hdr [<script>]`.

### ✨ Improved

* `archon init` accepts an optional parameter to define the ACF script to load.
* [#31](https://github.com/sdss/archon/pull/31) Tests for the actor.

### 🔧 Fixed

* Fixed error when moving shutter or hartmann doors manually.


## 0.4.0 - August 22, 2021

### 🚀 New

* Added `--count` flag to `lvm expose` to support multiple consecutive exposures.
* Support for the three LVM CCDs.

### ✨ Improved

* Always close connections to remote TCP services to prevent leaving unclosed file descriptors.
* Read pressure sensors concurrently.
* Update LVM lamps.

### 🔧 Fixed

* Improve how auto-flushing is implemented. In its previous mode, `FlushOne` would often be called once between exposing and reading out, introducing an offset in the lines that manifested as a lines overscan of ~90 lines. The new implementation allows to disable auto-flushing before an exposure begins.


## 0.3.0 - June 20, 2021

### 🚀 New

* [#21](https://github.com/sdss/archon/pull/21) Implemented profiles for LVM and BOSS (placeholder).
* [#22](https://github.com/sdss/archon/pull/22) Implement custom LVM expose delegate along with a group of `lvm` commands to control the shutter, hartmann doors, and to expose using the shutter.
* [#23](https://github.com/sdss/archon/pull/23) Refactor expose actor code into an `ExposeDelegate` that allows for more flexible customisation.
* [#26](https://github.com/sdss/archon/pull/26) Use the [furo](https://pradyunsg.me/furo/) theme for the documentation.
* Add option to define additional header keywords in the configuration file that read values from the actor keyword datamodel.
* Add `lvm-lab` script for laboratory testing.
* `POWERON` and `POWERBAD` controller status bits.
* Code to log LVM exposures in Google Sheets.

### 🔧 Fixed

* Require `sdss-clu>=0.7.8` to allow `archon expose finish --header` to work with strings that have spaces. It should now be possible to pass commands like `archon expose finish --header '{"KEYWORD1": [1, "A comment"]}'`. For header keyword values that are a list of value and comment, the list is converted into a tuple internally so that `astropy` can parse it correctly.

### 🧹 Cleanup

* [#17](https://github.com/sdss/archon/issues/17) Handle actor shutdown more gently when it is started from the CLI either in debug mode or as a daemon.


## 0.2.1 - April 6, 2021

### 🔧 Fixed

* Fix Docker creation for tags.


## 0.2.0 - April 6, 2021

### 🚀 New

* [#10](https://github.com/sdss/archon/issues/10) Add actor command `reconnect` that allows to recreate the TCP/IP connection to one or multiple controllers. If the controller cannot be connected when the actor starts, a warning is issued but the actor will be created.
* [#11](https://github.com/sdss/archon/issues/11) Read the Govee H5179 temperature and humidity and write a basic FITS header.
* [#12](https://github.com/sdss/archon/issues/12) Add `ArchonController` methods to `abort`, `read out`, and `flush` an exposure. Actor `expose` command now accepts `expose start` and `expose finish` to allow for non-blocking integration. Better handling of status flags.

### 🧹 Cleanup

* Basic documentation.
* Use GitHub Container Registry instead of Docker Hub.


## 0.1.0 - March 6, 2021

### 🚀 New

* Initial version of the library and actor. Supports communication with the Archon controller, Archon command tracking and reply parsing, and basic actor functionality, including exposing.
* Build and push docker image to [lvmi/archon](https://hub.docker.com/repository/docker/lvmi/archon).
