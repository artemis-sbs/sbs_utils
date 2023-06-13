# Changelog


## 7.9
- PyMast routing
* PyMast Reroute gui
- query.has_link_to
- follow route to force a route e.g. force science scan
- Routes now check so they don't schedule multiple times (For selections)


## 7.8

- Made Mast globals illegal as variable name e.g. max = 2 is an error (Added test)
- made sbs, sim as globals (sim is still set in schedulers, but this makes it an illegal variable name)
- the newline character is no longer valid whitespace for (most) commands, was always wrong to include it
- Added the setting Mast.include_code to cache the mast code to improve error messages
- fixed 'unlink' / removing links
- grid objects target pos
- reroute gui tasks
- on change processing

