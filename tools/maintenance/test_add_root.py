"""Read-only root-plan regression tests; no live input-method data."""
import copy
import json
from pathlib import Path
import unittest
from add_root import transform
from export import extract_json


class RootTests(unittest.TestCase):
    def setUp(self):
        root = {'根': '一', '键': 'p', '组': '横'}
        self.plan = {'root': {'根': '无点根', '键': 'v', '组': '戈'},
                     'replace_sequence': ['一', '折', '撇'],
                     'characters': ['尧'], 'examples': ['尧']}
        roots = [root, {'根': '折', '键': 'b', '组': '折'},
                 {'根': '撇', '键': 'f', '组': '撇'}, {'根': '兀', '键': 'p', '组': '儿'},
                 {'根': '戈', '键': 'v', '组': '戈'}]
        data = {'尧': {'根': roots[:4], '新拆': '一 ＋ 折 ＋ 撇 ＋ 兀',
                      '编码': [{'码': 'ycpp', '位': 1, '同码': ['尧']}]}}
        dump = lambda n, v: 'const '+n+'='+json.dumps(v, ensure_ascii=False)+';'
        view = dump('D', data)+dump('ROOTS', roots)
        views = {'query': view, 'components': view,
                 'text': dump('rows', [['尧', data['尧']['新拆'], '一', '兀']]),
                 'practice': dump('roots', roots)+dump('rootExamples', {}),
                 'roots': '<table><tbody></tbody></table>',
                 'image': '<section data-search="v 戈"><dt>戈</dt><dd>弋</dd></section>'}
        self.page = dump('views', views)
        self.table = [('尧', 'ycpp'), ('尧', 'ycv'), ('尧', 'ycvp')]
        self.full = {('尧', 'yc'): ['ycvp']}

    def test_all_views_and_legacy_codes(self):
        page, changes = transform(self.page, self.plan, self.table, self.full)
        self.assertEqual(len(changes), 1)
        views = extract_json(page, 'views')
        for name in ('query', 'components'):
            data = extract_json(views[name], 'D')['尧']
            self.assertEqual(data['新拆'], '无点根 ＋ 兀')
            self.assertEqual([x['码'] for x in data['编码']], ['ycpp', 'ycv', 'ycvp'])
        for value in views.values():
            self.assertIn('无点根', value)
        with self.assertRaises(ValueError):
            transform(page, self.plan, self.table, self.full)

    def test_reject_unreviewed_impact(self):
        plan = copy.deepcopy(self.plan); plan['characters'].append('翘')
        with self.assertRaises(ValueError):
            transform(self.page, plan, self.table, self.full)

    def test_reject_wrong_formal_code(self):
        with self.assertRaises(ValueError):
            transform(self.page, self.plan, self.table, {('尧', 'yc'): ['ycpp']})

    def test_reject_unknown_group(self):
        plan = copy.deepcopy(self.plan); plan['root']['键'] = 'z'
        with self.assertRaises(ValueError):
            transform(self.page, plan, self.table, self.full)


if __name__ == '__main__':
    unittest.main()
