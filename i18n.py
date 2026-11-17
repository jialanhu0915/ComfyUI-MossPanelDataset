"""日本語・英語・中国語（簡体）の選択肢と、英語のエラーメッセージ。

内部では従来の日本語の値を正とし、英語と中国語の値は同じ意味の別名として受け付ける。
保存済みワークフローやAPI形式の入力は、どの言語の値でもそのまま動く。
実行時の表示言語はPython側で分からないため、エラーは英語だけで示す。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# 英語の表示名・説明は locales/en/nodeDefs.json を正とする。日本語は locales/ja/nodeDefs.json、
# 中国語（簡体）は locales/zh/nodeDefs.json でComfyUIが切り替える。
LABELS = json.loads((ROOT / 'locales' / 'en' / 'nodeDefs.json').read_text(encoding='utf-8'))
CATEGORY = 'Manga panel dataset'


def labeled(node, fields):
    """入力へ英語の表示名と説明を付ける。内部名（日本語）は保存済みワークフローとの互換のため変えない。"""
    inputs = LABELS[node].get('inputs', {})
    result = {}
    for name, spec in fields.items():
        extra = dict(spec[1]) if len(spec) > 1 else {}
        label = inputs.get(name, {})
        if 'name' in label:
            extra['display_name'] = label['name']
        if 'tooltip' in label:
            extra['tooltip'] = label['tooltip']
        result[name] = (spec[0], extra) if extra else (spec[0],)
    return result


def outputs(node, count):
    return tuple(LABELS[node]['outputs'][str(i)]['name'] for i in range(count))


# (日本語, 英語, 中国語) の組。並び順が画面の選択肢の順になる。
ACTORS = [
    ('人物1のみ', 'Character 1 only', '仅人物1'), ('人物2のみ', 'Character 2 only', '仅人物2'),
    ('人物1と人物2', 'Characters 1 and 2', '人物1和人物2'), ('人物なし', 'No characters', '无人物'),
    ('人物3のみ', 'Character 3 only', '仅人物3'), ('人物1と人物3', 'Characters 1 and 3', '人物1和人物3'),
    ('人物2と人物3', 'Characters 2 and 3', '人物2和人物3'),
    ('人物1と人物2と人物3', 'Characters 1, 2, and 3', '人物1、人物2和人物3'),
]
SPEAKERS = [('セリフなし', 'No dialogue', '无台词'), ('人物1', 'Character 1', '人物1'),
    ('人物2', 'Character 2', '人物2'), ('人物3', 'Character 3', '人物3')]
OUTPUTS = [('漫画', 'Manga', '漫画'), ('空のコマ枠', 'Empty panel frames', '空白分格框')]
COLOURS = [('白黒', 'Black and white', '黑白'), ('カラー', 'Color', '彩色')]
EDITOR_MODES = [('受け取ったまま', 'As received', '保持收到内容'), ('編集した文', 'Edited text', '编辑后的文本')]
APPEARANCE_MODES = [
    ('文章のみ', 'Text only', '仅文本'), ('画像から抽出', 'Extract from image', '从图片提取'),
    ('画像から抽出＋文章で補足', 'Extract from image + text', '从图片提取＋文本补充'),
]
DEFAULT_NAMES = [('漫画家', 'Manga artist', '漫画家'), ('編集者', 'Editor', '编辑')]
SLOT_EN = {ja: en for ja, en, _ in SPEAKERS}
ACTOR_EN = {ja: en for ja, en, _ in ACTORS}


def options(pairs):
    """日本語の値を先に、続けて同じ順で英語と中国語の値を並べた、ComfyUIの検証に通る選択肢。"""
    result = []
    for index in range(len(pairs[0])):
        for pair in pairs:
            if pair[index] not in result:
                result.append(pair[index])
    return result


def canonical(pairs, value, label_en):
    """英語・中国語の値を日本語の値へそろえる。どれでもなければ分かるように止める。"""
    for pair in pairs:
        if value in pair:
            return pair[0]
    choices = ' / '.join(pair[1] for pair in pairs)
    raise ValueError(f'"{value}" is not a valid value for "{label_en}". Choose one of: {choices}')


def slot_label(slot):
    return SLOT_EN[slot]


def actors_label(value):
    return ACTOR_EN.get(value, value)
