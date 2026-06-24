
v1.4.0
* Expose more useful Python builtins in the MAST eval globals (sbs_utils/mast/mast_globals.py).
  Currently missing: dict, zip, enumerate (and likely others). Today scripts must
  work around these with list methods (e.g. ids[items.index(it)] instead of dict(zip(...))).
  Add them (with a test) so inline Python in MAST is less surprising. Note: {...}
  dict literals already work (syntax, not the dict builtin). Widens eval surface a bit.
  Candidates: dict, zip, enumerate, tuple, round, sum, any, all, bool, float, sorted(already), zip.


General
* Handle Docking
* Handling Grid Items


Mast
* Grid items
* Damage 
* Docking


Routing types:

    * Comms
    * GridComms
    * Science
    * ChangeConsole
    * Spawn (Setup state+Start AI)
    Damage
    Destroy?
    Gui?







        Text,
        AppendText,
        Choose,
        Disconnect,
        OnChange,
        OnClick,
        AwaitGui,
        AwaitSelect,
        Refresh,
        Update
        Comms,
        Scan,
        ScanTab,
        ScanResult






        Route,
            FollowRoute,
            TransmitReceive,
            Broadcast,
            CommsInfo,
            Button,
            Simulation,
#            Face,
#            Ship,
#            Icon,
            GuiContent,
#            Blank,
#            Hole,
#            Section,
            Style,

            ButtonControl,
            RerouteGui,
            SliderControl,
            CheckboxControl,
            RadioControl,
            DropdownControl,
            ImageControl,
            TextInputControl,
            WidgetList,
            Console,
            BuildaConsole,


