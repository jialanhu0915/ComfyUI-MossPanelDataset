// 画面の表示言語。ComfyUIの言語設定（Comfy.Locale）が日本語なら日本語、それ以外は英語にする。
let appRef=null;
export function useApp(app){appRef=app??appRef;}

export function locale(){
    try{
        const app=appRef??globalThis.comfyAPI?.app?.app;
        const value=app?.extensionManager?.setting?.get?.('Comfy.Locale')??app?.ui?.settings?.getSettingValue?.('Comfy.Locale');
        if(value)return String(value);
    }catch{}
    return globalThis.navigator?.language??'en';
}
export const isJa=()=>/^ja(\b|[-_])/i.test(locale());
export const isZh=()=>/^zh([-_](cn|hans|sg))?$/i.test(locale());
// 0=日本語、1=英語、2=中国語（簡体）。
export const languageIndex=()=>isJa()?0:isZh()?2:1;
// 中国語の訳がない文字列は英語を出す。
export const tr=(ja,en,zh)=>[ja,en,zh??en][languageIndex()];

let tablePromise=null;
export function translations(fetchApi){
    tablePromise??=fetchApi('/moss_panel_dataset/i18n').then(r=>{if(!r.ok)throw Error(tr('翻訳データを読み込めません。','Could not load translations.','无法读取翻译数据。'));return r.json();}).catch(e=>{tablePromise=null;throw e;});
    return tablePromise;
}

// [日本語, 英語, 中国語] の組から、今の表示言語の値を返す。中国語の訳がない組は英語を使う。
export function localizeValue(pairs,value){
    const pair=pairs.find(p=>p.includes(value));
    return pair?pair[languageIndex()]??pair[1]:value;
}

// 選択肢を表示言語の値だけにし、保存済みの値も同じ意味の表示言語の値へ置き換える。
export function localizeCombo(widget,pairs,{text=false}={}){
    if(!widget||!pairs?.length)return false;
    const index=languageIndex();
    if(!text&&Array.isArray(widget.options?.values))widget.options.values=pairs.map(p=>p[index]??p[1]);
    const next=localizeValue(pairs,widget.value);
    if(next===widget.value)return false;
    widget.value=next;
    return true;
}
