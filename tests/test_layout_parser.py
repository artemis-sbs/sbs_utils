from email import parser
import unittest
from sbs_utils.mast.parsers import LayoutAreaParser


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
        assert(len(asts)== 1)


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
        
    