# Changelog


## 7.8

- Made Mast globals illegal as variable name e.g. max = 2 is an error (Added test)
- made sbs, sim as globals (sim is still set in schedulers, but this makes it an illegal variable name)
- the newline character is no longer valid whitespace for (most) commands, was always wrong to include it
- Added the setting Mast.include_code to cache the mast code to improve error messages
- fixed 'unlink' / removing links
- grid objects target pos
- reroute gui tasks
- on change processing

