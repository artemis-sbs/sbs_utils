from email import parser
import unittest
from sbs_utils.mast.parsers import LayoutAreaParser, StyleDefinition
from sbs_utils.pages.layout.text_area import TextArea


class TestLayoutParser(unittest.TestCase):
    
    
    def test_lex(self):
        tokens = LayoutAreaParser.lex("20,20,30,40px")
        assert(len(tokens)== 8)
        tokens = LayoutAreaParser.lex("20-10,(20+15px)*3,30,40")
        assert(len(tokens)== 16)
        tokens = LayoutAreaParser.lex("min(30,20)")
        assert(len(tokens)== 7)


    def test_parse(self):
        tokens = LayoutAreaParser.lex("20,20,30,40px")
        asts = LayoutAreaParser.parse_list(tokens)
        assert(len(asts)== 4)
        tokens = LayoutAreaParser.lex("20-10,(20+15px)*3,30,40")
        asts = LayoutAreaParser.parse_list(tokens)
        assert(len(asts)== 4)
        tokens = LayoutAreaParser.lex("min(30,20)")
        asts = LayoutAreaParser.parse_e2(tokens)
        assert(asts.token_type == "min")


    def test_compute(self):
        self.do_compute("20,20,30,40px", [20,20,30,(40/500)*100])
        self.do_compute("100-400px,20,30,40px", [100-(400/500)*100,20,30,(40/500)*100])

        self.do_compute("2*x,2*x,3*x,x*40px", [10,10,15,5*(40/500)*100], {"x": 5})

        tokens = LayoutAreaParser.lex("min(30,20)")
        ast = LayoutAreaParser.parse_e2(tokens)
        v = LayoutAreaParser.compute(ast,None, 500)
        assert(v==20)
        tokens = LayoutAreaParser.lex("max(30,20)")
        ast = LayoutAreaParser.parse_e2(tokens)
        v = LayoutAreaParser.compute(ast,None, 500)
        assert(v==30)
        

    def do_compute(self, source, expected, vars=None):
        if vars is None:
            vars = {}
        tokens = LayoutAreaParser.lex(source)
        asts = LayoutAreaParser.parse_list(tokens)
        for i, ast in enumerate(asts):
            test = LayoutAreaParser.compute(ast, vars, 500)
            expect = expected[i]
            assert(test == expect)
        
    
class TestTextAreaParser(unittest.TestCase):
    
    
    def test_style(self):
        ta = TextArea("1", "[](style:font:gui-2;) Hello")
        s = ta.parse_style_line("font:gui-1")
        assert(s.get("style") == "font:gui-1;" )
        ta.calc_rich(0)


        
        




class TestRowHeightColWidthArithmetic(unittest.TestCase):
    """`row-height` / `col-width` must parse whole expressions.

    They were wired to parse_e2, which handles only * and /, so a `+` or `-`
    term was lexed and then SILENTLY DROPPED -- `1em+10px` computed to exactly
    `1em`, and `col-width: 62-25px` to exactly `62`. No error, no warning.
    LegendaryMissions' document screen had been running with a column 25px wider
    than it asked for, and LM's mission-picker title could not be given room for
    its own padding because the `+10px` evaporated.

    `area:` was always fine -- it goes through parse_list -> parse_e. These two
    entry points were simply wired to the wrong level of the grammar.
    """

    AR_Y = 768
    FONT = 28          # gui-3

    def _px(self, expr):
        ast = StyleDefinition.parse_height(expr)
        pct = LayoutAreaParser.compute(ast, None, self.AR_Y, self.FONT)
        return round(pct / 100 * self.AR_Y, 1)

    def test_addition_is_not_dropped(self):
        self.assertEqual(self._px("1em"), 28.0)
        self.assertEqual(self._px("1em+10px"), 38.0)

    def test_subtraction_is_not_dropped(self):
        self.assertEqual(self._px("100px-25px"), 75.0)

    def test_em_keeps_its_font_size_inside_an_expression(self):
        """font_size used to be dropped on recursion, so an `em` anywhere but at
        the top of an expression fell back to the default 20."""
        self.assertEqual(self._px("1em+10px"), 38.0)      # 28 + 10, not 20 + 10
        self.assertEqual(self._px("min(2em,1000)"), 56.0)  # 2*28, not 2*20

    def test_existing_forms_are_unchanged(self):
        self.assertEqual(self._px("50"), 384.0)           # bare percent
        self.assertEqual(self._px("10px"), 10.0)
        self.assertEqual(self._px("2em"), 56.0)
        self.assertEqual(self._px("2*3em"), 168.0)
        self.assertEqual(self._px("min(10,20)"), 76.8)

    def test_col_width_takes_the_same_path(self):
        ast = StyleDefinition.parse_width("62-25px")
        pct = LayoutAreaParser.compute(ast, None, 1024, self.FONT)
        self.assertAlmostEqual(pct, 62 - (25 / 1024 * 100), places=4)
