# Signal routes
Signals are script defined event.

Signals are emitted. Signal name and the data to pass to the signal 

=== ":mast-icon: {{ab.m}}"   
    ```
    signal_emit("player_ship_destroyed", {"DESTROYED_ID": ship_id})
    ```


Only the server receives shared signals

=== ":mast-icon: {{ab.m}}"   
    ```
    //shared/signal/player_ship_destroyed
    ```

Each console will receive this signal

=== ":mast-icon: {{ab.m}}"   
    ```
    //signal/player_ship_destroyed
    ```


    
