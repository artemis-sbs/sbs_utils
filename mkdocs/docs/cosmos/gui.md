# Gui Components

The MAST Story Components are used to create GUI elements.

This can be part of a console, 


- Layout
- Layout components
- Form Controls

## Gui Layout

<video controls autostart loop width="640" height="480" src="../../media/gui_layout.mp4">
</video>


## await gui (choices)

def await_gui (self, 
    buttons=None, 
    timeout=None, 
    on_message=None, 
    test_refresh=None, 
    test_end_await=None, 
    on_disconnect=None):

=== ":mast-icon: {{ab.m}}"
    ```
    await gui
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.await_gui()
    ```

## Section


=== ":mast-icon: {{ab.m}}"
    ```
    section style=""
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_section("")
    ```

## Row


=== ":mast-icon: {{ab.m}}"
    ```
    row
    row style=""
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_row()
    self.gui_row("")
    ```

## Row


=== ":mast-icon: {{ab.m}}"
    ```
    blank
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_blank()
    ```

## Hole


=== ":mast-icon: {{ab.m}}"
    ```
    hole
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_hole()
    ```

## Text and Text append


=== ":mast-icon: {{ab.m}}"
    ```
    """TEXT """

    ^^^ Append ^^^
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_text("")
    ```

## Text Input


=== ":mast-icon: {{ab.m}}"
    ```
    input message "Make a toast"
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_text_input("", "Hint" label)
    ```

## Button


=== ":mast-icon: {{ab.m}}"
    ```
    button "Text":
       ... code...
    end_button
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_button("Text", label)
    ```

## Checkbox


=== ":mast-icon: {{ab.m}}"
    ```
    checkbox var "Text" 
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_checkbox("Text", value)
    ```

## Dropdown


=== ":mast-icon: {{ab.m}}"
    ```
    dropdown var "val1,val2":
        ... code...
    end_dropdown 
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_dropdown("val1,val2", value)
    # Handle change in on_message
    ```

## Face


=== ":mast-icon: {{ab.m}}"
    ```
    face var
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_face("Face Text")
    ```

## Slider


=== ":mast-icon: {{ab.m}}"
    ```
    intslider var low high value
    slider var low high value
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    def gui_slider (self, val, low, high, show_number=True, label=None, style=None):
    self.gui_slider("Face Text")
    ```

## Radio buttons


=== ":mast-icon: {{ab.m}}"
    ```
    radio var "b1, b2, b3"
    vradio var "b1, b2, b3"
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_radio("b1, b2, b3")
    self.gui_radio("b1, b2, b3", True)
    ```

## Ship


=== ":mast-icon: {{ab.m}}"
    ```
    ship val # this isn't support when write this
    ship "val"
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_ship(ship)
    ```

## Image


=== ":mast-icon: {{ab.m}}"
    ```
    ship val # this isn't support when write this
    ship "val"
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_image(file, color)
    ```

## Sprite

This doesn't exists as I write this

=== ":mast-icon: {{ab.m}}"
    ```
    sprite val # this isn't support when write this
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_sprite(ship, x,y, w,h)
    ```

## Full console

For building console widget by widget. 
Call this to specify which console.

=== ":mast-icon: {{ab.m}}"
    ```
    console "helm"
    console var
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_console("helm")
    ```

## Activate console

For building console widget by widget. 
Call this to specify which console.

=== ":mast-icon: {{ab.m}}"
    ```
    console activate "helm"
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_activate_console("helm")
    ```

## Layout console widget


=== ":mast-icon: {{ab.m}}"
    ```
    console widget "2dview"
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_console_widget("2dview")
    ```

## Layout console widget


=== ":mast-icon: {{ab.m}}"
    ```
    widget_list "norm_helm"  "2dview^throttle"
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_console_widget+list("norm_helm", "2dview^throttle")
    ```

## Layout python coded widget


=== ":mast-icon: {{ab.m}}"
    ```
    gui control func()
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    self.gui_content(listbox())
    ```
