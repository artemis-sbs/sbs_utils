# Changelog


## 1.3.0

### LegendaryMissions (core addons)

- Improved Game master console
- elite abilities refactor to allow new and custom abilities
- Ship changes can be disable via settings.yaml SHIP_PICK_READ_ONLY
- changing console can be disabled via settings.yaml CAN_CHANGE_CONSOLE
- added more comms select popup speech bubble text from forum feedback
- a number of gui changes based on sub_utils updates: e.g. removed gui_represent calls
- wreck behavior now behav_wreck the engine does use this new value

- hangar has a override setting file hangar_crafts.yaml
- craft names changed


-  #518, #369, #454, #460, #476, #473, #467, #463, #442, #432, #425, #423, #304, #407

### sbs_utils

- the fetch batch file system was replaced with the sbs command line tool. Docs were updated.
- added log files for compile errors (mast.compile.log) and runtime errors (mast.runtime.log)
- comms_message emits a signal comms_message
- is_dev_build is cached and can be set via set_dev_build
- Added debug_print
- added gui dirty system so script no longer needs to call gui_represent items mark themselves dirty and the represent is handled automatically
- a mock version of sbs ships with library in sbs_utils.mock.sbs used for testing and debugging outside of the Cosmos exe
- added Image atlas
- Improve gui_tab system
- Removed engine grid in hangar crafts
- Buttons and checkbox have icon options, background color
- Add more option to log and logger
- Improved listbox handling of gui_subsection
- gui_subsection can be used in gui_message e.g. to make a custom button/clickable area
- gui margin, borders padding work correctly 
- listbox supports tree like expand and collapse
- listbox supports custom collapse item
- listbox supports custom click_tag
- text area fixed measuring issues
- text area subset of markdown syntax: can have images, face, ship sections
- Quest screen
- if, for, match statements can be used in main




Fixes:
    #382, #399, #351, #513, #335, #515, #362, #532, #525



