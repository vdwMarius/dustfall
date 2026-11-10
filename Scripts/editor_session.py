"""Dedicated local editor authoring host; never needed by the playable game.

Launch using -ExecCmds="py <absolute path>/Scripts/editor_session.py".
It consumes Saved/Codex/editor_command.py once and writes editor_result.txt.
Only use in the dedicated development editor, preserving other unsaved scenes.
"""
import pathlib
import traceback
import unreal

ROOT = pathlib.Path(unreal.Paths.project_dir()).resolve()
QUEUE = ROOT / 'Saved/Codex/editor_command.py'
RESULT = ROOT / 'Saved/Codex/editor_result.txt'
RESULT.parent.mkdir(parents=True, exist_ok=True)

def poll_editor_command(delta):
    if not QUEUE.exists():
        return
    source = QUEUE.read_text(encoding='utf-8')
    QUEUE.unlink()
    try:
        exec(compile(source, str(QUEUE), 'exec'), {'__name__': '__main__', 'ROOT': ROOT})
        RESULT.write_text('Editor command completed', encoding='utf-8')
    except Exception:
        RESULT.write_text(traceback.format_exc(), encoding='utf-8')
        unreal.log_error(traceback.format_exc())

_dustfall_session_callback = unreal.register_slate_post_tick_callback(poll_editor_command)
RESULT.write_text('Dedicated editor host ready', encoding='utf-8')
