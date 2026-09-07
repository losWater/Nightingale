import importlib.util
import unittest
from collections import OrderedDict
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'work/夜莺0.85/scripts/build_v085_derived_tables_from_masters.py'
spec = importlib.util.spec_from_file_location('sogou_explicit', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExplicitWordOrderTests(unittest.TestCase):
    def test_sparse_export_includes_selected_ordinary_words(self):
        source = OrderedDict([('yige', ['一个', '一哥', '亿个']), ('viui', ['知识', '只是'])])
        sparse = module.render_sogou(source, ['; header'], True)
        actual = module.explicit_word_order(sparse, source, ['yige'])
        self.assertEqual(actual, ['; header', '', 'yige,1=一个', 'yige,2=一哥', 'yige,3=亿个'])

    def test_existing_rows_are_replaced_without_duplicates(self):
        source = OrderedDict([('yige', ['一个', '一哥'])])
        self.assertEqual(module.explicit_word_order(['abc,1=字', 'yige,2=旧词'], source, ['yige', 'yige']),
                         ['abc,1=字', 'yige,1=一个', 'yige,2=一哥'])

    def test_invalid_or_missing_codes_fail(self):
        for code in ['yg', 'missing', 'aaaa']:
            with self.assertRaises(ValueError):
                module.explicit_word_order([], OrderedDict(), [code])
