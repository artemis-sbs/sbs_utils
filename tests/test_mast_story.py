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
    
    def test_compile_no_err(self):
        (errors, mast)= mast_story_compile( code = """
await gui

await gui timeout 5s

input name "enter name"

await choice timeout 1m 1s:
    * "Button one":
        -> JumpLabel
    + "Button Two":
        -> JumpLabel
    + "Button Jump": 
    timeout:
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

style area:1,2,3,4;
style area: 1,2,3-1px,4;
style area:1,2,3,4;row-height:10px;


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


if __name__ == '__main__':
    try:
        unittest.main(exit=False)
    except Exception as e:
        print(e.msg)

