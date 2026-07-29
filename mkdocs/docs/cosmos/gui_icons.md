# Icons by name

Cosmos ships an icon sheet, and until now the only way to reach it was the cell number:

```python
gui_icon("icon_index:111;color:#cc0;")     # ...which one is 111?
```

Nobody remembers 111, nothing can check it, and a mission that wants its *own* art has
to find and edit every screen that draws one. So every glyph now has a name:

```python
gui_icon_name("wanted", "#cc0")            # the same icon
gui_icon_name("quest.job", "#cc0")         # better: say what it MEANS
```

## A look, or a meaning

There are two kinds of name, and the difference is the whole point.

| | example | what it is |
|---|---|---|
| **A look** | `square`, `wanted`, `bell`, `sitemap` | one per drawn cell — what the glyph *is* |
| **A meaning** | `quest.job`, `quest.state`, `list.expand` | an alias onto a look — what it's *for* |

Ask for the **meaning** wherever you can. `quest.job` says why the icon is there;
`wanted` only says what it looks like today. Re-point the meaning once and every screen
drawing it changes together.

```python
from sbs_utils.procedural.gui.icon_sheet import ICON_ALIAS
ICON_ALIAS["quest.job"] = "flag"           # every quest log now flags its jobs
```

The meanings that ship:

| meaning | look | used for |
|---|---|---|
| `quest.arc` | `sitemap` | the heading over a run of beats |
| `quest.job` | `wanted` | work posted for someone to take |
| `quest.objective` | `flag` | something the crew is to do |
| `quest.beat` | `talks` | a moment they live through |
| `quest.cue` | `bell` | a stage direction; fires unseen |
| `quest.state` | `square` | the state pip, recolored per state |
| `check.on` / `check.off` | `square` / `square-outline` | a checked and an unchecked row |
| `list.expand` / `list.collapse` | `expand` / `collapse` | a fold that opens or closes |
| `list.prev` / `list.next` | `rewind` / `forward` | paging through a list |

## Color is per use, not per icon

Every built-in glyph is **white on transparent**, so one glyph serves every state — pass
the color at the point of drawing:

```python
for quest in quests:
    gui_icon_name("quest.state", "#6d6" if quest.done else "#888")
```

## Bring your own sheet

A name is not tied to the built-in sheet. Claim the **look** for a cell of your own and
it wins over the built-in index:

```python
from sbs_utils.procedural.gui import gui_icon_add_atlas
from sbs_utils.procedural.media_paths import media_shared

# One 64px cell out of your own sheet, claiming the name "wanted".
gui_icon_add_atlas("wanted", media_shared("icons/quest-sheet"), 0, 0, 64, 64)
```

From then on every `gui_icon_name("quest.job")` in the game draws *your* art — **with no
edit to the code that draws it**. That is what lets a screen be written before its art
exists, and lets an add-on re-skin screens it doesn't own.

Or claim a whole sheet at once, laid out row-major:

```python
gui_icon_add_atlas_grid(media_shared("icons/quest-sheet"), 8, 8,
                        ["wanted", "flag", "talks", None, "bell"], cell=64)
```

!!! warning "Claiming a look has to be deliberate"
    `gui_icon_add_atlas` is `gui_image_add_atlas(..., domain="icon")`, and only the icon
    domain re-skins. A plain `gui_image_add_atlas("square", ...)` — a perfectly ordinary
    thing to call an image — does **not** become the icon `square`. Without that scope
    one image registration could silently re-skin every state pip in the game, and the
    author would have no way to know why.

## Icons written as a fact sheet

A sheet is a catalog, and a catalog is what AMD is for. An
[image section](../build/amd-format.md) registers the same keys with no Python at all —
`Sheet`, `Cell` and the domain are written once on the section, so an entry is one line:

```amd
## [Icons](icons)
---
icons
Sheet: icons/quest-sheet
Cell: 64
---
The quest log's glyphs. White silhouettes - color is applied per use.

### [Job](wanted)
---
At: 0, 0
---

### [Beat](talks)
---
At: 1, 0
Color: #888
---
```

```python
images_load_amd("icons.amd")     # or images_declare_document(doc) for a section of a bigger file
```

A section whose kind noun is `icons` registers in the icon domain — so those keys are
looks. Any other word (`images`, `art`, `atlas`) registers ordinary atlas keys, which is
what a card deck or a set of console backdrops wants:

```amd
## [Cards](cards)
---
images
Sheet: casino/terran_deck
Cell: 190, 280
Domain: casino
---

### [Back](card_back)
---
At: 0, 0
---
```

`sbs lint` checks these: a sheet that is not on disk, an `At:` with no `Cell:` to measure
against, and a cell that falls off the edge of the sheet. All three draw a blank widget
today with no error anywhere.

!!! tip "Where a custom sheet should live"
    Put it in a **[shared media pack](../build/shared-media.md)** rather than in each
    mission that draws it. `media_shared()` finds it wherever it was unpacked, so the
    same call works in a clone and in a fetched copy.

## Sub-rects are pixels

When you cut cells out of your own sheet, `gui_image_add_atlas(key, file, l, t, r, b)`
takes **pixel** coordinates, not 0–1 texture coordinates. A 64px grid is
`(col*64, row*64, (col+1)*64, (row+1)*64)`.

## Things worth knowing

- **An unknown name draws nothing** and logs a warning once, rather than falling back to
  some arbitrary glyph. A wrong icon is worse than a missing one, because it looks
  deliberate.
- **Both backings lay out the same.** A built-in name goes out as an engine icon; a
  custom one goes out as an image (the engine has no icon concept for art it didn't
  ship). Both are square columns sized off the row height, so re-skinning a name cannot
  shift a layout.
- **`click_tag` works on the built-in path only** today. A clickable icon whose name may
  be re-skinned isn't supported yet — use `gui_icon` directly if you need the click.
- `icon_names()` lists everything that resolves; `icon_resolve(name)` returns
  `(icon_index, atlas_key)` with exactly one of the two set.

## The whole sheet

176 named glyphs. The number after each name is the raw `icon_index`, in case you're
reading older code that used it. Names in italics are meanings that point at that look.

<style>
.icon-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(6.5rem, 1fr));
             gap: .4rem; margin: .8rem 0 1.4rem; }
.icon-grid figure { margin: 0; padding: .45rem .2rem; border-radius: .35rem;
                    background: #23272e; text-align: center; }
.icon-grid i { display: block; width: 40px; height: 40px; margin: 0 auto .3rem;
               /* TWO levels up, and it has to be counted from the built URL rather
                  than from this file. MkDocs rewrites relative links in MARKDOWN but not
                  inside a style block, and with directory URLs the page is served at
                  /cosmos/gui_icons/ - so `../media` resolved to /cosmos/media and every
                  tile was blank on the site. (`fix_url` computes from the SOURCE depth,
                  which is the same off-by-one.) Relative, not /media, so it still works
                  where the site is served under a subpath, as GitHub Pages does. */
               background-image: url(../../media/icon-sheet.png);
               background-size: 2000% 900%; background-repeat: no-repeat; }
.icon-grid figcaption { font-size: .68rem; line-height: 1.25; color: #dfe4ec;
                        word-break: break-word; }
.icon-grid figcaption span { display: block; color: #8b94a3; }
.icon-grid figcaption em { display: block; color: #7fb2e5; font-style: normal; }
</style>

<!-- BEGIN generated gallery -->

### Science & space
<div class="icon-grid" markdown="0">
<figure><i style="background-position:0.0000% 0.0000%"></i><figcaption>atom<span>0</span></figcaption></figure>
<figure><i style="background-position:5.2632% 0.0000%"></i><figcaption>wheel<span>1</span></figcaption></figure>
<figure><i style="background-position:10.5263% 0.0000%"></i><figcaption>propeller<span>2</span></figcaption></figure>
<figure><i style="background-position:15.7895% 0.0000%"></i><figcaption>swirl<span>3</span></figcaption></figure>
<figure><i style="background-position:21.0526% 0.0000%"></i><figcaption>magnet<span>4</span></figcaption></figure>
<figure><i style="background-position:26.3158% 0.0000%"></i><figcaption>brain<span>5</span></figcaption></figure>
<figure><i style="background-position:31.5789% 0.0000%"></i><figcaption>trefoil<span>6</span></figcaption></figure>
<figure><i style="background-position:36.8421% 0.0000%"></i><figcaption>vortex<span>7</span></figcaption></figure>
<figure><i style="background-position:42.1053% 0.0000%"></i><figcaption>pinwheel<span>8</span></figcaption></figure>
<figure><i style="background-position:47.3684% 0.0000%"></i><figcaption>rings<span>9</span></figcaption></figure>
<figure><i style="background-position:57.8947% 0.0000%"></i><figcaption>satellite-dish<span>11</span></figcaption></figure>
<figure><i style="background-position:63.1579% 0.0000%"></i><figcaption>gem<span>12</span></figcaption></figure>
<figure><i style="background-position:68.4211% 0.0000%"></i><figcaption>globe<span>13</span></figcaption></figure>
<figure><i style="background-position:78.9474% 0.0000%"></i><figcaption>waveform<span>15</span></figcaption></figure>
<figure><i style="background-position:89.4737% 0.0000%"></i><figcaption>ram<span>17</span></figcaption></figure>
<figure><i style="background-position:47.3684% 12.5000%"></i><figcaption>radioactive<span>29</span></figcaption></figure>
<figure><i style="background-position:52.6316% 12.5000%"></i><figcaption>honeycomb<span>30</span></figcaption></figure>
<figure><i style="background-position:21.0526% 25.0000%"></i><figcaption>triskelion<span>44</span></figcaption></figure>
<figure><i style="background-position:57.8947% 25.0000%"></i><figcaption>asteroid<span>51</span></figcaption></figure>
<figure><i style="background-position:73.6842% 25.0000%"></i><figcaption>molecule<span>54</span></figcaption></figure>
<figure><i style="background-position:15.7895% 37.5000%"></i><figcaption>microscope<span>63</span></figcaption></figure>
<figure><i style="background-position:21.0526% 37.5000%"></i><figcaption>specimen<span>64</span></figcaption></figure>
<figure><i style="background-position:26.3158% 75.0000%"></i><figcaption>reactor<span>125</span></figcaption></figure>
<figure><i style="background-position:94.7368% 75.0000%"></i><figcaption>dome<span>138</span></figcaption></figure>
<figure><i style="background-position:100.0000% 75.0000%"></i><figcaption>fallout<span>139</span></figcaption></figure>
<figure><i style="background-position:100.0000% 87.5000%"></i><figcaption>globe-grid<span>159</span></figcaption></figure>
</div>

### Ship systems & engineering
<div class="icon-grid" markdown="0">
<figure><i style="background-position:100.0000% 0.0000%"></i><figcaption>sawblade<span>19</span></figcaption></figure>
<figure><i style="background-position:0.0000% 12.5000%"></i><figcaption>recycle<span>20</span></figcaption></figure>
<figure><i style="background-position:5.2632% 12.5000%"></i><figcaption>capsule<span>21</span></figcaption></figure>
<figure><i style="background-position:42.1053% 12.5000%"></i><figcaption>gears<span>28</span></figcaption></figure>
<figure><i style="background-position:78.9474% 12.5000%"></i><figcaption>battery<span>35</span></figcaption></figure>
<figure><i style="background-position:78.9474% 25.0000%"></i><figcaption>gear<span>55</span></figcaption></figure>
<figure><i style="background-position:84.2105% 25.0000%"></i><figcaption>gear-solid<span>56</span></figcaption></figure>
<figure><i style="background-position:89.4737% 25.0000%"></i><figcaption>gears-two<span>57</span></figcaption></figure>
<figure><i style="background-position:94.7368% 25.0000%"></i><figcaption>maintenance<span>58</span></figcaption></figure>
<figure><i style="background-position:100.0000% 25.0000%"></i><figcaption>turbine<span>59</span></figcaption></figure>
<figure><i style="background-position:0.0000% 37.5000%"></i><figcaption>factory<span>60</span></figcaption></figure>
<figure><i style="background-position:5.2632% 37.5000%"></i><figcaption>pipes<span>61</span></figcaption></figure>
<figure><i style="background-position:10.5263% 37.5000%"></i><figcaption>press<span>62</span></figcaption></figure>
<figure><i style="background-position:26.3158% 37.5000%"></i><figcaption>device<span>65</span></figcaption></figure>
<figure><i style="background-position:31.5789% 37.5000%"></i><figcaption>damaged<span>66</span></figcaption></figure>
<figure><i style="background-position:36.8421% 37.5000%"></i><figcaption>gear-ring<span>67</span></figcaption></figure>
<figure><i style="background-position:42.1053% 37.5000%"></i><figcaption>circuit<span>68</span></figcaption></figure>
<figure><i style="background-position:47.3684% 37.5000%"></i><figcaption>circuit-maze<span>69</span></figcaption></figure>
<figure><i style="background-position:52.6316% 37.5000%"></i><figcaption>mechanism<span>70</span></figcaption></figure>
<figure><i style="background-position:68.4211% 62.5000%"></i><figcaption>forge<span>113</span></figcaption></figure>
<figure><i style="background-position:73.6842% 62.5000%"></i><figcaption>fountain<span>114</span></figcaption></figure>
<figure><i style="background-position:78.9474% 62.5000%"></i><figcaption>elevator<span>115</span></figcaption></figure>
</div>

### Combat
<div class="icon-grid" markdown="0">
<figure><i style="background-position:84.2105% 12.5000%"></i><figcaption>turret<span>36</span></figcaption></figure>
<figure><i style="background-position:100.0000% 12.5000%"></i><figcaption>lightning<span>39</span></figcaption></figure>
<figure><i style="background-position:0.0000% 25.0000%"></i><figcaption>bullets<span>40</span></figcaption></figure>
<figure><i style="background-position:5.2632% 25.0000%"></i><figcaption>bullets-plus<span>41</span></figcaption></figure>
<figure><i style="background-position:10.5263% 25.0000%"></i><figcaption>bullet-plus<span>42</span></figcaption></figure>
<figure><i style="background-position:15.7895% 25.0000%"></i><figcaption>bullseye<span>43</span></figcaption></figure>
<figure><i style="background-position:26.3158% 25.0000%"></i><figcaption>flame<span>45</span></figcaption></figure>
<figure><i style="background-position:47.3684% 25.0000%"></i><figcaption>spider<span>49</span></figcaption></figure>
<figure><i style="background-position:63.1579% 25.0000%"></i><figcaption>fighter<span>52</span></figcaption></figure>
<figure><i style="background-position:68.4211% 25.0000%"></i><figcaption>fist<span>53</span></figcaption></figure>
<figure><i style="background-position:78.9474% 37.5000%"></i><figcaption>cavalry<span>75</span></figcaption></figure>
<figure><i style="background-position:84.2105% 37.5000%"></i><figcaption>valkyrie<span>76</span></figcaption></figure>
<figure><i style="background-position:89.4737% 37.5000%"></i><figcaption>knight<span>77</span></figcaption></figure>
<figure><i style="background-position:94.7368% 37.5000%"></i><figcaption>goblin<span>78</span></figcaption></figure>
<figure><i style="background-position:63.1579% 62.5000%"></i><figcaption>crosshair<span>112</span></figcaption></figure>
<figure><i style="background-position:89.4737% 62.5000%"></i><figcaption>rifle<span>117</span></figcaption></figure>
<figure><i style="background-position:52.6316% 100.0000%"></i><figcaption>skull<span>170</span></figcaption></figure>
<figure><i style="background-position:57.8947% 100.0000%"></i><figcaption>skull-horned<span>171</span></figcaption></figure>
<figure><i style="background-position:63.1579% 100.0000%"></i><figcaption>sword<span>172</span></figcaption></figure>
<figure><i style="background-position:68.4211% 100.0000%"></i><figcaption>helm-spartan<span>173</span></figcaption></figure>
</div>

### People
<div class="icon-grid" markdown="0">
<figure><i style="background-position:89.4737% 12.5000%"></i><figcaption>squad<span>37</span></figcaption></figure>
<figure><i style="background-position:31.5789% 25.0000%"></i><figcaption>teleport<span>46</span></figcaption></figure>
<figure><i style="background-position:36.8421% 25.0000%"></i><figcaption>run<span>47</span></figcaption></figure>
<figure><i style="background-position:57.8947% 37.5000%"></i><figcaption>muscle<span>71</span></figcaption></figure>
<figure><i style="background-position:63.1579% 37.5000%"></i><figcaption>robot<span>72</span></figcaption></figure>
<figure><i style="background-position:68.4211% 37.5000%"></i><figcaption>king<span>73</span></figcaption></figure>
<figure><i style="background-position:73.6842% 37.5000%"></i><figcaption>hero<span>74</span></figcaption></figure>
<figure><i style="background-position:100.0000% 37.5000%"></i><figcaption>walk<span>79</span></figcaption></figure>
<figure><i style="background-position:0.0000% 50.0000%"></i><figcaption>crowd<span>80</span></figcaption></figure>
<figure><i style="background-position:5.2632% 50.0000%"></i><figcaption>gauntlet<span>81</span></figcaption></figure>
<figure><i style="background-position:10.5263% 50.0000%"></i><figcaption>portrait<span>82</span></figcaption></figure>
<figure><i style="background-position:15.7895% 50.0000%"></i><figcaption>person<span>83</span></figcaption></figure>
<figure><i style="background-position:100.0000% 62.5000%"></i><figcaption>bandit<span>119</span></figcaption></figure>
<figure><i style="background-position:57.8947% 75.0000%"></i><figcaption>meeting<span>131</span></figcaption></figure>
<figure><i style="background-position:63.1579% 75.0000%"></i><figcaption>talks<span>132</span><em>quest.beat</em></figcaption></figure>
<figure><i style="background-position:78.9474% 100.0000%"></i><figcaption>handshake<span>175</span></figcaption></figure>
</div>

### Medical
<div class="icon-grid" markdown="0">
<figure><i style="background-position:26.3158% 12.5000%"></i><figcaption>first-aid<span>25</span></figcaption></figure>
<figure><i style="background-position:21.0526% 50.0000%"></i><figcaption>medic-up<span>84</span></figcaption></figure>
<figure><i style="background-position:26.3158% 50.0000%"></i><figcaption>heart-minus<span>85</span></figcaption></figure>
<figure><i style="background-position:31.5789% 50.0000%"></i><figcaption>heart-plus<span>86</span></figcaption></figure>
<figure><i style="background-position:36.8421% 50.0000%"></i><figcaption>hospital<span>87</span></figcaption></figure>
<figure><i style="background-position:0.0000% 62.5000%"></i><figcaption>medical-cross<span>100</span></figcaption></figure>
<figure><i style="background-position:10.5263% 62.5000%"></i><figcaption>cross-box<span>102</span></figcaption></figure>
<figure><i style="background-position:21.0526% 75.0000%"></i><figcaption>medic-down<span>124</span></figcaption></figure>
<figure><i style="background-position:68.4211% 75.0000%"></i><figcaption>caduceus<span>133</span></figcaption></figure>
</div>

### Places & cargo
<div class="icon-grid" markdown="0">
<figure><i style="background-position:63.1579% 12.5000%"></i><figcaption>supplies<span>32</span></figcaption></figure>
<figure><i style="background-position:42.1053% 25.0000%"></i><figcaption>shell<span>48</span></figcaption></figure>
<figure><i style="background-position:52.6316% 25.0000%"></i><figcaption>hex-cargo<span>50</span></figcaption></figure>
<figure><i style="background-position:42.1053% 50.0000%"></i><figcaption>observatory<span>88</span></figcaption></figure>
<figure><i style="background-position:47.3684% 50.0000%"></i><figcaption>chest-open<span>89</span></figcaption></figure>
<figure><i style="background-position:52.6316% 50.0000%"></i><figcaption>barrel<span>90</span></figcaption></figure>
<figure><i style="background-position:100.0000% 50.0000%"></i><figcaption>chest<span>99</span></figcaption></figure>
<figure><i style="background-position:21.0526% 62.5000%"></i><figcaption>tavern<span>104</span></figcaption></figure>
<figure><i style="background-position:36.8421% 62.5000%"></i><figcaption>home<span>107</span></figcaption></figure>
<figure><i style="background-position:31.5789% 75.0000%"></i><figcaption>container<span>126</span></figcaption></figure>
<figure><i style="background-position:36.8421% 75.0000%"></i><figcaption>chef<span>127</span></figcaption></figure>
<figure><i style="background-position:5.2632% 87.5000%"></i><figcaption>mess<span>141</span></figcaption></figure>
<figure><i style="background-position:10.5263% 87.5000%"></i><figcaption>bunks<span>142</span></figcaption></figure>
<figure><i style="background-position:15.7895% 87.5000%"></i><figcaption>cards<span>143</span></figcaption></figure>
</div>

### Signals, orders & the map
<div class="icon-grid" markdown="0">
<figure><i style="background-position:52.6316% 0.0000%"></i><figcaption>arrow-curve<span>10</span></figcaption></figure>
<figure><i style="background-position:73.6842% 0.0000%"></i><figcaption>tread<span>14</span></figcaption></figure>
<figure><i style="background-position:84.2105% 0.0000%"></i><figcaption>zoom-in<span>16</span></figcaption></figure>
<figure><i style="background-position:94.7368% 0.0000%"></i><figcaption>chevrons-right<span>18</span></figcaption></figure>
<figure><i style="background-position:10.5263% 12.5000%"></i><figcaption>hourglass<span>22</span></figcaption></figure>
<figure><i style="background-position:15.7895% 12.5000%"></i><figcaption>flag<span>23</span><em>quest.objective</em></figcaption></figure>
<figure><i style="background-position:21.0526% 12.5000%"></i><figcaption>hand<span>24</span></figcaption></figure>
<figure><i style="background-position:31.5789% 12.5000%"></i><figcaption>wrench<span>26</span></figcaption></figure>
<figure><i style="background-position:36.8421% 12.5000%"></i><figcaption>shield<span>27</span></figcaption></figure>
<figure><i style="background-position:57.8947% 12.5000%"></i><figcaption>sitemap<span>31</span><em>quest.arc</em></figcaption></figure>
<figure><i style="background-position:68.4211% 12.5000%"></i><figcaption>radar<span>33</span></figcaption></figure>
<figure><i style="background-position:73.6842% 12.5000%"></i><figcaption>antenna<span>34</span></figcaption></figure>
<figure><i style="background-position:63.1579% 50.0000%"></i><figcaption>folder<span>92</span></figcaption></figure>
<figure><i style="background-position:68.4211% 50.0000%"></i><figcaption>satellite<span>93</span></figcaption></figure>
<figure><i style="background-position:73.6842% 50.0000%"></i><figcaption>export<span>94</span></figcaption></figure>
<figure><i style="background-position:78.9474% 50.0000%"></i><figcaption>import<span>95</span></figcaption></figure>
<figure><i style="background-position:84.2105% 50.0000%"></i><figcaption>burst<span>96</span></figcaption></figure>
<figure><i style="background-position:15.7895% 62.5000%"></i><figcaption>claws<span>103</span></figcaption></figure>
<figure><i style="background-position:31.5789% 62.5000%"></i><figcaption>shield-plain<span>106</span></figcaption></figure>
<figure><i style="background-position:42.1053% 62.5000%"></i><figcaption>bishop<span>108</span></figcaption></figure>
<figure><i style="background-position:47.3684% 62.5000%"></i><figcaption>shield-broken<span>109</span></figcaption></figure>
<figure><i style="background-position:52.6316% 62.5000%"></i><figcaption>helm-wheel<span>110</span></figcaption></figure>
<figure><i style="background-position:57.8947% 62.5000%"></i><figcaption>wanted<span>111</span><em>quest.job</em></figcaption></figure>
<figure><i style="background-position:0.0000% 75.0000%"></i><figcaption>stop<span>120</span></figcaption></figure>
<figure><i style="background-position:52.6316% 75.0000%"></i><figcaption>tablet<span>130</span></figcaption></figure>
<figure><i style="background-position:73.6842% 75.0000%"></i><figcaption>phone<span>134</span></figcaption></figure>
<figure><i style="background-position:0.0000% 87.5000%"></i><figcaption>patrol-badge<span>140</span></figcaption></figure>
<figure><i style="background-position:21.0526% 87.5000%"></i><figcaption>python<span>144</span></figcaption></figure>
<figure><i style="background-position:26.3158% 87.5000%"></i><figcaption>bell<span>145</span><em>quest.cue</em></figcaption></figure>
<figure><i style="background-position:31.5789% 87.5000%"></i><figcaption>ship-sail<span>146</span></figcaption></figure>
<figure><i style="background-position:36.8421% 87.5000%"></i><figcaption>acorn<span>147</span></figcaption></figure>
</div>

### Rank pips
<div class="icon-grid" markdown="0">
<figure><i style="background-position:94.7368% 12.5000%"></i><figcaption>chevrons-circle<span>38</span></figcaption></figure>
<figure><i style="background-position:57.8947% 50.0000%"></i><figcaption>rank-star<span>91</span></figcaption></figure>
<figure><i style="background-position:94.7368% 50.0000%"></i><figcaption>rank-3<span>98</span></figcaption></figure>
<figure><i style="background-position:26.3158% 62.5000%"></i><figcaption>rank-2<span>105</span></figcaption></figure>
<figure><i style="background-position:84.2105% 62.5000%"></i><figcaption>rank-1<span>116</span></figcaption></figure>
<figure><i style="background-position:10.5263% 75.0000%"></i><figcaption>rank-down-2<span>122</span></figcaption></figure>
<figure><i style="background-position:15.7895% 75.0000%"></i><figcaption>rank-down<span>123</span></figcaption></figure>
<figure><i style="background-position:42.1053% 75.0000%"></i><figcaption>rank-4<span>128</span></figcaption></figure>
<figure><i style="background-position:78.9474% 75.0000%"></i><figcaption>rank-cone<span>135</span></figcaption></figure>
</div>

### Emblems
<div class="icon-grid" markdown="0">
<figure><i style="background-position:21.0526% 100.0000%"></i><figcaption>emblem-compass<span>164</span></figcaption></figure>
<figure><i style="background-position:26.3158% 100.0000%"></i><figcaption>emblem-diamond<span>165</span></figcaption></figure>
<figure><i style="background-position:31.5789% 100.0000%"></i><figcaption>emblem-hex<span>166</span></figcaption></figure>
<figure><i style="background-position:36.8421% 100.0000%"></i><figcaption>emblem-bars<span>167</span></figcaption></figure>
<figure><i style="background-position:42.1053% 100.0000%"></i><figcaption>emblem-axe<span>168</span></figcaption></figure>
<figure><i style="background-position:47.3684% 100.0000%"></i><figcaption>emblem-blade<span>169</span></figcaption></figure>
<figure><i style="background-position:73.6842% 100.0000%"></i><figcaption>laurel<span>174</span></figcaption></figure>
</div>

### Shapes & widget furniture
<div class="icon-grid" markdown="0">
<figure><i style="background-position:89.4737% 50.0000%"></i><figcaption>circle<span>97</span></figcaption></figure>
<figure><i style="background-position:5.2632% 62.5000%"></i><figcaption>square<span>101</span><em>check.on, quest.state</em></figcaption></figure>
<figure><i style="background-position:94.7368% 62.5000%"></i><figcaption>cursor<span>118</span></figcaption></figure>
<figure><i style="background-position:5.2632% 75.0000%"></i><figcaption>square-outline<span>121</span><em>check.off</em></figcaption></figure>
<figure><i style="background-position:47.3684% 75.0000%"></i><figcaption>circle-outline<span>129</span></figcaption></figure>
<figure><i style="background-position:84.2105% 75.0000%"></i><figcaption>move<span>136</span></figcaption></figure>
<figure><i style="background-position:89.4737% 75.0000%"></i><figcaption>menu<span>137</span></figcaption></figure>
<figure><i style="background-position:42.1053% 87.5000%"></i><figcaption>arrow-up<span>148</span></figcaption></figure>
<figure><i style="background-position:47.3684% 87.5000%"></i><figcaption>arrow-right<span>149</span></figcaption></figure>
<figure><i style="background-position:52.6316% 87.5000%"></i><figcaption>arrow-down<span>150</span></figcaption></figure>
<figure><i style="background-position:57.8947% 87.5000%"></i><figcaption>arrow-left<span>151</span></figcaption></figure>
<figure><i style="background-position:63.1579% 87.5000%"></i><figcaption>rewind<span>152</span><em>list.prev</em></figcaption></figure>
<figure><i style="background-position:68.4211% 87.5000%"></i><figcaption>forward<span>153</span><em>list.next</em></figcaption></figure>
<figure><i style="background-position:73.6842% 87.5000%"></i><figcaption>expand<span>154</span><em>list.expand</em></figcaption></figure>
<figure><i style="background-position:78.9474% 87.5000%"></i><figcaption>collapse<span>155</span><em>list.collapse</em></figcaption></figure>
<figure><i style="background-position:84.2105% 87.5000%"></i><figcaption>plus<span>156</span></figcaption></figure>
<figure><i style="background-position:89.4737% 87.5000%"></i><figcaption>minus<span>157</span></figcaption></figure>
<figure><i style="background-position:94.7368% 87.5000%"></i><figcaption>ban<span>158</span></figcaption></figure>
<figure><i style="background-position:0.0000% 100.0000%"></i><figcaption>magnifier<span>160</span></figcaption></figure>
<figure><i style="background-position:5.2632% 100.0000%"></i><figcaption>magnifier-large<span>161</span></figcaption></figure>
<figure><i style="background-position:10.5263% 100.0000%"></i><figcaption>magnifier-thin<span>162</span></figcaption></figure>
<figure><i style="background-position:15.7895% 100.0000%"></i><figcaption>magnifier-small<span>163</span></figcaption></figure>
</div>

<!-- END generated gallery -->

*Icons from [game-icons.net](https://game-icons.net/). The gallery is generated from
`icon_sheet.py` by `mkdocs/gen_icon_gallery.py` — re-run it after adding a name.*
