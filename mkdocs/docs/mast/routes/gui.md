
# GUI

Routes related to the GUI

# Gui consoles


New consoles can be created using a @console route

The client console will discover these and add them to the list of selectable consoles

=== ":mast-icon: {{ab.m}}"
    ```
    @console/hangar "Flight Hangar"
    " Fly fighter- shuttle and cargo missions

    ```


    

Respond to when a console is presented

=== ":mast-icon: {{ab.m}}"
    ```
    //gui/norm_weap
    ```

e.g. manual beams is implemented as an extension of weapons

    
# Other Console events

When the user select change console

=== ":mast-icon: {{ab.m}}"
    ```
    //console/change
    ```

When the user changes the camera mode

=== ":mast-icon: {{ab.m}}"
    ```
    //console/mainscreen/change
    ```
