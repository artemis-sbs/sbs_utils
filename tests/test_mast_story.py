from sbs_utils.mast.mast import Mast
from sbs_utils.mast.maststory import MastStory
import unittest
from sbs_utils.agent import clear_shared

Mast.enable_logging()


def mast_story_compile(code=None):
    mast = MastStory()
    clear_shared()
    errors = mast.compile(code, "test")
    return (errors, mast)

def mast_story_compile_file(code=None):
    mast = MastStory()
    clear_shared()
    errors = mast.from_file(code)
    return (errors, mast)




    
    

class TestMastStoryCompile(unittest.TestCase):
    def test_compile_on_change_no_err(self):
        (errors, mast)= mast_story_compile( code = """
on change enemy_count:
   jump label

 
on change len(role(players)):
   jump label

""")
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)


    def test_compile_no_err(self):
        (errors, mast)= mast_story_compile( code = """
await gui()

await gui(timeout=timeout(5))

gui_input("enter name")

await gui():
    + "Start Mission" if started==False:
    ~~ sbs.resume_sim()~~
    + "Resume Mission" if started==True:
    ~~ sbs.resume_sim() ~~


await gui():
    * "Button one":
        -> JumpLabel
    + "Button Two":
        -> JumpLabel
    + "Button Jump":
    =timeout():
        -> JumpSomeWhere



await gui():
* "Button one":
    await gui():
    * "Button one":
        await gui():
        * "Button one":
            -> JumpLabel

gui_style("padding:3px;", ".button")
gui_style("padding:2px;", ".face")

gui_style("area:1,2,3,4;", "fred")
gui_style("area: 1,2,3-1px,4;", "barney")
gui_style("area:1,2,3,4;row-height:10px;", "wilma")

gui_section(style="area:1,2,3,4;")

gui_section(style="area: 1,2,3-1px,4;")

gui_section(style="area:1,2,3,4;row-height:10px;")

gui_section(style=fred)



gui_radio( "helm,weapons,science", var=" var")
gui_vradio( "helm,weapons,science", var=" var")

console("helm")
console("clear")
console("console_name")


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
        # NOTE: Currently fails because of colon in string
        assert(len(errors) == 0)

    def test_compile_no_err_22(self):
        (errors, mast)= mast_story_compile( code = """

=========== server_main =====
gui_section(style="area:2,20,18,35;")

on gui_message(gui_button("Speak")):
    log("{fred}")
    ->server_main

gui_row()
gui_slider("low:0;high:5", var="fred") 


await gui():
    + "{x}" for x in range(3):
        log("well test")


await gui():
    + "Test" if y == 2:
        log("well test")


await gui():
    + "{x}" for x in range(3) if s==3:
        log("well test")


await gui():
    + "{x}" if s==3:
        log("well test")
    + "{x}" for x in range(3) if s==3:
        log("well test")
    + "Test":
        log("well test")

->END


""")
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)

    def test_weird(self):
        (errors,  _) = mast_story_compile( code = """
#import grid_editor.mast

reroute_server(server_start)
reroute_clients(client_start_once)


===== add_menu =====

#section style="area:10, 0, 30, 45px;"
gui_dropdown('text  Editor; list grid,character;', var="menu")


on change menu.value:
#    sel = menu.value
    #
    if menu == "grid":
        jump grid_editor_client_start
#        case "character":
#            jump character_editor_client_start
    

""")
        assert(len(errors)==0)

if __name__ == '__main__':
    try:
        unittest.main(exit=False)
    except Exception as e:
        print(e.msg)

