# -*- coding: utf-8 -*-
import json
import io
import os
import re
import sys
import time
import importlib.util
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import adsk.core
import adsk.fusion


def _load_i18n_symbols():
    try:
        from BambuLabNativeV10_i18n import  _getText,_ensure_lang
        return _getText,_ensure_lang
    except Exception:
        pass

    module_name = 'BambuLabNativeV10_i18n'
    module_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), module_name + '.py')
    module_dir = os.path.dirname(module_path)
    if module_dir and module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if not spec or not spec.loader:
        raise ImportError('Could not load i18n module: ' + module_path)

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, '_getText'), getattr(mod, '_ensure_lang')


_getText, _ensure_lang = _load_i18n_symbols()

PALETTE_ID='BambuLabNativePaletteV10'
TOOLS_PALETTE_ID='BambuLabNativeToolsPaletteV10'
SETTINGS_PALETTE_ID='BambuLabNativeSettingsPaletteV10'
CMD_ID='BambuLabNativeV10'
handlers=[]
ACTIVE_SCOPE='body'

CATALOG_CACHE_URL='https://donkie.github.io/SpoolmanDB/filaments.json'
CATALOG_CACHE_FILE='filament_catalog_cache.json'
UI_STATE_FILE='ui_state.json'
CATALOG_CACHE_TTL_SECONDS=7*24*60*60
HEX_RE=re.compile(r'^[0-9A-Fa-f]{6}$')
MAX_COLOR_FILTER_TOLERANCE=30
DEFAULT_COLOR_FILTER_TOLERANCE=12


def _get_palette(ui,palette_id):
    return ui.palettes.itemById(palette_id)


def _send_to_palette(ui,palette_id,action,data):
    p=_get_palette(ui,palette_id)
    if p:
        p.sendInfoToHTML(action,data)


def _broadcast_status(ui,message):
    _send_to_palette(ui,PALETTE_ID,'status',message)
    _send_to_palette(ui,TOOLS_PALETTE_ID,'status',message)
    _send_to_palette(ui,SETTINGS_PALETTE_ID,'status',message)


def _ensure_palette(ui,palette_id,title,file_name,width,height):
    p=_get_palette(ui,palette_id)
    if p:
        return p
    file_path=os.path.join(os.path.dirname(os.path.realpath(__file__)),file_name)
    palette_path=make_file_url(file_path)
    p=ui.palettes.add(palette_id,title,palette_path,True,True,True,width,height,True)
    p.dockingState=adsk.core.PaletteDockingStates.PaletteDockStateRight
    h=PH()
    p.incomingFromHTML.add(h)
    handlers.append(h)
    return p


def _ui_state_path():
    return os.path.join(_addon_dir(),UI_STATE_FILE)


def _default_ui_state():
    return {
        'scope':'body',
        'filters':{
            'q':'',
            'cat':'',
            'mat':'',
            'fin':'',
            'sort':'name',
            'cOn':'0',
            'cHex':'#4F8CFF',
            'cDist':str(DEFAULT_COLOR_FILTER_TOLERANCE),
            'pageSize':'40'
        }
    }


def _sanitize_filters(filters):
    if not isinstance(filters,dict):
        return _default_ui_state()['filters']
    out={}
    for key in ('q','cat','mat','fin','sort','cOn','cHex','cDist','pageSize'):
        value=filters.get(key,'')
        out[key]=value if isinstance(value,str) else ''
    if out.get('sort') not in ('name','color'):
        out['sort']='name'
    if out.get('cOn') not in ('0','1'):
        out['cOn']='0'
    color_hex=(out.get('cHex') or '').strip().lstrip('#')
    if HEX_RE.fullmatch(color_hex):
        out['cHex']='#'+color_hex.upper()
    else:
        out['cHex']='#4F8CFF'
    try:
        distance=int(out.get('cDist') or str(DEFAULT_COLOR_FILTER_TOLERANCE))
    except ValueError:
        distance=DEFAULT_COLOR_FILTER_TOLERANCE
    out['cDist']=str(max(0,min(MAX_COLOR_FILTER_TOLERANCE,distance)))
    if out.get('pageSize') not in ('20','40','80','120','200'):
        out['pageSize']='40'
    return out


def _load_ui_state():
    state=_default_ui_state()
    try:
        loaded=_read_json_file(_ui_state_path())
    except (OSError,json.JSONDecodeError):
        return state
    if not isinstance(loaded,dict):
        return state
    scope=loaded.get('scope')
    if scope in ('body','face','component','selected_all','all_model'):
        state['scope']=scope
    state['filters']=_sanitize_filters(loaded.get('filters'))
    return state


def _save_ui_state(state):
    safe=_default_ui_state()
    if isinstance(state,dict):
        scope=state.get('scope')
        if scope in ('body','face','component','selected_all','all_model'):
            safe['scope']=scope
        safe['filters']=_sanitize_filters(state.get('filters'))
    _write_json_file(_ui_state_path(),safe)
    return safe


def _get_saved_filters():
    return _load_ui_state().get('filters',_default_ui_state()['filters'])


def _save_filters(filters):
    state=_load_ui_state()
    state['filters']=_sanitize_filters(filters)
    _save_ui_state(state)


def _load_saved_scope():
    return _load_ui_state().get('scope','body')


def _save_scope(scope):
    state=_load_ui_state()
    if scope in ('body','face','component','selected_all','all_model'):
        state['scope']=scope
    _save_ui_state(state)

def C(h,a=255):
    h=h.lstrip('#')
    return adsk.core.Color.create(int(h[:2],16),int(h[2:4],16),int(h[4:6],16),a)

# On Windows, the path comes with backslashes, so we need to replace them with forward slashes for the file URL.
# Otherwise when Fusion is running on Windows, it fails to find the palette.
def make_file_url(path):
    return Path(path).as_uri()

def _find_native_base(translucent=False):
    """
    Find a genuine Autodesk library appearance, not an appearance created
    in this document. Preference is given to native libraries.
    """
    app=adsk.core.Application.get()
    libs=app.materialLibraries
    candidates=[]

    for i in range(libs.count):
        try:
            lib=libs.item(i)
            # Native Autodesk library first.
            native_score=0 if getattr(lib,'isNative',False) else 1
            for j in range(lib.appearances.count):
                try:
                    a=lib.appearances.item(j)
                    props=a.appearanceProperties
                    if not props:
                        continue

                    if translucent:
                        # Genuine transparent schemas expose transparent_color.
                        if props.itemById('transparent_color'):
                            # Prefer simple glass/clear-plastic-like schemas.
                            name=(a.name or '').lower()
                            name_score=0 if any(k in name for k in ('glass','clear','transparent','plastic')) else 1
                            candidates.append((native_score,name_score,a))
                    else:
                        # Generic Autodesk opaque appearances expose opaque_albedo.
                        if props.itemById('opaque_albedo'):
                            name=(a.name or '').lower()
                            # Prefer Plastic / Generic rather than wood, stone, paint texture, etc.
                            good=any(k in name for k in ('plastic','generic','smooth','matte'))
                            bad=any(k in name for k in ('wood','oak','walnut','stone','brick','fabric','leather','marble'))
                            name_score=0 if good and not bad else (2 if bad else 1)
                            candidates.append((native_score,name_score,a))
                except:
                    pass
        except:
            pass

    if not candidates:
        return None

    candidates.sort(key=lambda x:(x[0],x[1]))
    return candidates[0][2]

def _set_native_copied_color(a,d):
    """
    Change only the color-related properties of the copied native appearance.
    This deliberately keeps the Autodesk appearance schema and metadata.
    """
    c=C(d['hex'])
    props=a.appearanceProperties

    # Disconnect texture on the primary color slot where possible.
    # A copied plastic with a texture would otherwise keep the wood/etc look.
    for pid in ('opaque_albedo','transparent_color','generic_diffuse'):
        try:
            p=props.itemById(pid)
            if not p:
                continue
            try:
                if p.hasConnectedTexture:
                    p.hasConnectedTexture=False
            except:
                pass
            if not p.isReadOnly:
                p.value=c
        except:
            pass

    # Newer Fusion also exposes the normalized color property.
    try:
        a.color=c
    except:
        pass

    # Keep native schema, only tune roughness if writable.
    rough=float(d.get('roughness',.44))
    for rid in ('surface_roughness','opaque_roughness','generic_roughness'):
        try:
            rp=props.itemById(rid)
            if rp and not rp.isReadOnly:
                rp.value=rough
                break
        except:
            pass

    # Transparent appearance parameters: keep the native transparent schema.
    if d.get('translucent'):
        opacity=float(d.get('opacity',.45))
        # Different Autodesk schemas expose different parameter ids.
        for pid in ('transparency','generic_transparency','transparent_transparency'):
            try:
                p=props.itemById(pid)
                if p and not p.isReadOnly:
                    # Most transparency properties represent amount transparent.
                    p.value=max(0.0,min(1.0,1.0-opacity))
            except:
                pass

def get_app(design,d):
    """
    V9 strategy:
      Native Autodesk Library Appearance
                ↓ addByCopy()
      Appearance stored in current Fusion design
                ↓ recolor
      Bambu Native appearance
    """
    name=f"Bambu Native | {d['material']} | {d['color_name']} | {d['hex']}"
    existing=design.appearances.itemByName(name)
    if existing:
        return existing

    base=_find_native_base(bool(d.get('translucent')))
    if not base:
        return None

    try:
        copied=design.appearances.addByCopy(base,name)
        _set_native_copied_color(copied,d)
        return copied
    except:
        return None

def _all_visible_bodies(design):
    bodies=[]
    try:
        root=design.rootComponent
        for i in range(root.bRepBodies.count):
            b=root.bRepBodies.item(i)
            try:
                if b.isVisible:bodies.append(b)
            except:
                bodies.append(b)
        # Occurrence bodies
        occs=root.allOccurrences
        for i in range(occs.count):
            occ=occs.item(i)
            try:
                if not occ.isVisible: continue
            except:
                pass
            comp=occ.component
            for j in range(comp.bRepBodies.count):
                try:
                    bp=occ.bRepBodies.item(j)
                except:
                    bp=None
                if bp:
                    try:
                        if bp.isVisible:bodies.append(bp)
                    except:
                        bodies.append(bp)
    except:
        pass
    return bodies

def apply_sel(a, scope='auto', sel=None):
    app=adsk.core.Application.get()
    ui=app.userInterface
    design=adsk.fusion.Design.cast(app.activeProduct)
    s=sel or ui.activeSelections
    n=0

    # Entire model, no selection required.
    if scope=='all_model':
        for b in _all_visible_bodies(design):
            try:
                b.appearance=a
                n+=1
            except:
                pass
        return _getText('apply_all_model_success',n=n) if n else _getText('apply_all_model_none')

    if s.count==0:
        return _getText('select_prompt')

    for i in range(s.count):
        e=s.item(i)
        try:
            # FACE ONLY
            if scope=='face':
                if isinstance(e,adsk.fusion.BRepFace):
                    e.appearance=a
                    n+=1

            # BODY / OBJECT
            elif scope=='body':
                if isinstance(e,adsk.fusion.BRepBody):
                    e.appearance=a
                    n+=1
                elif isinstance(e,adsk.fusion.BRepFace):
                    try:
                        e.body.appearance=a
                        n+=1
                    except:
                        pass

            # COMPONENT: all bodies in selected component/occurrence
            elif scope=='component':
                if isinstance(e,adsk.fusion.Occurrence):
                    try:
                        for j in range(e.bRepBodies.count):
                            e.bRepBodies.item(j).appearance=a
                            n+=1
                    except:
                        comp=e.component
                        for j in range(comp.bRepBodies.count):
                            comp.bRepBodies.item(j).appearance=a
                            n+=1
                elif isinstance(e,adsk.fusion.Component):
                    for j in range(e.bRepBodies.count):
                        e.bRepBodies.item(j).appearance=a
                        n+=1
                elif isinstance(e,adsk.fusion.BRepBody):
                    try:
                        comp=e.parentComponent
                        for j in range(comp.bRepBodies.count):
                            comp.bRepBodies.item(j).appearance=a
                            n+=1
                    except:
                        e.appearance=a
                        n+=1

            # ALL SELECTED: whatever is selected, recursively where sensible
            elif scope=='selected_all':
                if isinstance(e,adsk.fusion.BRepFace):
                    e.appearance=a
                    n+=1
                elif isinstance(e,adsk.fusion.BRepBody):
                    e.appearance=a
                    n+=1
                elif isinstance(e,adsk.fusion.Occurrence):
                    for j in range(e.bRepBodies.count):
                        e.bRepBodies.item(j).appearance=a
                        n+=1
                elif isinstance(e,adsk.fusion.Component):
                    for j in range(e.bRepBodies.count):
                        e.bRepBodies.item(j).appearance=a
                        n+=1

            # AUTO: preserve previous behavior
            else:
                if isinstance(e,(adsk.fusion.BRepBody,adsk.fusion.BRepFace,adsk.fusion.Occurrence)):
                    e.appearance=a
                    n+=1
                elif isinstance(e,adsk.fusion.Component):
                    for j in range(e.bRepBodies.count):
                        e.bRepBodies.item(j).appearance=a
                        n+=1
        except:
            pass

    labels={
        'face':_getText('label_face'),
        'body':_getText('label_body'),
        'component':_getText('label_component'),
        'selected_all':_getText('label_selected_all'),
        'auto':_getText('label_auto')
    }
    return _getText('apply_scope_success',n=n,label=labels.get(scope,_getText('label_auto'))) if n else _getText('selection_mode_mismatch') 


def _safe_doc_name(name):
    import re
    s=(name or 'Bambu_Model').strip()
    s=re.sub(r'[\\/:*?"<>|]+','-',s)
    return s[:80] or 'Bambu_Model'

def _pick_folder(ui):
    dlg=ui.createFolderDialog()
    dlg.title=_getText('pick_folder_title')
    if dlg.showDialog()!=adsk.core.DialogResults.DialogOK:
        return None
    return dlg.folder

def _export_f3d_to(design, filename):
    mgr=design.exportManager
    opts=mgr.createFusionArchiveExportOptions(filename, design.rootComponent)
    return bool(mgr.execute(opts))

def _export_3mf_to(design, filename):
    mgr=design.exportManager
    opts=mgr.createC3MFExportOptions(design.rootComponent, filename)
    opts.sendToPrintUtility=False
    try:
        opts.isOneFilePerBody=False
    except:
        pass
    try:
        opts.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
    except:
        pass
    return bool(mgr.execute(opts))

def export_parent(kind='bundle'):
    app=adsk.core.Application.get()
    ui=app.userInterface
    design=adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        return False,_getText('open_design')

    folder=_pick_folder(ui)
    if not folder:
        return False,_getText('export_cancelled')

    doc=app.activeDocument
    base=_safe_doc_name(doc.name if doc else 'Bambu_Model')
    f3d=os.path.join(folder,base+'_PARENT.f3d')
    mf3=os.path.join(folder,base+'_PARENT.3mf')
    done=[]
    failed=[]

    if kind in ('f3d','bundle'):
        try:
            if _export_f3d_to(design,f3d):
                done.append('F3D')
            else:
                failed.append('F3D')
        except Exception as ex:
            failed.append('F3D: '+str(ex))

    if kind in ('3mf','bundle'):
        try:
            if _export_3mf_to(design,mf3):
                done.append('3MF')
            else:
                failed.append('3MF')
        except Exception as ex:
            failed.append('3MF: '+str(ex))

    if kind=='bundle':
        try:
            with open(os.path.join(folder,'BAMBU_PARENT_EXPORT_README.txt'),'w',encoding='utf-8') as f:
                f.write(_getText('export_readme',base=base))
        except:
            pass

    msg=''
    if done:
        msg+=_getText('export_done')+', '.join(done)
    if failed:
        if msg: msg+=' · '
        msg+=_getText('export_failed')+' | '.join(failed)
    msg+=' · '+_getText('export_folder',folder=folder)
    return len(done)>0,msg

def _addon_dir():
    return os.path.dirname(os.path.realpath(__file__))


def _cache_catalog_path():
    return os.path.join(_addon_dir(),CATALOG_CACHE_FILE)


def _read_json_file(path):
    with open(path,'r',encoding='utf-8') as f:
        return json.load(f)


def _write_json_file(path,payload):
    with open(path,'w',encoding='utf-8') as f:
        json.dump(payload,f,ensure_ascii=False,separators=(',',':'))


def _json_text(payload):
    return json.dumps(payload,ensure_ascii=False,separators=(',',':'))


def _normalize_hex(value):
    if not isinstance(value,str):
        return ''
    s=value.strip().lstrip('#')
    if not HEX_RE.fullmatch(s):
        return ''
    return '#'+s.upper()


def _normalize_hexes(color_hex,color_hexes):
    values=[]
    if isinstance(color_hexes,list):
        for item in color_hexes:
            hx=_normalize_hex(item)
            if hx:
                values.append(hx)
    first=_normalize_hex(color_hex)
    if first and first not in values:
        values.insert(0,first)
    if not values and first:
        values=[first]
    return values


def _map_finish(raw_finish,pattern,multi_color_direction,glow):
    finish=(raw_finish or '').strip().lower()
    pattern_name=(pattern or '').strip().lower()
    has_multi=bool((multi_color_direction or '').strip())
    if glow:
        return 'glow'
    if has_multi:
        return 'multi'
    if pattern_name=='sparkle':
        return 'sparkle'
    if finish=='matte':
        return 'matte'
    if finish in ('glossy','silk'):
        return 'silk'
    return 'standard'


def _build_search_text(manufacturer,material,color_name,finish,pattern):
    parts=[manufacturer,material,color_name,finish,pattern]
    return ' '.join([p.strip().lower() for p in parts if isinstance(p,str) and p.strip()])


def _spoolman_row_to_catalog_entry(row):
    if not isinstance(row,dict):
        return None
    manufacturer=(row.get('manufacturer') or '').strip()
    material=(row.get('material') or '').strip()
    color_name=(row.get('name') or '').strip()
    hexes=_normalize_hexes(row.get('color_hex'),row.get('color_hexes'))
    if not manufacturer or not material or not color_name or not hexes:
        return None

    finish=_map_finish(
        row.get('finish'),
        row.get('pattern'),
        row.get('multi_color_direction'),
        bool(row.get('glow'))
    )
    translucent=bool(row.get('translucent'))
    pattern=(row.get('pattern') or '').strip()

    return {
        'manufacturer':manufacturer,
        'material':material,
        'color_name':color_name,
        'hex':hexes[0],
        'hexes':hexes,
        'finish':finish,
        'translucent':translucent,
        'opacity':0.45 if translucent else 1.0,
        'roughness':0.58 if finish=='matte' else 0.44,
        'hex_quality':'spoolman-db',
        'search_text':_build_search_text(manufacturer,material,color_name,finish,pattern)
    }


def _normalize_spoolman_entries(rows):
    out=[]
    seen=set()
    if not isinstance(rows,list):
        return out
    for row in rows:
        entry=_spoolman_row_to_catalog_entry(row)
        if not entry:
            continue
        key='|'.join([
            entry.get('manufacturer',''),
            entry.get('material',''),
            entry.get('color_name',''),
            entry.get('hex','')
        ])
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def _build_payload(entries,version,source):
    return {
        'schema_version':2,
        'catalog_version':str(version),
        'generated_epoch':int(time.time()),
        'entry_count':len(entries),
        'source':source,
        'entries':entries
    }


def _download_spoolman_entries():
    req=Request(
        CATALOG_CACHE_URL,
        headers={'User-Agent':'BambuLabNativeV10/1.0'}
    )
    with urlopen(req,timeout=20) as resp:
        status=getattr(resp,'status',200)
        if status<200 or status>=300:
            raise ValueError(f'Unexpected HTTP status: {status}')
        charset=(resp.headers.get_content_charset() or 'utf-8')
        text_stream=io.TextIOWrapper(resp,encoding=charset,errors='replace')
        payload=json.load(text_stream)
        if not isinstance(payload,list):
            raise ValueError('Remote catalog payload is not a list')
        return payload


def _load_cache_payload():
    try:
        payload=_read_json_file(_cache_catalog_path())
    except (OSError,json.JSONDecodeError):
        return None
    if not isinstance(payload,dict):
        return None
    if not isinstance(payload.get('entries'),list):
        return None
    return payload


def _is_supported_catalog_entry(entry):
    if not isinstance(entry,dict):
        return False
    manufacturer=(entry.get('manufacturer') or entry.get('brand') or entry.get('maker') or '').strip()
    material=(entry.get('material') or entry.get('product_line') or '').strip()
    color_name=(entry.get('color_name') or entry.get('color') or entry.get('name') or '').strip()
    if not manufacturer or not material or not color_name:
        return False
    if isinstance(entry.get('hexes'),list):
        for hx in entry.get('hexes'):
            if _normalize_hex(hx):
                return True
    if _normalize_hex(entry.get('hex') or entry.get('primary_hex') or ''):
        return True
    return False


def _has_usable_entries(payload):
    if not isinstance(payload,dict):
        return False
    entries=payload.get('entries')
    if not isinstance(entries,list) or not entries:
        return False
    for entry in entries:
        if _is_supported_catalog_entry(entry):
            return True
    return False


def _cache_is_fresh(payload):
    if not payload:
        return False
    try:
        generated=int(payload.get('generated_epoch') or 0)
    except (TypeError,ValueError):
        return False
    if generated<=0:
        return False
    return (int(time.time())-generated)<CATALOG_CACHE_TTL_SECONDS


def _refresh_cache_from_remote():
    raw_rows=_download_spoolman_entries()
    entries=_normalize_spoolman_entries(raw_rows)
    if not entries:
        raise ValueError('Remote catalog normalization produced zero entries')
    version=f"spoolman-{int(time.time())}"
    payload=_build_payload(entries,version,'spoolman-db')
    _write_json_file(_cache_catalog_path(),payload)
    return payload


def _build_catalog_payload(force_refresh=False):
    cache_payload=_load_cache_payload()
    cache_usable=_has_usable_entries(cache_payload)
    if (not force_refresh) and cache_payload and cache_usable and _cache_is_fresh(cache_payload):
        return cache_payload

    remote_error=None
    try:
        fresh=_refresh_cache_from_remote()
        return fresh
    except (OSError,TimeoutError,ValueError,HTTPError,URLError,json.JSONDecodeError) as ex:
        remote_error=str(ex)

    if cache_payload and cache_usable:
        stale=dict(cache_payload)
        stale['source']=f"{cache_payload.get('source','cache')}-stale"
        stale['remote_error']=remote_error
        return stale

    payload=_build_payload([],f"unavailable-{int(time.time())}",'remote-unavailable')
    payload['remote_error']=remote_error or 'Remote catalog unavailable and no usable cache is present.'
    return payload


def _build_catalog_payload_text(force_refresh=False):
    return _json_text(_build_catalog_payload(force_refresh=force_refresh))


def _catalog_update_status_message(payload):
    if not isinstance(payload,dict):
        return _getText('catalog_update_failed')
    source=str(payload.get('source') or '')
    entries=payload.get('entries') or []
    n=len(entries) if isinstance(entries,list) else 0
    if source=='spoolman-db':
        return _getText('catalog_update_success',n=n)
    if source.endswith('-stale'):
        return _getText('catalog_update_stale',n=n)
    return _getText('catalog_update_failed')


class PH(adsk.core.HTMLEventHandler):
    def notify(self, eventArgs):
        try:
            global ACTIVE_SCOPE
            app=adsk.core.Application.get()
            ui=app.userInterface

            if eventArgs.action=='request_lang':
                lang = _ensure_lang()
                _send_to_palette(ui,PALETTE_ID,'setLang',lang)
                _send_to_palette(ui,TOOLS_PALETTE_ID,'setLang',lang)
                _send_to_palette(ui,SETTINGS_PALETTE_ID,'setLang',lang)
                adsk.doEvents()
                return

            if eventArgs.action=='open_actions_palette':
                p_tools=_ensure_palette(ui,TOOLS_PALETTE_ID,_getText('palette_actions_title'),'palette_actions.html',360,420)
                p_tools.isVisible=True
                _send_to_palette(ui,TOOLS_PALETTE_ID,'setLang',_ensure_lang())
                adsk.doEvents()
                return

            if eventArgs.action=='open_settings_palette':
                p_settings=_ensure_palette(ui,SETTINGS_PALETTE_ID,_getText('palette_settings_title'),'palette_settings.html',300,280)
                p_settings.isVisible=True
                _send_to_palette(ui,SETTINGS_PALETTE_ID,'setLang',_ensure_lang())
                adsk.doEvents()
                return

            if eventArgs.action=='request_scope':
                _send_to_palette(ui,PALETTE_ID,'setScope',ACTIVE_SCOPE)
                _send_to_palette(ui,TOOLS_PALETTE_ID,'setScope',ACTIVE_SCOPE)
                adsk.doEvents()
                return

            if eventArgs.action=='set_scope':
                scope=(eventArgs.data or '').strip()
                if scope in ('body','face','component','selected_all','all_model'):
                    ACTIVE_SCOPE=scope
                    _save_scope(scope)
                _send_to_palette(ui,PALETTE_ID,'setScope',ACTIVE_SCOPE)
                _send_to_palette(ui,TOOLS_PALETTE_ID,'setScope',ACTIVE_SCOPE)
                adsk.doEvents()
                return

            if eventArgs.action=='request_filters':
                _send_to_palette(ui,PALETTE_ID,'setFilters',_json_text(_get_saved_filters()))
                adsk.doEvents()
                return

            if eventArgs.action=='save_filters':
                try:
                    payload=json.loads(eventArgs.data or '{}')
                except json.JSONDecodeError:
                    payload={}
                _save_filters(payload)
                adsk.doEvents()
                return

            if eventArgs.action=='request_catalog':
                payload=_build_catalog_payload(force_refresh=False)
                _send_to_palette(ui,PALETTE_ID,'catalog',_json_text(payload))
                adsk.doEvents()
                return

            if eventArgs.action=='request_catalog_force':
                payload=_build_catalog_payload(force_refresh=True)
                _send_to_palette(ui,PALETTE_ID,'catalog',_json_text(payload))
                _broadcast_status(ui,_catalog_update_status_message(payload))
                adsk.doEvents()
                return

            if eventArgs.action in ('export_parent_f3d','export_parent_3mf','export_parent_bundle'):
                kind='f3d' if eventArgs.action=='export_parent_f3d' else ('3mf' if eventArgs.action=='export_parent_3mf' else 'bundle')
                _, msg = export_parent(kind)
                _broadcast_status(ui,msg)
                adsk.doEvents()
                return

            if eventArgs.action!='apply':return
            # We need to cache the selection here because during the appearance copy process
            # "something" in Fusion will remove the selection, so we cache it here.
            sel = adsk.core.Application.get().userInterface.activeSelections.all
            design=adsk.fusion.Design.cast(app.activeProduct)
            d=json.loads(eventArgs.data)
            a=get_app(design,d)
            msg=apply_sel(a, ACTIVE_SCOPE, sel) if a else _getText('appearance_create_failed')
            _broadcast_status(ui,f"{_getText('native_tag')} · {d['material']} · {d['color_name']} - {msg}")
            adsk.doEvents()
            # Restore the cached selection after applying the appearance.
            adsk.core.Application.get().userInterface.activeSelections.all = sel
        except:
            pass

class CH(adsk.core.CommandCreatedEventHandler):
    def notify(self, eventArgs):
        ui=adsk.core.Application.get().userInterface
        p_catalog=_get_palette(ui,PALETTE_ID)
        if not p_catalog:
            p_catalog=_ensure_palette(ui,PALETTE_ID,_getText('palette_title'),'palette.html',520,720)
            p_catalog.isVisible=True
            adsk.doEvents()
        else:
            # Command works as a toggle: Command+B can open OR close the palette.
            next_visible=not p_catalog.isVisible
            p_catalog.isVisible=next_visible
            if not next_visible:
                p_tools=_get_palette(ui,TOOLS_PALETTE_ID)
                p_settings=_get_palette(ui,SETTINGS_PALETTE_ID)
                if p_tools:
                    p_tools.isVisible=False
                if p_settings:
                    p_settings.isVisible=False

def run(context):
    global ACTIVE_SCOPE
    ACTIVE_SCOPE=_load_saved_scope()
    app=adsk.core.Application.get()
    ui=app.userInterface
    d=ui.commandDefinitions.itemById(CMD_ID)
    if not d:
        d=ui.commandDefinitions.addButtonDefinition(
            CMD_ID,
            _getText('command_name'),
            _getText('command_description')
        )
    h=CH()
    d.commandCreated.add(h)
    handlers.append(h)

    # Add a persistent toolbar button in the Solid > Modify panel when available.
    panel=ui.allToolbarPanels.itemById('SolidModifyPanel')
    if panel and not panel.controls.itemById(CMD_ID):
        c=panel.controls.addCommand(d)
        try:
            c.isPromoted=True
        except:
            pass
        try:
            c.isPromotedByDefault=True
        except:
            pass

    # Open palette on first load.
    d.execute()

def stop(context):
    try:
        ui=adsk.core.Application.get().userInterface
        p=ui.palettes.itemById(PALETTE_ID)
        if p:
            p.deleteMe()
        p_tools=ui.palettes.itemById(TOOLS_PALETTE_ID)
        if p_tools:
            p_tools.deleteMe()
        p_settings=ui.palettes.itemById(SETTINGS_PALETTE_ID)
        if p_settings:
            p_settings.deleteMe()
        panel=ui.allToolbarPanels.itemById('SolidModifyPanel')
        if panel:
            c=panel.controls.itemById(CMD_ID)
            if c:
                c.deleteMe()
        d=ui.commandDefinitions.itemById(CMD_ID)
        if d:
            d.deleteMe()
    except:pass
