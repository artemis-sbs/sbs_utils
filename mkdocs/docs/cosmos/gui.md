Gui Components
##################

The MAST Story Components are used to create GUI elements.

This can be part of a console, 


- Layout
- Layout components
- Form Controls

Gui Layout
================================

<video controls autostart loop width="640" height="480" src="../../media/gui_layout.mp4">
</video>


await gui (choices)
=================================

def await_gui (self, 
    buttons=None, 
    timeout=None, 
    on_message=None, 
    test_refresh=None, 
    test_end_await=None, 
    on_disconnect=None):

.. tabs::
    .. code-tab:: mast

        await gui

    .. code-tab:: py PyMast
        
        self.await_gui()



Section
=================================


.. tabs::
    .. code-tab:: mast

        section style=""

    .. code-tab:: py PyMast
        
        self.gui_section("")


Row
=================================


.. tabs::
    .. code-tab:: mast

        row
        row style=""

    .. code-tab:: py PyMast
        
        self.gui_row()
        self.gui_row("")


Row
=================================


.. tabs::
    .. code-tab:: mast

        blank
        
    .. code-tab:: py PyMast
        
        self.gui_blank()


Hole
=================================


.. tabs::
    .. code-tab:: mast

        hole

    .. code-tab:: py PyMast
        
        self.gui_hole()



Text and Text append
=================================


.. tabs::
    .. code-tab:: mast
        
        """TEXT """

        ^^^ Append ^^^


    .. code-tab:: py PyMast

        self.gui_text("")


Text Input
=================================


.. tabs::
    .. code-tab:: mast
        
        input message "Make a toast"

    .. code-tab:: py PyMast
        
        self.gui_text_input("", "Hint" label)



Button
=================================


.. tabs::
    .. code-tab:: mast
        
        button "Text":
           ... code...
        end_button

    .. code-tab:: py PyMast
        
        self.gui_button("Text", label)




Checkbox
=================================


.. tabs::
    .. code-tab:: mast
        
        checkbox var "Text" 

    .. code-tab:: py PyMast
        
        self.gui_checkbox("Text", value)


Dropdown
=================================


.. tabs::
    .. code-tab:: mast
        
        dropdown var "val1,val2":
            ... code...
        end_dropdown 

    .. code-tab:: py PyMast
        
        self.gui_dropdown("val1,val2", value)
        # Handle change in on_message



Face
=================================


.. tabs::
    .. code-tab:: mast
        
        face var

    .. code-tab:: py PyMast
        
        self.gui_face("Face Text")



Slider
=================================


.. tabs::
    .. code-tab:: mast
        
        intslider var low high value
        slider var low high value

    .. code-tab:: py PyMast
        
        def gui_slider (self, val, low, high, show_number=True, label=None, style=None):
        self.gui_slider("Face Text")


Radio buttons
=================================


.. tabs::
    .. code-tab:: mast
        
        radio var "b1, b2, b3"
        vradio var "b1, b2, b3"

    .. code-tab:: py PyMast
        
        self.gui_radio("b1, b2, b3")
        self.gui_radio("b1, b2, b3", True)
    



Ship
=================================


.. tabs::
    .. code-tab:: mast
        
        ship val # this isn't support when write this
        ship "val"

    .. code-tab:: py PyMast
        
        self.gui_ship(ship)


Image
=================================


.. tabs::
    .. code-tab:: mast
        
        ship val # this isn't support when write this
        ship "val"

    .. code-tab:: py PyMast
        
        self.gui_image(file, color)



Sprite
=================================

This doesn't exists as I write this

.. tabs::
    .. code-tab:: mast
        
        sprite val # this isn't support when write this
        

    .. code-tab:: py PyMast
        
        self.gui_sprite(ship, x,y, w,h)


Full console
=================================

For building console widget by widget. 
Call this to specify which console.

.. tabs::
    .. code-tab:: mast
        
        console "helm"
        console var
        

    .. code-tab:: py PyMast
        
        self.gui_console("helm")


 

Activate console
=================================

For building console widget by widget. 
Call this to specify which console.

.. tabs::
    .. code-tab:: mast
        
        console activate "helm"
        

    .. code-tab:: py PyMast
        
        self.gui_activate_console("helm")

Layout console widget
=================================


.. tabs::
    .. code-tab:: mast
        
        console widget "2dview"
        

    .. code-tab:: py PyMast
        
        self.gui_console_widget("2dview")


Layout console widget
=================================


.. tabs::
    .. code-tab:: mast
        
        widget_list "norm_helm"  "2dview^throttle"
        

    .. code-tab:: py PyMast
        
        self.gui_console_widget+list("norm_helm", "2dview^throttle")
        


Layout python coded widget
=================================


.. tabs::
    .. code-tab:: mast
        
        gui control func()
        

    .. code-tab:: py PyMast
        
        self.gui_content(listbox())
        

