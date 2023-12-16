Engine Interactions
########################


Target,
Tell,
Broadcast,
Comms,






Await Comms
=================================

.. tabs::
    .. code-tab:: mast
        
        await comms:
            + "Hail":
                have self tell player "{comms_id}! We will destroy you, disgusting Terran scum!"
            + "You're Ugly":
                have self tell player  """You are a foolish Terran, {comms_id}.  We know that the taunt functionality is not currently implemented.^"""
            + "Surrender now":
                have self tell player """OK we give up, {comms_id}."""
        end_await

        

    .. code-tab:: py PyMast
        
            self.await_comms({
                "Hail": self.comms_station_hail,
                "Build Homing": self.comms_build_homing,
                "Build Nuke": self.comms_build_nuke,
                "Build EMP": self.comms_build_emp,
                "Build Mine": self.comms_build_mine,
            })

        

        



