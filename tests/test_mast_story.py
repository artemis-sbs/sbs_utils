from sbs_utils.mast.mast import Mast
from sbs_utils.mast.maststory import MastStory, ButtonControl
import unittest

Mast.enable_logging()


def mast_story_compile(code=None):
    mast = MastStory()
    errors = mast.compile(code)
    return (errors, mast)

def mast_story_compile_file(code=None):
    mast = MastStory()
    errors = mast.from_file(code)
    return (errors, mast)




    
    

class TestMastStoryCompile(unittest.TestCase):
    def test_compile_on_change_no_err(self):
        (errors, mast)= mast_story_compile( code = """
on change enemy_count:
   jump label
end_on
 
on change len(role(players)):
   jump label
end_on
""")
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)


    def test_compile_no_err(self):
        (errors, mast)= mast_story_compile( code = """
await gui

await gui timeout 5s

input name "enter name"

await choice:
    + "Start Mission" if started==False:
    ~~ sbs.resume_sim()~~
    + "Resume Mission" if started==True:
    ~~ sbs.resume_sim() ~~
end_await

await choice:
    * "Button one":
        -> JumpLabel
    + "Button Two":
        -> JumpLabel
    + "Button Jump":
timeout  1m 1s:
    -> JumpSomeWhere
end_await


await choice:
* "Button one":
    await choice:
    * "Button one":
        await choice:
        * "Button one":
            -> JumpLabel
        end_await
    end_await
end_await

style .button="padding:3px;"
style .face="padding:2px;"

style fred = "area:1,2,3,4;"
style barney="area: 1,2,3-1px,4;"
style wilma="area:1,2,3,4;row-height:10px;"

section style="area:1,2,3,4;"

section style="area: 1,2,3-1px,4;"

section style="area:1,2,3,4;row-height:10px;"

section style=fred



radio var "helm,weapons,science"
vradio var "helm,weapons,science"

console helm
console clear
console console_name


""")
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)

    
    def test_compile_file_ttt(self):
        (errors, mast) = mast_story_compile_file( code ="tests/mast/ttt.mast")     
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)

    def test_compile_file_bar(self):
        (errors, mast) = mast_story_compile_file( code ="tests/mast/bar.mast")     
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)

    def test_compile_file_gui(self):
        (errors, mast) = mast_story_compile_file( code ="tests/mast/story_gui.mast")     
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)

    def test_compile_no_err_22(self):
        (errors, mast)= mast_story_compile( code = """

=========== server_main =====
section style="area:2,20,18,35;"

button "Speak":
    log "{fred}"
    ->server_main
end_button
row
slider fred "low:0;high:5"


await choice:
    + "{x}" for x in range(3):
        log "well test"
end_await

await choice:
    + "Test" if y == 2:
        log "well test"
end_await

await choice:
    + "{x}" for x in range(3) if s==3:
        log "well test"
end_await

await choice:
    + "{x}" if s==3:
        log "well test"
    + "{x}" for x in range(3) if s==3:
        log "well test"
    + "Test":
        log "well test"
end_await

->END


""")
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)

    def test_weird(self):
        (errors,  _) = mast_story_compile( code = """
#import grid_editor.mast

reroute server server_start
reroute clients client_start_once


===== add_menu =====

#section style="area:10, 0, 30, 45px;"
dropdown menu 'text  Editor; list grid,character;':
end_dropdown

on change menu.value:
#    sel = menu.value
    #
    if menu == "grid":
        jump grid_editor_client_start
#        case "character":
#            jump character_editor_client_start
    end_if
end_on 

""")
        assert(len(errors)==0)

if __name__ == '__main__':
    try:
        unittest.main(exit=False)
    except Exception as e:
        print(e.msg)

