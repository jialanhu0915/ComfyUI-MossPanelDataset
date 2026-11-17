"""専用欄の入力をMOSSプロンプトへ渡すComfyUIノード。"""
import json

from . import dataset as core
from . import composition
from .appearance import MossCharacterAppearance
from .i18n import (ACTORS, SPEAKERS, OUTPUTS, COLOURS, EDITOR_MODES, CATEGORY, LABELS, canonical,
    labeled, options, outputs, slot_label, actors_label)

SLOTS=['人物1','人物2','人物3']
ACTOR_SLOTS={'人物1のみ':['人物1'],'人物2のみ':['人物2'],'人物1と人物2':['人物1','人物2'],'人物なし':[],
    '人物3のみ':['人物3'],'人物1と人物3':['人物1','人物3'],'人物2と人物3':['人物2','人物3'],'人物1と人物2と人物3':SLOTS.copy()}
SCENES=['Drawing a manga manuscript with a pen at a desk. Medium shot of the studio.','Standing at the open studio door holding a folder.','Looking away nervously, holding a pen above a blank manuscript. Close-up.','Facing each other across a desk with blank manuscript sheets. Medium two-shot.']


class MossMangaCharacters:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':labeled('MossMangaCharacters',{
            '人物1_名前':('STRING',{'default':'漫画家'}),
            '人物1_外見':('STRING',{'multiline':True,'default':core.DEFAULT_CAST['漫画家']}),
            '人物2_名前':('STRING',{'default':'編集者'}),
            '人物2_外見':('STRING',{'multiline':True,'default':core.DEFAULT_CAST['編集者']})}),
            'optional':labeled('MossMangaCharacters',{'人物3_名前':('STRING',{'default':''}),
            '人物3_外見':('STRING',{'multiline':True,'default':''})})}
    RETURN_TYPES=('MOSS_MANGA_CAST',)
    RETURN_NAMES=outputs('MossMangaCharacters',1)
    DESCRIPTION=LABELS['MossMangaCharacters']['description']
    FUNCTION='build'
    CATEGORY=CATEGORY
    def build(self,**kw):
        cast={s:{'name':kw[s+'_名前'].strip(),'appearance':kw[s+'_外見'].strip()} for s in SLOTS[:2]}
        third={'name':kw.get('人物3_名前','').strip(),'appearance':kw.get('人物3_外見','').strip()}
        if third['name'] or third['appearance']:
            if not third['name'] or not third['appearance']:
                missing_en='Character 3 name' if not third['name'] else 'Character 3 appearance'
                raise ValueError(f'To use character 3, fill in both "Character 3 name" and "Character 3 appearance". "{missing_en}" is empty. Leave both empty if you do not use character 3.')
            cast['人物3']=third
        for slot,person in cast.items():
            n=slot[-1]
            if not person['name']:
                raise ValueError(f'"Character {n} name" is empty. Enter a name (any language).')
            if not person['appearance']:
                raise ValueError(f'"Character {n} appearance" is empty. Describe the appearance in English, or connect the output of "Character appearance (image / text)".')
        names=[person['name'] for person in cast.values()]
        duplicated=sorted({name for name in names if names.count(name)>1})
        if duplicated:
            raise ValueError(f'The character name "{", ".join(duplicated)}" is used more than once. Give each character a different name.')
        return (cast,)

class MossMangaPanel:
    @classmethod
    def INPUT_TYPES(cls):
        speakers=options(SPEAKERS)
        return {'required':labeled('MossMangaPanel',{
            '場面':('STRING',{'multiline':True,'default':SCENES[0]}),
            '登場人物':(options(ACTORS),),
            '話者1':(speakers,),
            'セリフ1':('STRING',{'multiline':True,'default':''}),
            '話者2':(speakers,),
            'セリフ2':('STRING',{'multiline':True,'default':''})}),
            'optional':labeled('MossMangaPanel',{'構図':('MOSS_COMPOSITION',),
                '話者3':(speakers,{'default':'セリフなし'}),
                'セリフ3':('STRING',{'multiline':True,'default':''})})}
    RETURN_TYPES=('MOSS_MANGA_PANEL',)
    RETURN_NAMES=outputs('MossMangaPanel',1)
    DESCRIPTION=LABELS['MossMangaPanel']['description']
    FUNCTION='build'
    CATEGORY=CATEGORY
    def build(self,**kw):
        scene=kw['場面'].strip()
        if not scene:
            raise ValueError('"Scene" is empty. Describe the scene of this panel in English.')
        chosen=canonical(ACTORS,kw['登場人物'],'Characters')
        actors=ACTOR_SLOTS[chosen]
        lines=[]
        for i in (1,2,3):
            speaker=canonical(SPEAKERS,kw.get(f'話者{i}','セリフなし'),f'Speaker {i}')
            text=kw.get(f'セリフ{i}','')
            if speaker=='セリフなし':
                if text.strip():
                    raise ValueError(f'"Line {i}" has text, but "Speaker {i}" is "No dialogue". Choose who says line {i}, or clear line {i}.')
                continue
            if not actors:
                raise ValueError(f'A panel with "No characters" cannot have dialogue, but "Speaker {i}" is {slot_label(speaker)}. Choose characters for the panel, or set speaker {i} to "No dialogue".')
            if speaker not in actors:
                raise ValueError(f'"Speaker {i}" is {slot_label(speaker)}, but this panel\'s characters are "{actors_label(chosen)}". {slot_label(speaker)} is not in this panel and cannot speak. Add {slot_label(speaker)} to the characters, or change speaker {i}.')
            if not text.strip():
                raise ValueError(f'"Speaker {i}" is {slot_label(speaker)}, but "Line {i}" is empty. Enter the line, or set speaker {i} to "No dialogue".')
            lines.append({'slot':speaker,'text':text})
        panel={'scene':scene,'actors':list(actors),'dialogue':lines}
        if kw.get('構図') is not None:
            template=kw['構図']
            boxes=template.get('boxes')
            if not isinstance(template.get('prompt'),str) or not template['prompt'].strip() or not isinstance(boxes,list):
                raise ValueError('Invalid composition data. Connect the output of "Choose a composition (preview images)" to "Composition".')
            if len(actors)!=len(boxes):
                raise ValueError(f'The connected composition "{template.get("name_en") or template.get("name","")}" is for {len(boxes)} character(s), but this panel has {len(actors)} ("{actors_label(chosen)}"). Choose a composition with the same number of characters, or change the characters.')
            panel['scene']=scene+' Composition: '+template['prompt']
            panel['composition_boxes']=template['boxes']
        return (panel,)

class MossPanelDatasetFlexible:
    @classmethod
    def INPUT_TYPES(cls):
        names=[name for _,name in core.list_layouts()]+[name for _,name in core.list_layouts('en')]
        required={'コマ割り':(names,),'生成内容':(options(OUTPUTS),),'配色':(options(COLOURS),{'default':'白黒'}),'人物設定':('MOSS_MANGA_CAST',)}
        required.update({f'コマ{i}':('MOSS_MANGA_PANEL',) for i in (1,2)})
        return {'required':labeled('MossPanelDatasetFlexible',required),'optional':labeled('MossPanelDatasetFlexible',{f'コマ{i}':('MOSS_MANGA_PANEL',) for i in (3,4,5,6)})}
    RETURN_TYPES=('STRING','INT','INT')
    RETURN_NAMES=outputs('MossPanelDatasetFlexible',3)
    DESCRIPTION=LABELS['MossPanelDatasetFlexible']['description']
    FUNCTION='build'
    CATEGORY=CATEGORY
    @classmethod
    def IS_CHANGED(cls,**kw):
        return core.CATALOG.stat().st_mtime_ns

    def build(self,**kw):
        layout=core.load_layout(kw['コマ割り'])
        mode=canonical(OUTPUTS,kw['生成内容'],'Output')
        colour=canonical(COLOURS,kw.get('配色','白黒'),'Coloring')
        if mode=='空のコマ枠':
            prompt=core.compile_prompt(layout,'空のコマ枠',colour=colour)
        else:
            count=len(layout['panels'])
            expected={i for i in range(1,count+1)}
            supplied={i for i in range(1,7) if kw.get(f'コマ{i}') is not None}
            if supplied!=expected:
                missing=sorted(expected-supplied); extra=sorted(supplied-expected)
                detail_en='; '.join(([f'not connected: {", ".join(f"panel {i}" for i in missing)}'] if missing else [])+([f'extra: {", ".join(f"panel {i}" for i in extra)}'] if extra else []))
                raise ValueError(f'The selected layout has {count} panels. Connect one "Panel content" node to each of panel 1 to panel {count}, and disconnect the others ({detail_en}).')
            cast=kw['人物設定']
            panels=[]
            for i in range(1,count+1):
                p=kw[f'コマ{i}']
                missing=[slot for slot in p['actors'] if slot not in cast]
                if missing:
                    slot=missing[0]
                    raise ValueError(f'Panel {i} uses {slot_label(slot)}, but {slot_label(slot)} is not set in "Shared characters". Fill in both "{slot_label(slot)} name" and "{slot_label(slot)} appearance", or change the characters of panel {i}.')
                panels.append({'scene':p['scene'],'actors':[cast[s]['name'] for s in p['actors']],
                    'dialogue':[{'speaker':cast[line['slot']]['name'],'text':line['text']} for line in p['dialogue']]})
                if 'composition_boxes' in p:
                    panels[-1]['composition_boxes']=p['composition_boxes']
            prompt=core.compile_prompt(layout,'漫画',{p['name']:p['appearance'] for p in cast.values()},panels,colour)
        return prompt,layout['width'],layout['height']

class MossPromptEditor:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':labeled('MossPromptEditor',{
            'プロンプト':('STRING',{'forceInput':True}),
            '使うプロンプト':(options(EDITOR_MODES),),
            '編集用プロンプト':('STRING',{'multiline':True,'default':''})})}
    RETURN_TYPES=('STRING',)
    RETURN_NAMES=outputs('MossPromptEditor',1)
    DESCRIPTION=LABELS['MossPromptEditor']['description']
    FUNCTION='build'
    CATEGORY=CATEGORY
    def build(self,**kw):
        received=kw['プロンプト']
        if canonical(EDITOR_MODES,kw['使うプロンプト'],'Prompt to use')=='受け取ったまま':
            prompt=received
        else:
            edited=kw['編集用プロンプト']
            if not edited.strip():
                raise ValueError('"Edited prompt" is empty. Run once with "As received" to fill it with the received prompt.')
            try:
                prompt=core.dumps(json.loads(edited))
            except json.JSONDecodeError as error:
                raise ValueError(f'"Edited prompt" is not valid JSON (line {error.lineno}, column {error.colno}). Check brackets, commas, and quotes.') from error
        return {'ui':{'text':[received]},'result':(prompt,)}

class MossCompositionTemplate:
    @classmethod
    def INPUT_TYPES(cls):
        items=composition.catalog()
        names=[item['name'] for item in items]+[item['name_en'] for item in items]
        return {'required':labeled('MossCompositionTemplate',{'構図テンプレート':(names or ['生成済みの構図がありません / No compositions'],)})}
    RETURN_TYPES=('MOSS_COMPOSITION','STRING')
    RETURN_NAMES=outputs('MossCompositionTemplate',2)
    DESCRIPTION=LABELS['MossCompositionTemplate']['description']
    FUNCTION='build'
    CATEGORY=CATEGORY
    @classmethod
    def IS_CHANGED(cls,**kw):
        return composition.CATALOG.stat().st_mtime_ns if composition.CATALOG.exists() else 0
    def build(self,**kw):
        item=composition.load(kw['構図テンプレート'])
        return item,item['prompt']

NODE_CLASS_MAPPINGS={'MossCompositionTemplate':MossCompositionTemplate,'MossPanelDatasetFlexible':MossPanelDatasetFlexible,'MossMangaCharacters':MossMangaCharacters,'MossMangaPanel':MossMangaPanel,'MossPromptEditor':MossPromptEditor,'MossCharacterAppearance':MossCharacterAppearance}
NODE_DISPLAY_NAME_MAPPINGS={name:LABELS[name]['display_name'] for name in NODE_CLASS_MAPPINGS}
