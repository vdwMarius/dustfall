"""Read the live habitat origin across Phase 1/3 without changing any actors.

Uses loaded actors rather than an ignored/stale authoring report. Callers must
load the home cell; missing or duplicate anchors are errors.
"""


def habitat_origin(actors):
    actors = list(actors)
    directors = [a for a in actors if a.get_actor_label() == 'Dustfall Habitat Director'
                 and 'DF_Phase3_Habitat' in [str(t) for t in a.tags]]
    if directors:
        if len(directors) != 1:
            raise RuntimeError('Expected one loaded Phase 3 habitat director')
        p = directors[0].get_editor_property('HabitatOrigin')
        return (float(p.x), float(p.y), float(p.z))
    floors = [a for a in actors if a.get_actor_label() == 'P3_Hab_Floor'
              and 'DF_Phase3_Habitat' in [str(t) for t in a.tags]]
    if floors:
        if len(floors) != 1:
            raise RuntimeError('Expected one loaded Phase 3 habitat floor')
        p = floors[0].get_actor_location()
        return (float(p.x), float(p.y), float(p.z) - 25.0)
    bases = [a for a in actors if a.get_actor_label() == 'Hab_Base_Temporary'
             and 'DF_Phase1_Habitat_Blockout' in [str(t) for t in a.tags]]
    if len(bases) != 1:
        raise RuntimeError('Load exactly one habitat origin: Phase 3 director/floor or original Phase 1 base')
    p = bases[0].get_actor_location()
    return (float(p.x), float(p.y), float(p.z) - 10.0)


def phase3_habitat_present(actors):
    return any('DF_Phase3_Habitat' in [str(t) for t in a.tags]
               and a.get_actor_label() in ['Dustfall Habitat Director', 'P3_Hab_Floor'] for a in actors)
