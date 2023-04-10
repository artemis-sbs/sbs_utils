Behavior Components
###############################


Sequence
=================================

.. tabs::
    .. code-tab:: mast

        bt seq label1 & label2

    .. code-tab:: py PyMast
        
        self.behave_seq (label1, label2):

Select
=================================

.. tabs::
    .. code-tab:: mast

        bt  sel label1 | label2

    .. code-tab:: py PyMast
        
        self.behave_seq (label1, label2):

Until
=================================

.. tabs::
    .. code-tab:: mast

        bt until my_label
        bt until fail my_label

    .. code-tab:: py PyMast
        
        self.behave_until (my_label)
        self.behave_until (my_label, PollResults.OK_END)
        self.behave_until (my_label, PollResults.OK_FAIL)
        

Invert
=================================

.. tabs::
    .. code-tab:: mast

        bt invert my_label

    .. code-tab:: py PyMast
        
        self.behave_invert (my_label):
        

yield
=================================

.. tabs::
    .. code-tab:: mast

        yield FAIL
        yield SUCCESS

    .. code-tab:: py PyMast
        
        yield PollResults.BT_FAIL
        yield PollResults.BT_SUCCESS
        








