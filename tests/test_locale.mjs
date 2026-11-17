import assert from 'node:assert/strict';
import { useApp, languageIndex, tr, localizeCombo } from '../web/i18n.mjs';

const app=locale=>({extensionManager:{setting:{get:()=>locale}}});
const panel=[['人物1のみ','Character 1 only','仅人物1'],['人物2のみ','Character 2 only','仅人物2']];

useApp(app('ja'));
assert.equal(languageIndex(),0);
assert.equal(tr('日本語','English','中文'),'日本語');

useApp(app('zh'));
assert.equal(languageIndex(),2);
assert.equal(tr('日本語','English','中文'),'中文');
// 中国語の訳がない文字列は英語を出す。
assert.equal(tr('日本語','English'),'English');
const speakers={value:'人物2のみ',options:{values:['人物1のみ','Character 1 only','仅人物1','人物2のみ','Character 2 only','仅人物2']}};
assert.equal(localizeCombo(speakers,panel),true);
assert.equal(speakers.value,'仅人物2');
assert.deepEqual(speakers.options.values,['仅人物1','仅人物2']);
// 中国語の名前がないコマ割りは、英語の名前で表示する。
const layout={value:'2コマ・斜め01',options:{values:[]}};
assert.equal(localizeCombo(layout,[['2コマ・斜め01','2 panels · Diagonal 01']]),true);
assert.equal(layout.value,'2 panels · Diagonal 01');
assert.deepEqual(layout.options.values,['2 panels · Diagonal 01']);

// 繁体字中国語には未対応なので、英語で表示する。
useApp(app('zh-TW'));
assert.equal(languageIndex(),1);
assert.equal(tr('日本語','English','中文'),'English');
console.log('表示言語の判定、中国語の選択肢、英語への代替表示の検査が通りました。');
