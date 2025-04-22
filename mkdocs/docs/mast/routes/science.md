

# Science scan 
The task running the science routing will provide these variables

- SCIENCE_ORIGIN_ID - The engine ID of the player ship doing the scan
- SCIENCE_ORIGIN - The python Agent of the player ship doing the scan
- SCIENCE_SELECTED_ID - The engine ID of the Agent being scanned
- SCIENCE_SELECTED - The python Agent of being scanned


## Enabling science
NPCs are not immediately available to the science system. Science must be enabled.

??? warning "It is possible to enable science too much"
    Enabling science runs a task to handle the scans. It is vary possible that an agent meets the conditions of one or more //enable/science.
    roles and conditions should be created to make the agent unique enough so that it is only enabled once.
    If science is enabled more than once, you may not see all the scan tabs expected.
    This issue may be fixed in a future version.

Enabling science is a label, and can have addition task related data associated with it.

=== ":mast-icon: {{ab.m}}"
    ```
    //enable/science if has_roles(COMMS_SELECTED_ID, "raider")
        # Example of data being defined with enable science
        bio_scan_count = 0
    ```

## Scan tabs
Like the comms button system, science has buttons. These button are the scan tabs.
The code in the button's code block is executed when the scan is complete.
The \<scan> command specifies the scan results.

The example show that the response uses a random selection of responses.
Each line starting with % is one one the choices that could be displayed.

=== ":mast-icon: {{ab.m}}"
    ```

    //enable/science if has_roles(SCIENCE_SELECTED_ID, "wreck")

    //science if has_role(SCIENCE_SELECTED_ID, "wreck")

        + "scan":
            <scan>
                % Gutted and battle-scarred wreckage that used to be a starship.
                % Hulk of a destroyed ship.
                % Wreckage of a destroyed starship. 
        + "status":
            <scan> 
                % WARNING: Radiation leak detected! Do not board this derelict!
                % Readings indicate this ship was destroyed by weapons fire.
                % Cause of this ship's destruction cannot be determined by sensor scan.
                % WARNING: high radiation levels! This ship might have been destroyed by an accidental reactor leak.
                % WARNING: high radiation level warning for the entire crew! This ship might have been destroyed by an accidental reactor leak.

        + "bio":
            <scan>
                % Indeterminate life signs detected. It could be alien eggs or pods. Proceed with caution.
                % No life detected.
                % Readings indicate a dangerous pathogen on this wreck. Recommend quarantine protocol Beta.
                % Reading radiation mutations of pathogenetic viruses on this wreck. Recommend quarantine protocol Omicron.
    ```
