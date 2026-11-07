#!/usr/bin/env python3
"""Activity, season, expansion and event taxonomy for the grimoire.

Additive only: this module never drops or rewrites canon tables. It creates the
classification tables, seeds the catalogues, and tags existing content with a
confidence level. `unknown` is a valid outcome; nothing is guessed silently.

Four independent axes:
  expansion  major release (Forsaken, The Final Shape, ...)
  season     Bungie's official numeric season (1-26); episodes are season_type
             'episode' with their numeric slot and act
  activity   raid, dungeon, seasonal activity, story, patrol, ...
  event      rotating real-world event (Festival of the Lost, The Dawning, ...)
"""
import re
import sqlite3

SCHEMA_VERSION = '1.5.0'

# Activity facet keys emitted by the game-caption extraction
# (caption_activity.py NARRATOR/ACTIVITY_PAT keys) -> taxonomy slugs.
# Caption records carry the extraction key; transcript_classification stores
# the taxonomy slug, so the two vocabularies meet here - never in the loader.
CAPTION_ACTIVITY_SLUGS = {
    'gambit': 'gambit',
    'crucible': 'crucible',
    'menagerie': 'menagerie',
    'trials_osiris': 'trials-of-osiris',
    'trials_nine': 'trials-of-the-nine',
}

# --------------------------------------------------------------------------
# Expansions
# --------------------------------------------------------------------------
EXPANSIONS = [
    # slug, name, game, year, release_date, vaulted
    ('destiny-1', 'Destiny', 'Destiny 1', 2014, '2014-09-09', 0),
    ('the-dark-below', 'The Dark Below', 'Destiny 1', 2014, '2014-12-09', 0),
    ('house-of-wolves', 'House of Wolves', 'Destiny 1', 2015, '2015-05-19', 0),
    ('the-taken-king', 'The Taken King', 'Destiny 1', 2015, '2015-09-15', 0),
    ('rise-of-iron', 'Rise of Iron', 'Destiny 1', 2016, '2016-09-20', 0),
    ('age-of-triumph', 'Age of Triumph', 'Destiny 1', 2017, '2017-03-28', 0),
    ('destiny-2', 'Destiny 2', 'Destiny 2', 2017, '2017-09-06', 0),
    ('curse-of-osiris', 'Curse of Osiris', 'Destiny 2', 2017, '2017-12-05', 1),
    ('warmind', 'Warmind', 'Destiny 2', 2018, '2018-05-08', 1),
    ('forsaken', 'Forsaken', 'Destiny 2', 2018, '2018-09-04', 1),
    ('shadowkeep', 'Shadowkeep', 'Destiny 2', 2019, '2019-10-01', 0),
    ('beyond-light', 'Beyond Light', 'Destiny 2', 2020, '2020-11-10', 0),
    ('30th-anniversary', 'Bungie 30th Anniversary', 'Destiny 2', 2021, '2021-12-07', 0),
    ('the-witch-queen', 'The Witch Queen', 'Destiny 2', 2022, '2022-02-22', 0),
    ('lightfall', 'Lightfall', 'Destiny 2', 2023, '2023-02-28', 0),
    ('the-final-shape', 'The Final Shape', 'Destiny 2', 2024, '2024-06-04', 0),
    ('the-edge-of-fate', 'The Edge of Fate', 'Destiny 2', 2025, '2025-07-15', 0),
    ('renegades', 'Renegades', 'Destiny 2', 2025, '2025-12-02', 0),
]

# Destiny 1 has no numbered seasons. A D1 expansion must never inherit a D2
# season from an activity that was later reprised (Vault of Glass, King's Fall).
D1_EXPANSIONS = {
    'destiny-1', 'the-dark-below', 'house-of-wolves', 'the-taken-king',
    'rise-of-iron', 'age-of-triumph',
}

# --------------------------------------------------------------------------
# Seasons / episodes. Bungie's official numeric season slot.
# --------------------------------------------------------------------------
SEASONS = [
    # number, slug, name, type, act, destiny_year, expansion, start, end, vaulted
    (1, 'season-1', 'Season 1', 'season', None, 1, 'destiny-2', '2017-09-06', '2017-12-04', 1),
    (2, 'season-2', 'Season 2', 'season', None, 1, 'curse-of-osiris', '2017-12-05', '2018-05-07', 1),
    (3, 'season-3', 'Season 3', 'season', None, 1, 'warmind', '2018-05-08', '2018-09-03', 1),
    (4, 'season-4', 'Season 4', 'season', None, 1, 'forsaken', '2018-09-04', '2018-12-03', 1),
    (5, 'season-of-the-forge', 'Season of the Forge', 'season', None, 2, 'forsaken', '2018-12-04', '2019-03-04', 1),
    (6, 'season-of-the-drifter', "Season of the Drifter", 'season', None, 2, 'forsaken', '2019-03-05', '2019-06-03', 1),
    (7, 'season-of-opulence', 'Season of Opulence', 'season', None, 2, 'forsaken', '2019-06-04', '2019-09-30', 1),
    (8, 'season-of-the-undying', 'Season of the Undying', 'season', None, 3, 'shadowkeep', '2019-10-01', '2019-12-09', 1),
    (9, 'season-of-dawn', 'Season of Dawn', 'season', None, 3, 'shadowkeep', '2019-12-10', '2020-03-09', 1),
    (10, 'season-of-the-worthy', 'Season of the Worthy', 'season', None, 3, 'shadowkeep', '2020-03-10', '2020-06-08', 1),
    (11, 'season-of-arrivals', 'Season of Arrivals', 'season', None, 3, 'shadowkeep', '2020-06-09', '2020-11-09', 1),
    (12, 'season-of-the-hunt', 'Season of the Hunt', 'season', None, 4, 'beyond-light', '2020-11-10', '2021-02-08', 1),
    (13, 'season-of-the-chosen', 'Season of the Chosen', 'season', None, 4, 'beyond-light', '2021-02-09', '2021-05-10', 1),
    (14, 'season-of-the-splicer', 'Season of the Splicer', 'season', None, 4, 'beyond-light', '2021-05-11', '2021-08-23', 1),
    (15, 'season-of-the-lost', 'Season of the Lost', 'season', None, 4, 'beyond-light', '2021-08-24', '2022-02-21', 1),
    (16, 'season-of-the-risen', 'Season of the Risen', 'season', None, 5, 'the-witch-queen', '2022-02-22', '2022-05-23', 1),
    (17, 'season-of-the-haunted', 'Season of the Haunted', 'season', None, 5, 'the-witch-queen', '2022-05-24', '2022-08-22', 1),
    (18, 'season-of-plunder', 'Season of Plunder', 'season', None, 5, 'the-witch-queen', '2022-08-23', '2022-12-05', 1),
    (19, 'season-of-the-seraph', 'Season of the Seraph', 'season', None, 5, 'the-witch-queen', '2022-12-06', '2023-02-27', 1),
    (20, 'season-of-defiance', 'Season of Defiance', 'season', None, 6, 'lightfall', '2023-02-28', '2023-05-22', 1),
    (21, 'season-of-the-deep', 'Season of the Deep', 'season', None, 6, 'lightfall', '2023-05-23', '2023-08-21', 1),
    (22, 'season-of-the-witch', 'Season of the Witch', 'season', None, 6, 'lightfall', '2023-08-22', '2023-11-27', 1),
    (23, 'season-of-the-wish', 'Season of the Wish', 'season', None, 6, 'lightfall', '2023-11-28', '2024-06-03', 1),
    (24, 'episode-echoes', 'Episode: Echoes', 'episode', None, 7, 'the-final-shape', '2024-06-04', '2024-10-07', 1),
    (25, 'episode-revenant', 'Episode: Revenant', 'episode', None, 7, 'the-final-shape', '2024-10-08', '2025-02-03', 1),
    (26, 'episode-heresy', 'Episode: Heresy', 'episode', None, 7, 'the-final-shape', '2025-02-04', '2025-07-14', 1),
    (27, 'season-reclamation', 'Season: Reclamation', 'season', None, 8, 'the-edge-of-fate', '2025-07-15', '2025-12-02', 0),
    (28, 'monument-of-triumph', 'Monument of Triumph', 'season', None, 8, 'renegades', '2025-12-02', '2099-01-01', 0),
]

# season slug -> parent expansion slug, used when only the season is explicit.
SEASON_EXPANSION = {row[1]: row[6] for row in SEASONS}

# Episode acts (additive detail; seasons stay the numeric axis)
EPISODE_ACTS = [
    ('episode-echoes', 1, '2024-06-04', '2024-07-09'),
    ('episode-echoes', 2, '2024-07-09', '2024-08-13'),
    ('episode-echoes', 3, '2024-08-13', '2024-10-07'),
    ('episode-revenant', 1, '2024-10-08', '2024-11-12'),
    ('episode-revenant', 2, '2024-11-12', '2024-12-17'),
    ('episode-revenant', 3, '2024-12-17', '2025-02-03'),
    ('episode-heresy', 1, '2025-02-04', '2025-03-11'),
    ('episode-heresy', 2, '2025-03-11', '2025-04-15'),
    ('episode-heresy', 3, '2025-04-15', '2025-07-14'),
]

# --------------------------------------------------------------------------
# Activities. Type is one of:
#   raid, dungeon, seasonal, story, patrol, exotic_mission, strike, crucible,
#   gambit, public_event, lost_sector, quest, event, other
# --------------------------------------------------------------------------
ACTIVITIES = [
    # slug, name, type, expansion, season, event, vaulted, keywords
    ('leviathan', 'Leviathan', 'raid', 'destiny-2', 'season-1', None, 1,
     ['leviathan raid', 'the leviathan']),
    ('eater-of-worlds', 'Eater of Worlds', 'raid', 'curse-of-osiris', 'season-2', None, 1,
     ['eater of worlds']),
    ('spire-of-stars', 'Spire of Stars', 'raid', 'warmind', 'season-3', None, 1,
     ['spire of stars']),
    ('last-wish', 'Last Wish', 'raid', 'forsaken', 'season-4', None, 0,
     ['last wish']),
    ('scourge-of-the-past', 'Scourge of the Past', 'raid', 'forsaken', 'season-of-the-forge', None, 1,
     ['scourge of the past']),
    ('crown-of-sorrow', 'Crown of Sorrow', 'raid', 'forsaken', 'season-of-opulence', None, 1,
     ['crown of sorrow']),
    ('garden-of-salvation', 'Garden of Salvation', 'raid', 'shadowkeep', 'season-of-the-undying', None, 0,
     ['garden of salvation']),
    ('deep-stone-crypt', 'Deep Stone Crypt', 'raid', 'beyond-light', 'season-of-the-hunt', None, 0,
     ['deep stone crypt', 'deepstone crypt']),
    ('vault-of-glass', 'Vault of Glass', 'raid', 'the-witch-queen', 'season-of-the-splicer', None, 0,
     ['vault of glass']),
    ('vow-of-the-disciple', 'Vow of the Disciple', 'raid', 'the-witch-queen', 'season-of-the-risen', None, 0,
     ['vow of the disciple']),
    ('kings-fall', "King's Fall", 'raid', 'the-witch-queen', 'season-of-plunder', None, 0,
     ["king's fall", 'kings fall']),
    ('root-of-nightmares', 'Root of Nightmares', 'raid', 'lightfall', 'season-of-defiance', None, 0,
     ['root of nightmares']),
    ('crotas-end', "Crota's End", 'raid', 'lightfall', 'season-of-the-witch', None, 0,
     ["crota's end", 'crotas end']),
    ('salvations-edge', "Salvation's Edge", 'raid', 'the-final-shape', 'episode-echoes', None, 0,
     ["salvation's edge", 'salvations edge']),
    ('wrath-of-the-machine', 'Wrath of the Machine', 'raid', 'rise-of-iron', None, None, 1,
     ['wrath of the machine']),

    ('the-shattered-throne', 'The Shattered Throne', 'dungeon', 'forsaken', 'season-4', None, 0,
     ['shattered throne']),
    ('pit-of-heresy', 'Pit of Heresy', 'dungeon', 'shadowkeep', 'season-of-the-undying', None, 0,
     ['pit of heresy', 'lingering torment']),
    ('prophecy', 'Prophecy', 'dungeon', 'shadowkeep', 'season-of-arrivals', None, 0,
     ['prophecy dungeon', 'the prophecy']),
    ('grasp-of-avarice', 'Grasp of Avarice', 'dungeon', '30th-anniversary', 'season-of-the-lost', None, 0,
     ['grasp of avarice']),
    ('duality', 'Duality', 'dungeon', 'the-witch-queen', 'season-of-the-haunted', None, 0,
     ['duality dungeon', 'duality']),
    ('spire-of-the-watcher', 'Spire of the Watcher', 'dungeon', 'the-witch-queen', 'season-of-the-seraph', None, 0,
     ['spire of the watcher']),
    ('ghosts-of-the-deep', 'Ghosts of the Deep', 'dungeon', 'lightfall', 'season-of-the-deep', None, 0,
     ['ghosts of the deep']),
    ('warlords-ruin', "Warlord's Ruin", 'dungeon', 'lightfall', 'season-of-the-wish', None, 0,
     ["warlord's ruin", 'warlords ruin']),
    ('vespers-host', "Vesper's Host", 'dungeon', 'the-final-shape', 'episode-echoes', None, 0,
     ["vesper's host", 'vespers host']),
    ('sundered-doctrine', 'Sundered Doctrine', 'dungeon', 'the-final-shape', 'episode-heresy', None, 0,
     ['sundered doctrine']),

    ('forge-ignitions', 'Forge Ignitions', 'seasonal', 'forsaken', 'season-of-the-forge', None, 1,
     ['forge ignition', 'black armory forge', 'gofannon forge']),
    ('the-reckoning', 'The Reckoning', 'seasonal', 'forsaken', 'season-of-the-drifter', None, 1,
     ['the reckoning', 'reckoning']),
    ('menagerie', 'The Menagerie', 'seasonal', 'forsaken', 'season-of-opulence', None, 1,
     ['menagerie']),
    ('vex-offensive', 'Vex Offensive', 'seasonal', 'shadowkeep', 'season-of-the-undying', None, 1,
     ['vex offensive']),
    ('sundial', 'The Sundial', 'seasonal', 'shadowkeep', 'season-of-dawn', None, 1,
     ['the sundial', 'sundial']),
    ('seraph-towers', 'Seraph Towers', 'public_event', 'shadowkeep', 'season-of-the-worthy', None, 1,
     ['seraph tower', 'seraph towers']),
    ('contact', 'Contact', 'public_event', 'shadowkeep', 'season-of-arrivals', None, 1,
     ['contact public event']),
    ('wrathborn-hunts', 'Wrathborn Hunts', 'seasonal', 'beyond-light', 'season-of-the-hunt', None, 1,
     ['wrathborn hunt', 'hunt for the wrathborn', 'wrathborn']),
    ('battlegrounds-chosen', 'Battlegrounds', 'seasonal', 'beyond-light', 'season-of-the-chosen', None, 1,
     ['battlegrounds']),
    ('override', 'Override', 'seasonal', 'beyond-light', 'season-of-the-splicer', None, 1,
     ['override']),
    ('expunge', 'Expunge', 'seasonal', 'beyond-light', 'season-of-the-splicer', None, 1,
     ['expunge']),
    ('astral-alignment', 'Astral Alignment', 'seasonal', 'beyond-light', 'season-of-the-lost', None, 1,
     ['astral alignment']),
    ('shattered-realm', 'Shattered Realm', 'seasonal', 'beyond-light', 'season-of-the-lost', None, 1,
     ['shattered realm']),
    ('psiops-battlegrounds', 'PsiOps Battlegrounds', 'seasonal', 'the-witch-queen', 'season-of-the-risen', None, 1,
     ['psiops battlegrounds', 'psiops']),
    ('nightmare-hunts', 'Nightmare Hunts', 'seasonal', 'shadowkeep', 'season-of-the-undying', None, 1,
     ['nightmare hunt']),
    ('empire-hunts', 'Empire Hunts', 'seasonal', 'beyond-light', 'season-of-the-hunt', None, 1,
     ['empire hunt']),
    ('derelict-leviathan', 'Derelict Leviathan', 'patrol', 'the-witch-queen', 'season-of-the-haunted', None, 1,
     ['derelict leviathan', 'leviathan returns']),
    ('nightmare-containment', 'Nightmare Containment', 'seasonal', 'the-witch-queen', 'season-of-the-haunted', None, 1,
     ['nightmare containment']),
    ('sever', 'Sever', 'seasonal', 'the-witch-queen', 'season-of-the-haunted', None, 1,
     ['sever ', 'sever-', 'sever:']),
    ('ketchcrash', 'Ketchcrash', 'seasonal', 'the-witch-queen', 'season-of-plunder', None, 1,
     ['ketchcrash']),
    ('expedition', 'Expedition', 'seasonal', 'the-witch-queen', 'season-of-plunder', None, 1,
     ['expedition']),
    ('heist-battlegrounds', 'Heist Battlegrounds', 'seasonal', 'the-witch-queen', 'season-of-the-seraph', None, 1,
     ['heist battleground']),
    ('defiant-battlegrounds', 'Defiant Battlegrounds', 'seasonal', 'lightfall', 'season-of-defiance', None, 1,
     ['defiant battleground']),
    ('deep-dives', 'Deep Dives', 'seasonal', 'lightfall', 'season-of-the-deep', None, 1,
     ['deep dive']),
    ('salvage', 'Salvage', 'seasonal', 'lightfall', 'season-of-the-deep', None, 1,
     ['salvage']),
    ('altars-of-summoning', 'Altars of Summoning', 'seasonal', 'lightfall', 'season-of-the-witch', None, 1,
     ['altars of summoning']),
    ('the-coil', 'The Coil', 'seasonal', 'lightfall', 'season-of-the-witch', None, 1,
     ['the coil']),
    ('rivens-lair', "Riven's Lair", 'seasonal', 'lightfall', 'season-of-the-wish', None, 1,
     ["riven's lair", 'rivens lair']),
    ('breach-executable', 'Breach Executable', 'seasonal', 'the-final-shape', 'episode-echoes', None, 0,
     ['breach executable']),
    ('onslaught-salvation', 'Onslaught: Salvation', 'seasonal', 'the-final-shape', 'episode-revenant', None, 0,
     ['onslaught: salvation', 'onslaught salvation']),
    ('tomb-of-elders', 'Tomb of Elders', 'seasonal', 'the-final-shape', 'episode-revenant', None, 0,
     ['tomb of elders']),
    ('the-nether', 'The Nether', 'seasonal', 'the-final-shape', 'episode-heresy', None, 0,
     ['the nether']),
    ('court-of-blades', 'Court of Blades', 'seasonal', 'the-final-shape', 'episode-heresy', None, 0,
     ['court of blades']),

    ('presage', 'Presage', 'exotic_mission', 'beyond-light', 'season-of-the-chosen', None, 1,
     ['presage']),
    ('harbinger', 'Harbinger', 'exotic_mission', 'beyond-light', 'season-of-the-hunt', None, 1,
     ['harbinger']),
    ('the-lament', 'The Lament', 'exotic_mission', 'beyond-light', 'season-of-the-hunt', None, 1,
     ['the lament']),
    ('vox-obscura', 'Vox Obscura', 'exotic_mission', 'the-witch-queen', 'season-of-the-risen', None, 1,
     ['vox obscura']),
    ('seraphs-shield', "Seraph's Shield", 'exotic_mission', 'the-witch-queen', 'season-of-the-seraph', None, 1,
     ["seraph's shield", 'seraphs shield']),
    ('starcrossed', 'Starcrossed', 'exotic_mission', 'lightfall', 'season-of-the-wish', None, 1,
     ['starcrossed']),
    ('enigma-protocol', 'Enigma Protocol', 'exotic_mission', 'the-final-shape', 'episode-echoes', None, 0,
     ['enigma protocol']),
    ('encore', 'Encore', 'exotic_mission', 'the-final-shape', 'episode-echoes', None, 0,
     ['encore']),
    ('kells-fall', "Kell's Fall", 'exotic_mission', 'the-final-shape', 'episode-revenant', None, 0,
     ["kell's fall", 'kells fall']),

    # PvP playlists. Added so `--activity gambit` / `trials-of-osiris` resolve:
    # the Season of Arrivals caption extraction attributes in-match callouts to
    # these narrators (Drifter / Shaxx / Vance / Emissary). `crucible` and
    # `gambit` are documented activity types in this file's header comment.
    ('crucible', 'Crucible', 'crucible', 'destiny-2', None, None, 0,
     ['crucible']),
    ('gambit', 'Gambit', 'gambit', 'forsaken', None, None, 0,
     ['gambit']),
    ('trials-of-the-nine', 'Trials of the Nine', 'crucible', 'destiny-2', None, None, 1,
     ['trials of the nine']),
    ('trials-of-osiris', 'Trials of Osiris', 'crucible', 'shadowkeep', 'season-of-arrivals', None, 0,
     ['trials of osiris']),
]

# --------------------------------------------------------------------------
# Coverage notes. These explain a zero-coverage gap instead of leaving it
# ambiguous. Statuses:
#   no_dialogue              confirmed to have no spoken content
#   narration_only           transcript exists, but it has no speaker lines
#   dialogue_source_missing  dialogue exists, but no full transcript source
#   partial_transcript       verified dialogue exists, but coverage is incomplete
#   unverified               catalogued, no source checked yet
# --------------------------------------------------------------------------
COVERAGE_NOTES = [
    ('activity', 'crotas-end', 'no_dialogue',
     'Encounter transcript has no speaker lines; no spoken-dialogue source found.',
     'https://commons.ishtar-collective.net/t/3557'),
    ('activity', 'wrath-of-the-machine', 'no_dialogue',
     'Encounter transcript has no speaker lines; no spoken-dialogue source found.',
     'https://commons.ishtar-collective.net/t/3549'),
    ('activity', 'ketchcrash', 'partial_transcript',
     '38 verified lines from 12 activity dialogue videos; reviewed, not guaranteed exhaustive.',
     'https://www.youtube.com/watch?v=2A4-CoDnrLs'),
    ('activity', 'psiops-battlegrounds', 'partial_transcript',
     '51 verified lines from 15 videos across Moon, EDZ and Cosmodrome; not guaranteed exhaustive.',
     'https://www.youtube.com/watch?v=6cVt1oKZYTE'),
    ('activity', 'defiant-battlegrounds', 'partial_transcript',
     '73 verified lines from 24 videos across three battlegrounds; not guaranteed exhaustive.',
     'https://www.youtube.com/watch?v=yVA1_QDIO4E'),
    ('activity', 'expedition', 'partial_transcript',
     '35 verified lines from 12 videos across four destinations; not guaranteed exhaustive.',
     'https://www.youtube.com/watch?v=ayBfs8RVtSA'),
    ('event', 'bungie-day', 'no_dialogue',
     'Real-world community celebration; no in-game spoken content.', ''),
    ('event', 'moments-of-triumph', 'no_dialogue',
     'Annual triumph and seal retrospective; no spoken content.', ''),
    ('season', 'season-reclamation', 'partial_transcript',
     '27 verified lines from 19 Solo Ops, Heliostat and idle-dialogue videos; not guaranteed exhaustive.',
     'https://www.youtube.com/watch?v=B9vuLz3weH0'),
    ('season', 'monument-of-triumph', 'partial_transcript',
     '202 auto-captioned lines across 10 chapters; speaker labels from chapters, not verbatim-reviewed.',
     'https://www.youtube.com/watch?v=WD2wRN0It0E'),
]

# --------------------------------------------------------------------------
# Rotating events
# --------------------------------------------------------------------------
EVENTS = [
    # slug, name, type, first_year, last_year, recurring, vaulted, notes
    ('festival-of-the-lost', 'Festival of the Lost', 'seasonal_event', 2018, 2025, 1, 0,
     'Halloween event; Haunted Forest, then Festival activities.'),
    ('the-dawning', 'The Dawning', 'seasonal_event', 2016, 2025, 1, 0,
     'Winter event; Dawning Delights, Eva Levante, sparrows and shaders.'),
    ('solstice', 'Solstice', 'seasonal_event', 2018, 2025, 1, 0,
     'Formerly Solstice of Heroes; armor rekindling and EAZ.'),
    ('guardian-games', 'Guardian Games', 'seasonal_event', 2020, 2025, 1, 0,
     'Class competition event.'),
    ('crimson-days', 'Crimson Days', 'seasonal_event', 2018, 2020, 0, 1,
     'Removed Valentine event; Crimson Doubles.'),
    ('the-revelry', 'The Revelry', 'seasonal_event', 2019, 2019, 0, 1,
     'Removed spring event; Verdant Forest and Reveler\'s Tonic.'),
    ('moments-of-triumph', 'Moments of Triumph', 'seasonal_event', 2015, 2025, 1, 0,
     'Annual triumph seal and retrospective.'),
    ('bungie-day', 'Bungie Day', 'community', 2013, 2025, 1, 0,
     'Community celebration on 7 July.'),
    ('iron-banner', 'Iron Banner', 'crucible', 2014, 2025, 1, 0,
     'Recurring Crucible event; not a seasonal story event.'),
]

# Event occurrences: (event_slug, year, season_slug, start, end, vaulted)
EVENT_OCCURRENCES = [
    ('festival-of-the-lost', 2018, 'season-4', '2018-10-16', '2018-11-06', 1),
    ('festival-of-the-lost', 2019, 'season-of-the-undying', '2019-10-29', '2019-11-19', 1),
    ('festival-of-the-lost', 2020, 'season-of-arrivals', '2020-10-06', '2020-11-03', 1),
    ('festival-of-the-lost', 2021, 'season-of-the-lost', '2021-10-12', '2021-11-02', 1),
    ('festival-of-the-lost', 2022, 'season-of-plunder', '2022-10-18', '2022-11-08', 1),
    ('festival-of-the-lost', 2023, 'season-of-the-witch', '2023-10-17', '2023-11-07', 1),
    ('festival-of-the-lost', 2024, 'episode-revenant', '2024-10-29', '2024-11-19', 1),
    ('festival-of-the-lost', 2025, None, '2025-10-14', '2025-11-04', 0),

    ('the-dawning', 2016, None, '2016-12-13', '2017-01-03', 1),
    ('the-dawning', 2017, 'season-2', '2017-12-12', '2018-01-09', 1),
    ('the-dawning', 2018, 'season-of-the-forge', '2018-12-11', '2019-01-08', 1),
    ('the-dawning', 2019, 'season-of-dawn', '2019-12-10', '2020-01-07', 1),
    ('the-dawning', 2020, 'season-of-the-hunt', '2020-12-08', '2021-01-05', 1),
    ('the-dawning', 2021, 'season-of-the-lost', '2021-12-07', '2022-01-04', 1),
    ('the-dawning', 2022, 'season-of-the-seraph', '2022-12-06', '2023-01-03', 1),
    ('the-dawning', 2023, 'season-of-the-wish', '2023-12-05', '2024-01-02', 1),
    ('the-dawning', 2024, 'episode-revenant', '2024-12-10', '2025-01-07', 1),
    ('the-dawning', 2025, None, '2025-12-09', '2026-01-06', 0),

    ('solstice', 2018, 'season-4', '2018-07-31', '2018-08-28', 1),
    ('solstice', 2019, 'season-of-opulence', '2019-07-30', '2019-08-27', 1),
    ('solstice', 2020, 'season-of-arrivals', '2020-08-11', '2020-09-08', 1),
    ('solstice', 2021, 'season-of-the-lost', '2021-07-06', '2021-08-03', 1),
    ('solstice', 2022, 'season-of-the-haunted', '2022-07-19', '2022-08-16', 1),
    ('solstice', 2023, 'season-of-the-deep', '2023-07-18', '2023-08-15', 1),
    ('solstice', 2024, 'episode-echoes', '2024-08-06', '2024-09-03', 1),
    ('solstice', 2025, None, '2025-07-15', '2025-08-12', 0),

    ('guardian-games', 2020, 'season-of-the-worthy', '2020-04-21', '2020-05-12', 1),
    ('guardian-games', 2021, 'season-of-the-chosen', '2021-04-20', '2021-05-11', 1),
    ('guardian-games', 2022, 'season-of-the-risen', '2022-05-03', '2022-05-24', 1),
    ('guardian-games', 2023, 'season-of-defiance', '2023-05-02', '2023-05-23', 1),
    ('guardian-games', 2024, 'episode-echoes', '2024-06-04', '2024-06-25', 1),
    ('guardian-games', 2025, 'episode-heresy', '2025-04-22', '2025-05-13', 0),

    ('crimson-days', 2018, 'season-2', '2018-02-13', '2018-02-20', 1),
    ('crimson-days', 2019, 'season-of-the-forge', '2019-02-12', '2019-02-19', 1),
    ('crimson-days', 2020, 'season-of-dawn', '2020-02-11', '2020-02-18', 1),

    ('the-revelry', 2019, 'season-of-the-drifter', '2019-04-16', '2019-05-07', 1),

    ('moments-of-triumph', 2015, 'the-taken-king', '2015-06-30', '2015-09-14', 1),
    ('moments-of-triumph', 2016, 'rise-of-iron', '2016-07-08', '2016-09-19', 1),
    ('moments-of-triumph', 2017, 'age-of-triumph', '2017-03-28', '2017-08-31', 1),
    ('moments-of-triumph', 2018, 'season-4', '2018-07-31', '2018-08-28', 1),
    ('moments-of-triumph', 2019, 'season-of-opulence', '2019-07-02', '2019-08-27', 1),
    ('moments-of-triumph', 2020, 'season-of-arrivals', '2020-07-14', '2020-09-22', 1),
    ('moments-of-triumph', 2021, 'season-of-the-lost', '2021-07-06', '2021-08-24', 1),
    ('moments-of-triumph', 2022, 'season-of-plunder', '2022-07-19', '2022-08-23', 1),
    ('moments-of-triumph', 2023, 'season-of-the-deep', '2023-07-18', '2023-08-22', 1),
    ('moments-of-triumph', 2024, 'episode-echoes', '2024-07-09', '2024-08-06', 1),
    ('moments-of-triumph', 2025, 'episode-heresy', '2025-06-17', '2025-07-15', 0),
]

# --------------------------------------------------------------------------
# Matching helpers
# --------------------------------------------------------------------------
SEASON_NUMBER = {row[1]: row[0] for row in SEASONS}
SEASON_BY_NUMBER = {row[0]: row[1] for row in SEASONS}
EXPANSION_NAMES = {row[0]: row[1] for row in EXPANSIONS}

# Distinctive season phrases. Short generic words are deliberately excluded;
# a season is only derived from a title when the phrase is unambiguous.
SEASON_PHRASES = [
    ('season of the forge', 'season-of-the-forge'),
    ('season of the drifter', 'season-of-the-drifter'),
    ('season of opulence', 'season-of-opulence'),
    ('season of the undying', 'season-of-the-undying'),
    ('season of dawn', 'season-of-dawn'),
    ('season of the worthy', 'season-of-the-worthy'),
    ('season of arrivals', 'season-of-arrivals'),
    ('season of the hunt', 'season-of-the-hunt'),
    ('season of the chosen', 'season-of-the-chosen'),
    ('season of the splicer', 'season-of-the-splicer'),
    ('season of the lost', 'season-of-the-lost'),
    ('season of the risen', 'season-of-the-risen'),
    ('season of the haunted', 'season-of-the-haunted'),
    ('season of plunder', 'season-of-plunder'),
    ('season of the seraph', 'season-of-the-seraph'),
    ('season of defiance', 'season-of-defiance'),
    ('season of the deep', 'season-of-the-deep'),
    ('season of the witch', 'season-of-the-witch'),
    ('season of the wish', 'season-of-the-wish'),
    ('episode: echoes', 'episode-echoes'),
    ('episode echoes', 'episode-echoes'),
    ('episode: revenant', 'episode-revenant'),
    ('episode revenant', 'episode-revenant'),
    ('episode: heresy', 'episode-heresy'),
    ('episode heresy', 'episode-heresy'),
    ('monument of triumph', 'monument-of-triumph'),
    ('season reclamation', 'season-reclamation'),
]

EXPANSION_PHRASES = [
    ('the dark below', 'the-dark-below'),
    ('house of wolves', 'house-of-wolves'),
    ('the taken king', 'the-taken-king'),
    ('rise of iron', 'rise-of-iron'),
    ('age of triumph', 'age-of-triumph'),
    ('curse of osiris', 'curse-of-osiris'),
    ('warmind', 'warmind'),
    ('forsaken', 'forsaken'),
    ('shadowkeep', 'shadowkeep'),
    ('beyond light', 'beyond-light'),
    ('30th anniversary', '30th-anniversary'),
    ('the witch queen', 'the-witch-queen'),
    ('lightfall', 'lightfall'),
    ('the final shape', 'the-final-shape'),
    ('the edge of fate', 'the-edge-of-fate'),
    ('edge of fate', 'the-edge-of-fate'),
    ('renegades', 'renegades'),
    # Base-game phrases last: specific releases must win first.
    ('destiny 2', 'destiny-2'),
    ('destiny 1', 'destiny-1'),
]

EVENT_PHRASES = [
    ('festival of the lost', 'festival-of-the-lost'),
    ('haunted forest', 'festival-of-the-lost'),
    ('the dawning', 'the-dawning'),
    ('dawning', 'the-dawning'),
    ('solstice of heroes', 'solstice'),
    ('solstice', 'solstice'),
    ('guardian games', 'guardian-games'),
    ('crimson days', 'crimson-days'),
    ('crimson doubles', 'crimson-days'),
    ('the revelry', 'the-revelry'),
    ('revelry', 'the-revelry'),
    ('moments of triumph', 'moments-of-triumph'),
    ('bungie day', 'bungie-day'),
    ('iron banner', 'iron-banner'),
]


# Confident story-arc -> season/expansion links. These are named narrative
# arcs, not guesses from generic words; anything uncertain stays unknown.
STORY_ARC_SEASONS = [
    ('into the depths', 'season-of-the-deep'),
    ('beneath the waves', 'season-of-the-deep'),
    ('echoed warnings', 'episode-echoes'),
    ('rites of the deep', 'episode-heresy'),
    ('wayfinder', 'season-of-the-lost'),
    ('wishing all the best', 'season-of-the-wish'),
    ('a rising tide', 'season-of-the-splicer'),
    ('awaken, queensguard', 'season-of-the-lost'),
    ('parting the veil', 'season-of-the-splicer'),
    ('semaphore signals', 'season-of-plunder'),
    ("challenger's proving", 'season-of-the-chosen'),
    ('depth reception', 'season-of-the-deep'),
]
STORY_ARC_EXPANSIONS = [
    ('born in darkness', 'beyond-light'),
]

DATE_RE = re.compile(r'(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})')
SEASON_NUM_RE = re.compile(r'\bseason (\d{1,2})\b')


def season_for_date(iso_date):
    for num, slug, name, stype, act, dyear, exp, start, end, vaulted in SEASONS:
        if start and end and start <= iso_date <= end:
            return slug
    return None


def season_for_release(release):
    """Infer a season from a single dated release string (ranges are skipped)."""
    if not release:
        return None
    dates = DATE_RE.findall(release)
    if len(dates) != 1:
        return None
    y, m, d = dates[0]
    return season_for_date(f'{int(y):04d}-{int(m):02d}-{int(d):02d}')


def act_from_title(title):
    m = re.search(r'\bact (i{1,3})\b', norm(title))
    if not m:
        return None
    return {'i': 1, 'ii': 2, 'iii': 3}[m.group(1)]


def norm(value):
    value = (value or '').lower()
    value = value.replace('\u2019', "'").replace('\u2014', '-').replace('\u2013', '-')
    value = re.sub(r'[^a-z0-9: ]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def _match_phrase(text, phrases):
    for phrase, slug in phrases:
        if phrase in text:
            return slug
    return None


def classify(slug='', title='', release='', arc='', characters='', kind='transcript'):
    """Classify one item. Returns activity/season/event/expansion + confidence.

    Explicit metadata (release/arc) outranks derived title matching. Activity
    catalogues supply season/expansion when the activity is unambiguous.
    """
    text = norm(' '.join((slug or '', title or '', release or '', arc or '')))
    meta = norm(' '.join((release or '', arc or '')))
    title_text = norm(' '.join((slug or '', title or '')))
    if not text:
        return _result(kind=kind)

    activity = None
    evidence = []
    confidence = 'unknown'

    # 1. Activity, longest keyword first so "nightmare containment" beats "leviathan".
    best = None
    for row in ACTIVITIES:
        for kw in row[7]:
            # Keywords are authored in display form ("Crota's End"), but `text`
            # is normalized (apostrophes become spaces). Normalize the keyword
            # too so possessive activity names match.
            nkw = norm(kw)
            if nkw and nkw in text:
                if best is None or len(nkw) > best[0]:
                    best = (len(nkw), row, kw)
    if best:
        _, row, kw = best
        activity = row[0]
        evidence.append(f'activity:{kw}')

    # 2. Event
    event = _match_phrase(text, EVENT_PHRASES)
    if event:
        evidence.append(f'event:{event}')

    # 3. Season from explicit metadata, then distinctive title phrase.
    season = None
    if meta:
        season = _match_phrase(meta, SEASON_PHRASES)
        if season:
            confidence = 'explicit'
            evidence.append(f'season:{season}@meta')
    if not season:
        season = _match_phrase(title_text, SEASON_PHRASES)
        if season:
            evidence.append(f'season:{season}@title')
    if not season:
        m = SEASON_NUM_RE.search(text)
        if m and int(m.group(1)) in SEASON_BY_NUMBER:
            season = SEASON_BY_NUMBER[int(m.group(1))]
            evidence.append(f'season:{season}@number')
    if not season:
        season = _match_phrase(text, STORY_ARC_SEASONS)
        if season:
            evidence.append(f'season:{season}@arc')
    if not season:
        season = season_for_release(release)
        if season:
            evidence.append(f'season:{season}@date')

    # 4. Expansion from metadata, then title.
    expansion = None
    if meta:
        expansion = _match_phrase(meta, EXPANSION_PHRASES)
        if expansion:
            if confidence == 'unknown':
                confidence = 'explicit'
            evidence.append(f'expansion:{expansion}@meta')
    if not expansion:
        expansion = _match_phrase(title_text, EXPANSION_PHRASES)
        if expansion:
            evidence.append(f'expansion:{expansion}@title')
    if not expansion:
        expansion = _match_phrase(text, STORY_ARC_EXPANSIONS)
        if expansion:
            evidence.append(f'expansion:{expansion}@arc')

    # 5. Fill from the activity catalogue.
    if activity:
        arow = next(r for r in ACTIVITIES if r[0] == activity)
        if expansion not in D1_EXPANSIONS:
            season = season or arow[4]
        expansion = expansion or arow[3]
        if confidence == 'unknown':
            confidence = 'derived'
        evidence.append('activity_catalog')

    # 5b. A known season implies its parent expansion (e.g. Season of the
    # Haunted -> The Witch Queen). This fills expansion for season-only
    # releases without guessing from the date.
    if season and not expansion:
        expansion = SEASON_EXPANSION.get(season)
        if expansion:
            if confidence == 'unknown':
                confidence = 'derived'
            evidence.append('season_catalog')

    # 6. Type fallbacks for content with no catalogue entry.
    atype = None
    if activity:
        atype = next(r[2] for r in ACTIVITIES if r[0] == activity)
    else:
        atype = _fallback_type(title_text)
        if atype:
            evidence.append(f'type:{atype}')

    if confidence == 'unknown' and (activity or event or season or expansion or atype):
        confidence = 'derived'

    # 7. Season from release year for events (occurrence table), if still empty.
    if not season and event:
        season = _event_season_for(event, release)
        if season:
            evidence.append('event_occurrence')

    act = act_from_title(title) if season and season.startswith('episode-') else None
    if act:
        evidence.append(f'act:{act}')

    return _result(activity, atype, season, event, expansion,
                   confidence if evidence else 'unknown', ','.join(evidence), kind, act)


def _result(activity=None, activity_type=None, season=None, event=None,
            expansion=None, confidence='unknown', evidence='', kind='transcript', act=None):
    return {
        'activity_slug': activity,
        'activity_type': activity_type,
        'season_slug': season,
        'act': act,
        'event_slug': event,
        'expansion_slug': expansion,
        'confidence': confidence,
        'evidence': evidence,
        'kind': kind,
    }


def _fallback_type(text):
    if re.search(r'\b(raid)\b', text):
        return 'raid'
    if re.search(r'\b(dungeon)\b', text):
        return 'dungeon'
    if re.search(r'\b(cutscene|cinematic)\b', text):
        return 'cutscene'
    if 'ghost scan' in text or re.search(r'\bpatrol', text):
        return 'patrol'
    if re.search(r'\badventure\b', text):
        return 'story'
    if re.search(r'\b(speak (to|with)|talk to|meet (with|the)|visit|report to|debrief|'
                 r'reconvene|broadcast|commune with|return the|infiltrate|investigate|'
                 r'rescue|escort|search for|find the)\b', text):
        return 'story'
    if re.search(r'\bquest\b', text):
        return 'quest'
    if re.search(r'\bstrike\b', text):
        return 'strike'
    if re.search(r'\bgambit\b', text):
        return 'gambit'
    if re.search(r'\b(crucible|iron banner|trials)\b', text):
        return 'crucible'
    if re.search(r'\blost sector\b', text):
        return 'lost_sector'
    if re.search(r'\bpublic event\b', text):
        return 'public_event'
    if re.search(r'\bcampaign\b', text):
        return 'story'
    return None


def _event_season_for(event_slug, release):
    m = re.search(r'(20\d{2})', release or '')
    if not m:
        return None
    year = int(m.group(1))
    for ev, y, season, *_ in EVENT_OCCURRENCES:
        if ev == event_slug and y == year:
            return season
    return None


# --------------------------------------------------------------------------
# Schema + population
# --------------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS expansions (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    game TEXT,
    year INTEGER,
    release_date TEXT,
    vaulted INTEGER DEFAULT 0,
    sort_order INTEGER
);
CREATE INDEX IF NOT EXISTS idx_expansions_slug ON expansions(slug);

CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    season_number INTEGER UNIQUE,
    name TEXT NOT NULL,
    season_type TEXT NOT NULL DEFAULT 'season',
    act INTEGER,
    destiny_year INTEGER,
    expansion_slug TEXT,
    start_date TEXT,
    end_date TEXT,
    vaulted INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_seasons_number ON seasons(season_number);
CREATE INDEX IF NOT EXISTS idx_seasons_expansion ON seasons(expansion_slug);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    event_type TEXT,
    first_year INTEGER,
    last_year INTEGER,
    recurring INTEGER DEFAULT 1,
    vaulted INTEGER DEFAULT 0,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_slug ON events(slug);

CREATE TABLE IF NOT EXISTS event_occurrences (
    id INTEGER PRIMARY KEY,
    event_slug TEXT NOT NULL,
    year INTEGER NOT NULL,
    season_slug TEXT,
    start_date TEXT,
    end_date TEXT,
    vaulted INTEGER DEFAULT 0,
    UNIQUE(event_slug, year)
);
CREATE INDEX IF NOT EXISTS idx_event_occ_season ON event_occurrences(season_slug);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    expansion_slug TEXT,
    season_slug TEXT,
    event_slug TEXT,
    vaulted INTEGER DEFAULT 0,
    source TEXT DEFAULT 'catalog'
);
CREATE INDEX IF NOT EXISTS idx_activities_type ON activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_activities_season ON activities(season_slug);
CREATE INDEX IF NOT EXISTS idx_activities_expansion ON activities(expansion_slug);

CREATE TABLE IF NOT EXISTS coverage_notes (
    entity_type TEXT NOT NULL,
    slug TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence TEXT,
    source_url TEXT,
    PRIMARY KEY (entity_type, slug)
);
CREATE INDEX IF NOT EXISTS idx_coverage_status ON coverage_notes(status);

CREATE TABLE IF NOT EXISTS transcript_classification (
    transcript_id INTEGER PRIMARY KEY REFERENCES transcripts(id) ON DELETE CASCADE,
    activity_slug TEXT,
    activity_type TEXT,
    season_slug TEXT,
    act INTEGER,
    event_slug TEXT,
    expansion_slug TEXT,
    confidence TEXT NOT NULL DEFAULT 'unknown',
    evidence TEXT
);
CREATE INDEX IF NOT EXISTS idx_tc_activity ON transcript_classification(activity_slug);
CREATE INDEX IF NOT EXISTS idx_tc_season ON transcript_classification(season_slug);
CREATE INDEX IF NOT EXISTS idx_tc_event ON transcript_classification(event_slug);
CREATE INDEX IF NOT EXISTS idx_tc_conf ON transcript_classification(confidence);

CREATE TABLE IF NOT EXISTS item_classification (
    item_id INTEGER PRIMARY KEY REFERENCES items(id) ON DELETE CASCADE,
    season_slug TEXT,
    event_slug TEXT,
    expansion_slug TEXT,
    confidence TEXT NOT NULL DEFAULT 'unknown',
    evidence TEXT
);
CREATE INDEX IF NOT EXISTS idx_ic_season ON item_classification(season_slug);
CREATE INDEX IF NOT EXISTS idx_ic_event ON item_classification(event_slug);

CREATE TABLE IF NOT EXISTS document_classification (
    source TEXT NOT NULL,
    source_id INTEGER NOT NULL,
    season_slug TEXT,
    event_slug TEXT,
    expansion_slug TEXT,
    confidence TEXT NOT NULL DEFAULT 'unknown',
    evidence TEXT,
    PRIMARY KEY (source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_dc_season ON document_classification(season_slug);
CREATE INDEX IF NOT EXISTS idx_dc_event ON document_classification(event_slug);

CREATE VIEW IF NOT EXISTS v_transcript_taxonomy AS
SELECT t.id AS transcript_id, t.slug, t.title, t.release, t.arc,
       c.activity_slug, a.name AS activity_name, c.activity_type,
       c.season_slug, c.act, s.season_number, s.name AS season_name, s.season_type,
       c.event_slug, e.name AS event_name,
       c.expansion_slug, x.name AS expansion_name,
       c.confidence, c.evidence
FROM transcripts t
LEFT JOIN transcript_classification c ON c.transcript_id = t.id
LEFT JOIN activities a ON a.slug = c.activity_slug
LEFT JOIN seasons s ON s.slug = c.season_slug
LEFT JOIN events e ON e.slug = c.event_slug
LEFT JOIN expansions x ON x.slug = c.expansion_slug;

CREATE VIEW IF NOT EXISTS v_activity_coverage AS
SELECT a.slug, a.name, a.activity_type, a.season_slug, a.expansion_slug,
       a.event_slug, a.vaulted,
       COUNT(DISTINCT t.id) AS transcripts,
       COUNT(tl.id) AS lines
FROM activities a
LEFT JOIN transcript_classification c ON c.activity_slug = a.slug
LEFT JOIN transcripts t ON t.id = c.transcript_id
LEFT JOIN transcript_lines tl ON tl.transcript_id = t.id AND tl.is_stage_dir = 0
GROUP BY a.id;

CREATE VIEW IF NOT EXISTS v_season_coverage AS
SELECT s.season_number, s.slug, s.name, s.season_type, s.vaulted,
       COUNT(DISTINCT t.id) AS transcripts,
       COUNT(tl.id) AS lines
FROM seasons s
LEFT JOIN transcript_classification c ON c.season_slug = s.slug
LEFT JOIN transcripts t ON t.id = c.transcript_id
LEFT JOIN transcript_lines tl ON tl.transcript_id = t.id AND tl.is_stage_dir = 0
GROUP BY s.id;

CREATE VIEW IF NOT EXISTS v_event_coverage AS
SELECT e.slug, e.name, e.event_type, e.vaulted,
       COUNT(DISTINCT t.id) AS transcripts,
       COUNT(tl.id) AS lines,
       COUNT(DISTINCT o.year) AS occurrences
FROM events e
LEFT JOIN transcript_classification c ON c.event_slug = e.slug
LEFT JOIN transcripts t ON t.id = c.transcript_id
LEFT JOIN transcript_lines tl ON tl.transcript_id = t.id AND tl.is_stage_dir = 0
LEFT JOIN event_occurrences o ON o.event_slug = e.slug
GROUP BY e.id;
"""


def ensure_schema(conn):
    conn.executescript(SCHEMA)


def populate(conn):
    """Seed catalogues and classify every row. Idempotent."""
    ensure_schema(conn)
    for i, row in enumerate(EXPANSIONS):
        slug, name, game, year, rel, vaulted = row
        conn.execute(
            'INSERT OR REPLACE INTO expansions (slug,name,game,year,release_date,vaulted,sort_order) '
            'VALUES (?,?,?,?,?,?,?)', (slug, name, game, year, rel, vaulted, i))
    for row in SEASONS:
        num, slug, name, stype, act, dyear, exp, start, end, vaulted = row
        conn.execute(
            'INSERT OR REPLACE INTO seasons '
            '(slug,season_number,name,season_type,act,destiny_year,expansion_slug,start_date,end_date,vaulted) '
            'VALUES (?,?,?,?,?,?,?,?,?,?)',
            (slug, num, name, stype, act, dyear, exp, start, end, vaulted))
    for row in EVENTS:
        slug, name, etype, first, last, recurring, vaulted, notes = row
        conn.execute(
            'INSERT OR REPLACE INTO events '
            '(slug,name,event_type,first_year,last_year,recurring,vaulted,notes) '
            'VALUES (?,?,?,?,?,?,?,?)',
            (slug, name, etype, first, last, recurring, vaulted, notes))
    for row in EVENT_OCCURRENCES:
        slug, year, season, start, end, vaulted = row
        conn.execute(
            'INSERT OR REPLACE INTO event_occurrences '
            '(event_slug,year,season_slug,start_date,end_date,vaulted) VALUES (?,?,?,?,?,?)',
            (slug, year, season, start, end, vaulted))
    # Recurring events without explicit yearly rows get one occurrence per year.
    for slug, name, etype, first, last, recurring, vaulted, notes in EVENTS:
        if not recurring:
            continue
        if conn.execute('SELECT 1 FROM event_occurrences WHERE event_slug=? LIMIT 1',
                        (slug,)).fetchone():
            continue
        for year in range(first, last + 1):
            conn.execute('INSERT OR IGNORE INTO event_occurrences '
                         '(event_slug,year,vaulted) VALUES (?,?,?)', (slug, year, vaulted))

    for row in ACTIVITIES:
        slug, name, atype, exp, season, event, vaulted, keywords = row
        conn.execute(
            'INSERT OR REPLACE INTO activities '
            '(slug,name,activity_type,expansion_slug,season_slug,event_slug,vaulted,source) '
            'VALUES (?,?,?,?,?,?,?,?)',
            (slug, name, atype, exp, season, event, vaulted, 'catalog'))

    conn.execute('DELETE FROM coverage_notes')
    for entity_type, slug, status, evidence, source_url in COVERAGE_NOTES:
        conn.execute(
            'INSERT INTO coverage_notes (entity_type,slug,status,evidence,source_url) '
            'VALUES (?,?,?,?,?)', (entity_type, slug, status, evidence, source_url))

    # Transcripts
    rows = conn.execute('SELECT id, slug, title, release, arc, characters FROM transcripts').fetchall()
    tcounts = {}
    for tid, slug, title, release, arc, characters in rows:
        r = classify(slug=slug, title=title, release=release, arc=arc,
                     characters=characters, kind='transcript')
        conn.execute(
            'INSERT OR REPLACE INTO transcript_classification '
            '(transcript_id,activity_slug,activity_type,season_slug,act,event_slug,expansion_slug,confidence,evidence) '
            'VALUES (?,?,?,?,?,?,?,?,?)',
            (tid, r['activity_slug'], r['activity_type'], r['season_slug'], r['act'],
             r['event_slug'], r['expansion_slug'], r['confidence'], r['evidence']))
        tcounts[r['confidence']] = tcounts.get(r['confidence'], 0) + 1

    # Items: release text is authoritative-ish; titles add event keywords.
    items = conn.execute('SELECT id, slug, title, release FROM items').fetchall()
    icounts = {}
    for iid, slug, title, release in items:
        r = classify(slug=slug, title=title, release=release, kind='item')
        conn.execute(
            'INSERT OR REPLACE INTO item_classification '
            '(item_id,season_slug,event_slug,expansion_slug,confidence,evidence) VALUES (?,?,?,?,?,?)',
            (iid, r['season_slug'], r['event_slug'], r['expansion_slug'],
             r['confidence'], r['evidence']))
        icounts[r['confidence']] = icounts.get(r['confidence'], 0) + 1

    # Books and records: title/release only.
    dcounts = {}
    for source, table, title_col, release_col in (
            ('book', 'books', 'title', "''"),
            ('record', 'records', 'title', 'release')):
        sql = f'SELECT id, slug, {title_col}, {release_col} FROM {table}'
        for did, slug, title, release in conn.execute(sql).fetchall():
            r = classify(slug=slug, title=title, release=release, kind=source)
            conn.execute(
                'INSERT OR REPLACE INTO document_classification '
                '(source,source_id,season_slug,event_slug,expansion_slug,confidence,evidence) '
                'VALUES (?,?,?,?,?,?,?)',
                (source, did, r['season_slug'], r['event_slug'],
                 r['expansion_slug'], r['confidence'], r['evidence']))
            dcounts[r['confidence']] = dcounts.get(r['confidence'], 0) + 1

    return {'transcripts': tcounts, 'items': icounts, 'documents': dcounts}


def coverage(conn):
    """Compact coverage summary for reports and discovery tools."""
    out = {'activities': [], 'seasons': [], 'events': [], 'notes': [], 'gaps': {}}
    notes = {}
    for row in conn.execute(
            'SELECT entity_type,slug,status,evidence,source_url FROM coverage_notes'):
        note = dict(zip(('entity_type', 'slug', 'status', 'evidence', 'source_url'), row))
        notes[(note['entity_type'], note['slug'])] = note
        out['notes'].append(note)

    def status(entity_type, slug, transcripts):
        note = notes.get((entity_type, slug))
        if note:
            return note['status']
        return 'covered' if transcripts else 'missing'

    for r in conn.execute(
            'SELECT slug,name,activity_type,season_slug,vaulted,transcripts,lines '
            'FROM v_activity_coverage ORDER BY lines DESC, name'):
        item = dict(zip(
            ('slug', 'name', 'activity_type', 'season_slug', 'vaulted', 'transcripts', 'lines'), r))
        item['coverage_status'] = status('activity', item['slug'], item['transcripts'])
        out['activities'].append(item)
    for r in conn.execute(
            'SELECT season_number,slug,name,season_type,vaulted,transcripts,lines '
            'FROM v_season_coverage ORDER BY season_number'):
        item = dict(zip(
            ('season_number', 'slug', 'name', 'season_type', 'vaulted', 'transcripts', 'lines'), r))
        item['coverage_status'] = status('season', item['slug'], item['transcripts'])
        out['seasons'].append(item)
    for r in conn.execute(
            'SELECT slug,name,event_type,vaulted,transcripts,lines,occurrences '
            'FROM v_event_coverage ORDER BY name'):
        item = dict(zip(
            ('slug', 'name', 'event_type', 'vaulted', 'transcripts', 'lines', 'occurrences'), r))
        item['coverage_status'] = status('event', item['slug'], item['transcripts'])
        out['events'].append(item)
    out['gaps']['activities_without_transcripts'] = [
        a['slug'] for a in out['activities'] if a['transcripts'] == 0]
    out['gaps']['events_without_transcripts'] = [
        e['slug'] for e in out['events'] if e['transcripts'] == 0]
    out['gaps']['seasons_without_transcripts'] = [
        s['slug'] for s in out['seasons'] if s['transcripts'] == 0]
    out['gaps']['unexplained'] = [
        f"{kind}:{item['slug']}"
        for kind, key in (('activity', 'activities'), ('event', 'events'), ('season', 'seasons'))
        for item in out[key]
        if item['coverage_status'] in ('missing',)]
    return out


if __name__ == '__main__':
    import json
    import os
    import sys
    db = os.environ.get('GRIMOIRE_DB') or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db', 'grimoire.db')
    conn = sqlite3.connect(db)
    print(json.dumps(populate(conn), indent=2))
    conn.commit()
    conn.close()
