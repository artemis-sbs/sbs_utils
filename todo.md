
v1.4.0
* Shared media - phase 5, the icon sheet. Carried over from MEDIA_PLAN.md when it was
  deleted (phases 1-4 and 6 shipped; mechanism is documented in
  mkdocs/docs/build/shared-media.md and cosmos/gui_icons.md).
  Draw media/LegendaryMissions/icons/quest-sheet.png - an 8x8 grid of 64px WHITE
  silhouettes. Color is applied per use, so one glyph serves every state and a small
  sheet goes a long way. It ships in LM's media pack, so every mission that already
  declares the pack gets the icons free. The consumers (quest log) are already built and
  fall back to a plain pip, so this is additive.
  Three questions still open from that plan:
  - Who unpacks today? If the engine unpacks resources.media into the mission folder at
    load, it keeps doing so and we get both copies until the consumer stops declaring it.
  - Is resources.media a single string or a list? It is a string in every story.json here.
    If single-valued, a separate icons pack would COMPETE with LM's rather than add to it,
    which is the argument for icons living inside LM's pack.
  - Does ".." out of data/graphics survive on every platform the engine ships on? The
    probe answered it for one machine only.
  Also unverified: skybox and music from a pack resolve but have never been opened by the
  engine.

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


