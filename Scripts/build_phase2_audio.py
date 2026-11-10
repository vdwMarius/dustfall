"""Generate and import a project-owned seamless wind bed; editor authoring only."""
import array
import math
import pathlib
import random
import wave
import unreal


def build():
    source = pathlib.Path(unreal.Paths.project_saved_dir()) / 'Codex/WindBed_Phase2.wav'
    source.parent.mkdir(parents=True, exist_ok=True)
    rate, seconds = 22050, 16
    count = rate * seconds
    rng = random.Random(2042)
    # A periodic Fourier noise bed: integer periods make the loop continuous.
    # No third-party recording, voice or reference sample is used.
    harmonics = [(rng.randint(45, 5000), rng.random() * math.tau,
                  rng.uniform(.3, 1.) / math.sqrt(i + 1)) for i in range(96)]
    values = []
    for i in range(count):
        phase = math.tau * i / count
        noise = sum(math.sin(phase * k + p) * a for k, p, a in harmonics)
        envelope = .7 + .18 * math.sin(phase * 2) + .1 * math.sin(phase * 5 + .4)
        values.append(noise * envelope)
    peak = max(abs(v) for v in values)
    samples = array.array('h', (int(v / peak * 18000) for v in values))
    with wave.open(str(source), 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples.tobytes())
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = '/Game/Audio/Environment'
    task.destination_name = 'S_WindBed_Phase2'
    task.automated = True
    task.replace_existing = True
    task.save = False
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    sound = unreal.load_asset('/Game/Audio/Environment/S_WindBed_Phase2')
    if not sound:
        raise RuntimeError('Wind import failed')
    sound.set_editor_property('looping', True)
    sound.set_editor_property('volume', .4)
    unreal.EditorAssetLibrary.save_loaded_asset(sound)
    unreal.log('Imported project-owned procedural wind bed; listening validation required.')


if __name__ == '__main__':
    build()
