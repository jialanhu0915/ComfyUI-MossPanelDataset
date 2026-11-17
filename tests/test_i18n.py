"""日本語・英語・中国語（簡体）の表示と、英語のエラーメッセージを検査する。"""
import importlib
import json
import unittest

from test_composition import nodes, pkg, ROOT

picker_api = importlib.import_module(pkg.__name__ + '.picker_api')
i18n = importlib.import_module(pkg.__name__ + '.i18n')


def cast(**extra):
    fields = {'人物1_名前': '花子', '人物1_外見': 'Black hair, white blouse.', '人物2_名前': '太郎', '人物2_外見': 'Short hair, glasses.'}
    fields.update(extra)
    return nodes.MossMangaCharacters().build(**fields)[0]


def panel(**extra):
    fields = {'場面': 'Two adults talk.', '登場人物': '人物1のみ', '話者1': '人物1', 'セリフ1': 'こんにちは。', '話者2': 'セリフなし', 'セリフ2': ''}
    fields.update(extra)
    return nodes.MossMangaPanel().build(**fields)[0]


class Locales(unittest.TestCase):
    def test_locale_files_cover_the_same_nodes_inputs_and_outputs(self):
        en = json.loads((ROOT / 'locales' / 'en' / 'nodeDefs.json').read_text('utf-8'))
        ja = json.loads((ROOT / 'locales' / 'ja' / 'nodeDefs.json').read_text('utf-8'))
        zh = json.loads((ROOT / 'locales' / 'zh' / 'nodeDefs.json').read_text('utf-8'))
        self.assertEqual(set(en), set(nodes.NODE_CLASS_MAPPINGS))
        self.assertEqual(set(ja), set(en))
        self.assertEqual(set(zh), set(en))
        for name, cls in nodes.NODE_CLASS_MAPPINGS.items():
            with self.subTest(node=name):
                fields = cls.INPUT_TYPES()
                inputs = {**fields.get('required', {}), **fields.get('optional', {})}
                self.assertEqual(set(en[name]['inputs']), set(inputs))
                self.assertEqual(set(ja[name]['inputs']), set(inputs))
                self.assertEqual(set(zh[name]['inputs']), set(inputs))
                self.assertEqual(set(en[name]['outputs']), {str(i) for i in range(len(cls.RETURN_TYPES))})
                self.assertEqual(set(ja[name]['outputs']), set(en[name]['outputs']))
                self.assertEqual(set(zh[name]['outputs']), set(en[name]['outputs']))
                for labels in (ja, zh):
                    self.assertEqual({k for k, v in en[name]['inputs'].items() if 'tooltip' in v}, {k for k, v in labels[name]['inputs'].items() if 'tooltip' in v})
                # 中国語のノード名は英語のままでなく、翻訳した名前を出す。
                self.assertNotEqual(zh[name]['display_name'], en[name]['display_name'])
                # 英語の表示名はPython側の既定値にも入り、ComfyUIが日本語以外の言語でも英語で表示する。
                for key, spec in inputs.items():
                    self.assertEqual(spec[1]['display_name'], en[name]['inputs'][key]['name'])
                self.assertEqual(nodes.NODE_DISPLAY_NAME_MAPPINGS[name], en[name]['display_name'])
                self.assertEqual(cls.RETURN_NAMES, tuple(en[name]['outputs'][str(i)]['name'] for i in range(len(cls.RETURN_TYPES))))

    def test_every_combo_lists_every_language_values(self):
        table = picker_api.client_table()['nodes']
        for name, info in table.items():
            fields = nodes.NODE_CLASS_MAPPINGS[name].INPUT_TYPES()
            inputs = {**fields.get('required', {}), **fields.get('optional', {})}
            self.assertEqual(len(info['display']), 3)
            for key, pairs in info['combos'].items():
                with self.subTest(node=name, input=key):
                    # 中国語の選択肢がないコマ割り・構図の名前は、英語の値だけを持つ。
                    self.assertIn(len(pairs[0]), (2, 3))
                    for index in range(1, len(pairs[0])):
                        values = [pair[index] for pair in pairs]
                        self.assertEqual(len(set(values)), len(values))
                    if isinstance(inputs[key][0], list):
                        self.assertEqual(inputs[key][0], i18n.options(pairs))

    def test_layout_and_composition_have_unique_english_names(self):
        layouts = nodes.core.load_catalog()
        self.assertEqual(len({item['name_en'] for item in layouts}), 196)
        items = nodes.composition.catalog()
        self.assertEqual(len({item['name_en'] for item in items}), 120)
        for item in layouts[:3]:
            self.assertEqual(nodes.core.load_layout(item['name_en']), nodes.core.load_layout(item['name']))
        self.assertEqual(nodes.composition.load(items[0]['name_en'])['id'], items[0]['id'])


class EnglishValues(unittest.TestCase):
    def test_english_values_give_the_same_prompt_as_japanese(self):
        layout = nodes.core.load_catalog()[0]
        ja = panel(登場人物='人物1と人物2', 話者2='人物2', セリフ2='はい。')
        en = panel(登場人物='Characters 1 and 2', 話者1='Character 1', 話者2='Character 2', セリフ2='はい。')
        self.assertEqual(ja, en)
        build = nodes.MossPanelDatasetFlexible().build
        count = len(layout['specification']['panels'])
        args = {'人物設定': cast(), **{f'コマ{i}': ja for i in range(1, count + 1)}}
        self.assertEqual(build(コマ割り=layout['name'], 生成内容='漫画', **args), build(コマ割り=layout['name_en'], 生成内容='Manga', **args))
        self.assertEqual(build(コマ割り=layout['name'], 生成内容='空のコマ枠', **args), build(コマ割り=layout['name_en'], 生成内容='Empty panel frames', **args))

    def test_editor_and_appearance_accept_english_values(self):
        prompt = nodes.core.compile_prompt(nodes.core.load_layout('normal_2_01'), '空のコマ枠')
        editor = nodes.MossPromptEditor()
        self.assertEqual(editor.build(プロンプト=prompt, 使うプロンプト='As received', 編集用プロンプト='')['result'], (prompt,))
        self.assertEqual(editor.build(プロンプト=prompt, 使うプロンプト='Edited text', 編集用プロンプト=prompt)['result'], (prompt,))
        appearance = nodes.MossCharacterAppearance()
        self.assertEqual(appearance.check_lazy_status('Text only'), [])
        self.assertEqual(appearance.build('Text only', 'Red hair.')['result'], ('Red hair.',))

    def test_unknown_value_names_the_choices(self):
        with self.assertRaisesRegex(ValueError, 'Character 1 only'):
            panel(登場人物='誰か')


class ChineseValues(unittest.TestCase):
    def test_chinese_values_give_the_same_prompt_as_japanese(self):
        layout = nodes.core.load_catalog()[0]
        ja = panel(登場人物='人物1と人物2', 話者2='人物2', セリフ2='はい。')
        zh = panel(登場人物='人物1和人物2', 話者1='人物1', 話者2='人物2', セリフ2='はい。')
        self.assertEqual(ja, zh)
        build = nodes.MossPanelDatasetFlexible().build
        count = len(layout['specification']['panels'])
        args = {'人物設定': cast(), **{f'コマ{i}': ja for i in range(1, count + 1)}}
        self.assertEqual(build(コマ割り=layout['name'], 生成内容='漫画', **args), build(コマ割り=layout['name_en'], 生成内容='漫画', **args))
        self.assertEqual(build(コマ割り=layout['name'], 生成内容='空白分格框', **args), build(コマ割り=layout['name'], 生成内容='空のコマ枠', **args))

    def test_editor_and_appearance_accept_chinese_values(self):
        prompt = nodes.core.compile_prompt(nodes.core.load_layout('normal_2_01'), '空のコマ枠')
        editor = nodes.MossPromptEditor()
        self.assertEqual(editor.build(プロンプト=prompt, 使うプロンプト='保持收到内容', 編集用プロンプト='')['result'], (prompt,))
        self.assertEqual(editor.build(プロンプト=prompt, 使うプロンプト='编辑后的文本', 編集用プロンプト=prompt)['result'], (prompt,))
        appearance = nodes.MossCharacterAppearance()
        self.assertEqual(appearance.check_lazy_status('仅文本'), [])
        self.assertEqual(appearance.build('仅文本', 'Red hair.')['result'], ('Red hair.',))


class Colouring(unittest.TestCase):
    def test_black_and_white_and_color_change_the_summary(self):
        layout = nodes.core.load_layout('normal_2_01')
        cast = {'花子': 'Black hair, white blouse.'}
        panels = [{'scene': 'One adult talks.', 'actors': ['花子'], 'dialogue': []}] * 2
        white = json.loads(nodes.core.compile_prompt(layout, '漫画', cast, panels, '白黒'))
        color = json.loads(nodes.core.compile_prompt(layout, '漫画', cast, panels, 'カラー'))
        self.assertIn('black and white Japanese manga', white['summary']['caption'])
        self.assertIn('Professional inked manga with screentones.', white['summary']['caption'])
        self.assertIn('full-color Japanese manga', color['summary']['caption'])
        self.assertIn('Professional full-color manga artwork', color['summary']['caption'])
        self.assertNotIn('screentones', color['summary']['caption'])
        self.assertNotIn('black and white', color['summary']['caption'])
        # 色はsummaryだけで、コマの描写は変わらない。
        self.assertEqual(white['items'], color['items'])

    def test_other_language_values_are_accepted(self):
        build = nodes.MossPanelDatasetFlexible().build
        p = panel()
        args = {'コマ割り': 'normal_2_01', '生成内容': '漫画', '人物設定': cast(), 'コマ1': p, 'コマ2': p}
        self.assertEqual(build(配色='Color', **args), build(配色='カラー', **args))
        self.assertEqual(build(配色='黑白', **args), build(配色='白黒', **args))
        self.assertNotEqual(build(配色='カラー', **args), build(配色='白黒', **args))
        with self.assertRaisesRegex(ValueError, 'Coloring'):
            build(配色='sepia', **args)


class ErrorMessages(unittest.TestCase):
    def check(self, call, *parts):
        with self.assertRaises(ValueError) as caught:
            call()
        message = str(caught.exception)
        for part in parts:
            self.assertIn(part, message)
        # 実行時の表示言語はPython側で分からないため、エラーは英語の1行だけにする。
        self.assertNotIn('\n', message)
        return message

    def test_second_speaker_who_is_not_in_the_panel(self):
        # 登場人物が1人なのに、2つ目のセリフの話者に別の人物を選んだ場合。
        self.check(lambda: panel(話者2='人物2', セリフ2='原稿は？'),
                   '"Speaker 2" is Character 2', '"Character 1 only"', 'Add Character 2 to the characters')

    def test_speaker_mistakes(self):
        self.check(lambda: panel(セリフ2='原稿は？'), '"Line 2" has text')
        self.check(lambda: panel(話者2='人物1'), '"Line 2" is empty')
        self.check(lambda: panel(登場人物='人物なし'), '"No characters"')
        self.check(lambda: panel(場面='  '), '"Scene" is empty')

    def test_composition_count_mismatch_shows_both_counts(self):
        template = nodes.composition.load('duo_01')
        self.check(lambda: panel(構図=template), 'for 2 character(s)', 'this panel has 1', '("Character 1 only")')

    def test_character_mistakes(self):
        self.check(lambda: cast(人物3_名前='葵'), '"Character 3 appearance" is empty')
        self.check(lambda: cast(人物2_外見=''), '"Character 2 appearance" is empty')
        self.check(lambda: cast(人物2_名前='花子'), '"花子" is used more than once')

    def test_layout_mistakes(self):
        build = nodes.MossPanelDatasetFlexible().build
        p = panel()
        self.check(lambda: build(コマ割り='normal_2_01', 生成内容='漫画', 人物設定=cast(), コマ1=p, コマ2=None, コマ3=p),
                   'not connected: panel 2', 'extra: panel 3')
        third = panel(登場人物='人物3のみ', 話者1='人物3')
        self.check(lambda: build(コマ割り='normal_2_01', 生成内容='漫画', 人物設定=cast(), コマ1=p, コマ2=third),
                   'Panel 2 uses Character 3', 'is not set in "Shared characters"')
        self.check(lambda: build(コマ割り='存在しない配置', 生成内容='漫画', 人物設定=cast(), コマ1=p, コマ2=p),
                   'not in the bundled data')


if __name__ == '__main__':
    unittest.main()
