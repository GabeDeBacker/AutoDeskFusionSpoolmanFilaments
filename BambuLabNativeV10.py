# -*- coding: utf-8 -*-
import json
import os
import sys
import time
import importlib.util
from pathlib import Path
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
CMD_ID='BambuLabNativeV10'
handlers=[]

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

def _read_catalog_json_text():
    try:
        path=os.path.join(os.path.dirname(os.path.realpath(__file__)),'bambulab_full_catalog.json')
        with open(path,'r',encoding='utf-8') as f:
            return f.read()
    except:
        return '[]'

def _build_catalog_payload_text():
    raw=_read_catalog_json_text()
    try:
        entries=json.loads(raw)
        if not isinstance(entries,list):
            entries=[]
    except:
        entries=[]

    try:
        path=os.path.join(os.path.dirname(os.path.realpath(__file__)),'bambulab_full_catalog.json')
        mtime=int(os.path.getmtime(path))
    except:
        mtime=0

    payload={
        'schema_version':1,
        'catalog_version':str(mtime),
        'generated_epoch':int(time.time()),
        'entry_count':len(entries),
        'entries':entries
    }
    try:
        return json.dumps(payload,ensure_ascii=False)
    except:
        return '{"schema_version":1,"catalog_version":"0","generated_epoch":0,"entry_count":0,"entries":[]}'

class PH(adsk.core.HTMLEventHandler):
    def notify(self, eventArgs):
        try:
            app=adsk.core.Application.get()
            ui=app.userInterface

            if eventArgs.action=='request_lang':
                p=ui.palettes.itemById(PALETTE_ID)
                lang = _ensure_lang()
                if p:
                    p.sendInfoToHTML('setLang', lang)
                adsk.doEvents()
                return

            if eventArgs.action=='request_catalog':
                p=ui.palettes.itemById(PALETTE_ID)
                if p:
                    p.sendInfoToHTML('catalog',_build_catalog_payload_text())
                adsk.doEvents()
                return

            if eventArgs.action in ('export_parent_f3d','export_parent_3mf','export_parent_bundle'):
                kind='f3d' if eventArgs.action=='export_parent_f3d' else ('3mf' if eventArgs.action=='export_parent_3mf' else 'bundle')
                _, msg = export_parent(kind)
                p=ui.palettes.itemById(PALETTE_ID)
                if p:
                    p.sendInfoToHTML('status',msg)
                adsk.doEvents()
                return

            if eventArgs.action!='apply':return
            # We need to cache the selection here because during the appearance copy process
            # "something" in Fusion will remove the selection, so we cache it here.
            sel = adsk.core.Application.get().userInterface.activeSelections.all
            design=adsk.fusion.Design.cast(app.activeProduct)
            d=json.loads(eventArgs.data)
            a=get_app(design,d)
            msg=apply_sel(a, d.get('scope','auto'), sel) if a else _getText('appearance_create_failed')
            p=ui.palettes.itemById(PALETTE_ID)
            if p:
                p.sendInfoToHTML('status',f"{_getText('native_tag')} · {d['material']} · {d['color_name']} - {msg}")
            adsk.doEvents()
            # Restore the cached selection after applying the appearance.
            adsk.core.Application.get().userInterface.activeSelections.all = sel
        except:
            pass

class CH(adsk.core.CommandCreatedEventHandler):
    def notify(self, eventArgs):
        app=adsk.core.Application.get()
        ui=app.userInterface
        p=ui.palettes.itemById(PALETTE_ID)
        if not p:
            path=os.path.join(os.path.dirname(os.path.realpath(__file__)),'palette.html')
            palette_path=make_file_url(path)
            p=ui.palettes.add(PALETTE_ID,_getText('palette_title'),palette_path,True,True,True,520,720,True)
            p.dockingState=adsk.core.PaletteDockingStates.PaletteDockStateRight
            h=PH()
            p.incomingFromHTML.add(h)
            handlers.append(h)
            p.isVisible=True
            try:
                p.sendInfoToHTML('setLang', _ensure_lang())
                adsk.doEvents()
            except:
                pass
            try:
                p.sendInfoToHTML('catalog',_build_catalog_payload_text())
                adsk.doEvents()
            except:
                pass
        else:
            # Command works as a toggle: Command+B can open OR close the palette.
            p.isVisible=not p.isVisible

def run(context):
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
        panel=ui.allToolbarPanels.itemById('SolidModifyPanel')
        if panel:
            c=panel.controls.itemById(CMD_ID)
            if c:
                c.deleteMe()
        d=ui.commandDefinitions.itemById(CMD_ID)
        if d:
            d.deleteMe()
    except:pass
