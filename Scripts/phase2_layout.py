"""Shared editor-only route geometry in centimetres, relative to home."""


def route_polylines(cruiser):
    home_exit = [(550., 0.), (1800., 0.), (1800., 2000.)]
    wreck = (13000., 8500.)
    ruin = (32000., -23000.)
    cruiser_approach = (cruiser[0] + 12000., cruiser[1] - 1000.)
    return {
        'Home_Wreck': home_exit + [wreck],
        'Wreck_Ruin': [wreck, (18000., 6000.), ruin],
        'Home_Cruiser': home_exit + [(-2500., 2500.), cruiser_approach],
    }
