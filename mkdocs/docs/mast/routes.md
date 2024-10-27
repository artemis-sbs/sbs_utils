# Behavior Components


## Sequence

=== "Mast"
    ```
    bt seq label1 & label2
    ```

=== "Python"
    ```
    self.behave_seq (label1, label2):
    ```

## Select

=== "Mast"
    ```
    bt  sel label1 | label2
    ```
=== "Python"
    ```
    self.behave_seq (label1, label2):
    ```

## Until

=== "Mast"
    ```
    bt until my_label
    bt until fail my_label
    ```

=== "Python"
    ```
    self.behave_until (my_label)
    self.behave_until (my_label, PollResults.OK_END)
    self.behave_until (my_label, PollResults.OK_FAIL)
    ```        

## Invert

=== "Mast"
    ```
    bt invert my_label
    ```

=== "Python"
    ```
    self.behave_invert (my_label):
    ```


## yield

=== "Mast"
    ```
    yield FAIL
    yield SUCCESS
    ```

=== "Python"
    ```
    yield PollResults.BT_FAIL
    yield PollResults.BT_SUCCESS
    ```
