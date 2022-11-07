from email import parser
import unittest
from sbs_utils.mast.parsers import LayoutAreaParser


class TestLayoutParser(unittest.TestCase):
    
    
    def test_lex(self):
        tokens = LayoutAreaParser.lex("20,20,30,40px")
        assert(len(tokens)== 8)
        tokens = LayoutAreaParser.lex("20-10,(20+15px)*3,30,40")
        assert(len(tokens)== 16)


    def test_parse(self):
        tokens = LayoutAreaParser.lex("20,20,30,40px")
        asts = LayoutAreaParser.parse_list(tokens)
        assert(len(asts)== 4)
        tokens = LayoutAreaParser.lex("20-10,(20+15px)*3,30,40")
        asts = LayoutAreaParser.parse_list(tokens)
        assert(len(asts)== 4)


    def test_compute(self):
        self.do_compute("20,20,30,40px", [20,20,30,(40/500)*100])
        self.do_compute("100-400px,20,30,40px", [100-(400/500)*100,20,30,(40/500)*100])
        

    def do_compute(self, source, expected):
        tokens = LayoutAreaParser.lex(source)
        asts = LayoutAreaParser.parse_list(tokens)
        for i, ast in enumerate(asts):
            test = LayoutAreaParser.compute(ast, {}, 500)
            expect = expected[i]
            assert(test == expect)
        
    