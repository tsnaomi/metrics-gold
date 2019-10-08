#!/usr/bin/env python
# coding=utf-8

import json
import os

from aeneas.executetask import ExecuteTask
from aeneas.task import Task
from aeneas.downloader import Downloader

from app import db, get_doc

D = Downloader()

# automatic alignment ---------------------------------------------------------

# This dictionary matches inaugural addresses to YouTube recordings.
# (TODO: It is currently missing a recording for 1937-Roosevelt2.)
text_audio_pairs = {
    # text added initially: "President Hoover , Mr. Chief Justice , my friends
    # , this is a day of national consecration , and "
    '1933-Roosevelt1': 'KL3DXmQ4_jk',

    # text added initially: "My friends"
    '1941-Roosevelt3': 'DGt7oaS0IDA',

    # 1st sentence is missing in audio (fix)
    '1945-Roosevelt4': 'VVj1WVpNuwk',

    # 1st sentence is missing in audio (fix)
    '1949-Truman': 'vViEgE9whPQ',
    '1953-Eisenhower1': 'ZeJ76ZRQbyA',
    '1957-Eisenhower2': 'FZ-GwNQSnew',
    '1961-Kennedy': 'hyGXrxeMjaI',

    # 1st sentence is missing in audio (fix)
    '1965-Johnson': 'Dbp_Pok1k50',
    '1969-Nixon1': 'QqAEPbXXscI',

    # 1st sentence is missing in audio (fix)
    '1973-Nixon2': 'b5WPaeeDdK0',
    '1977-Carter': 'tMJ8yDSbhhU',
    '1981-Reagan1': 'hpPt7xGx4Xo',
    '1985-Reagan2': 'OBthkDPFBvg',
    '2001-Bush1': 'rXzgMdj5urs',
    '2005-Bush2': 'ceSJLivxk2k',
    '2009-Obama1': 'n_94YT46yFg',

    # fix first two alignments
    '2013-Obama2': 'g5bIT5JJX5U',

    # OK :)
    '1989-Bush': 'zMmrNcdmdVY',
    '1993-Clinton1': 'Qszv668rN20',
    '1997-Clinton2': 'Tu33kA83Rfo',
    }


def align(address_id, youtube_id=None):
    '''Use aeneas to align the given address and YouTube video.'''
    if not youtube_id:
        youtube_id = text_audio_pairs[address_id]

    # download YouTube video
    print('Downloading YouTube video...')
    print(D.audio_from_youtube(
        'http://www.youtube.com/watch?v=' + youtube_id,
        output_file_path=u'alignment/audio/' + address_id + '.webm',
        # preferred_format=u'webm'
        ))

    # designate text, audio, and syncmap files
    print('Designating filepaths...')
    text = os.path.abspath(u'alignment/text/' + address_id + '.txt')
    audio = os.path.abspath(u'alignment/audio/' + address_id + '.webm')
    syncmap = os.path.abspath(u'alignment/syncmaps/' + address_id + '.json')

    # align text to audio
    print('Align speech to text...')
    config = u'task_language=eng|is_text_type=plain|os_task_file_format=json'
    task = Task(config_string=config)
    task.text_file_path_absolute = text
    task.audio_file_path_absolute = audio
    task.sync_map_file_path_absolute = syncmap
    ExecuteTask(task).execute()
    task.output_sync_map_file()


def update(address_id, youtube_id=None):
    '''Update the database with the aeneas timestamps for the given address.'''
    if not youtube_id:
        youtube_id = text_audio_pairs[address_id]

    doc = get_doc(title=address_id)
    doc.youtube_id = youtube_id

    syncmap = os.path.abspath(u'alignment/syncmaps/' + address_id + '.json')
    syncmap = json.load(open(syncmap))['fragments']

    for sent, sync in zip(doc.sentences, syncmap):
        sent.youtube_id = youtube_id
        sent.aeneas_start = float(sync['begin'])
        sent.aeneas_end = float(sync['end'])

        # to reset any previous forced alignments
        sent.manual_start = None
        sent.manual_end = None

        db.session.add(sent)

    db.session.add(doc)
    db.session.commit()


# revisions -------------------------------------------------------------------

# This dictionary provides forced/manual alignments for specified sentences in
# misaligned inaugural addresses.
# (TODO: The alignments for 1997-Clinton2 have not been cleaned yet.)
alignment_fixes = {
    '1933-Roosevelt1': {
        # sentence index: (start time, end time)
        97: (1047.720, 1056),
        98: (1056, 1063),
        99: (1063, 1072),
        100: (1072, 1078),
        101: (1078, 1087),
        102: (1087, 1093),
        103: (1093, 1099),
        104: (1099, 1104),
        105: (1104, 1116),
        106: (1116, 1123),
        107: (1123, 1147.720)
        },
    '1945-Roosevelt4': {
        1: (0, 0),
        2: (0, 11.520),
        },
    '1949-Truman': {
        1: (0, 0),
        2: (0, 8.840),
        },
    '1961-Kennedy': {
        5: (47.840, 62),
        6: (62, 66),
        7: (66, 78.480),
        12: (120.000, 132),
        13: (132, 153.200),
        14: (153.200, 190),
        15: (190, 191.5),
        16: (191.5, 193),
        17: (193, 205.240),
        22: (241.480, 246),
        23: (246, 270),
        24: (270, 290),
        25: (289, 298),
        26: (298, 211),
        27: (211, 320.720),
        },
    '1965-Johnson': {
        1: (0, 0),
        2: (0, 19.000),
        84: (933.520, 940),
        85: (948, 962),
        86: (962, 975),
        87: (975, 1000),
        88: (1000, 1015),
        89: (1015, 1027),
        90: (1037, 1043),
        91: (1043, 1069),
        92: (1069, 1080),
        93: (1080, 1087),
        94: (1087, 1096),
        95: (1096, 1106),
        96: (1106, 1125),
        97: (1125, 1128),
        98: (1128, 1131),
        99: (1128, 1143),
        100: (1143, 1150),
        101: (1150, 1161),
        102: (1161, 1166),
        103: (1166, 1170),
        104: (1170, 1174),
        105: (1174, 1185),
        106: (1188, 1223),
        107: (1223, 1231),
        108: (1245, 1257),
        109: (1257, 1262),
        111: (1270, 1287),
        112: (1287, 1294.560),
        },
    '1969-Nixon1': {
        127: (872.520, 880),
        128: (888, 892),
        129: (892, 896),
        130: (896, 906),
        131: (906, 909.080),
        },
    '1973-Nixon2': {
        1: (0, 0),
        2: (11, 32.480),
        69: (732.640, 748),
        70: (754, 766),
        71: (766, 769),
        72: (769, 778.560),
        },
    '1977-Carter': {
        1: (0, 15),
        2: (47, 59.040),
        },
    '1981-Reagan1': {
        140: (1205.360, 1210),
        141: (1210, 1213),
        142: (1213, 1248.160),
        },
    '1985-Reagan2': {
        90: (797.320, 806),
        91: (806, 819),
        92: (828, 836),
        93: (835, 838.800),
        },
    '1993-Clinton1': {
        # ... ends late
        9: (109, 120),
        36: (310.5, 312.5),
        38: (329, 336.5),
        40: (356, 360),
        50: (415, 419),
        54: (446, 454.5),
        59: (504, 506.5),
        62: (514, 522),
        65: (544, 549),
        69: (573.5, 575),
        72: (587, 593),
        93: (719.5, 722),
        109: (831, 838.5),
        110: (838.5, 841.5),
    },
    '2001-Bush1': {
        1: (13, 15),
        2: (15, 38.320),
        },
    '2013-Obama2': {
        1: (3, 10),
        2: (20, 23.440),
        119: (1107.800, 1120),
        120: (1120, 1120.5),
        121: (1120.5, 1130),
        },
    }


def fix(address_id):
    '''Fix the alignments for the given address based on alignment_fixes.'''
    doc = get_doc(title=address_id)

    try:
        for sent_idx, (start, end) in alignment_fixes[address_id]:
            sent = doc.sentences.filter_by(doc=doc.id, index=sent_idx).one()
            sent.manual_start = start
            sent.manual_end = end
            db.session.add(sent)

        db.session.commit()

    except KeyError:
        pass


def fix_clinton_1993():  # womp womp
    '''Fix alignment with YouTube video Qszv668rN20.'''
    starts_early = set([
        8, 19, 50, 56, 71, 73, 74, 81, 92, 96, 99, 104, 106, 107, 108,
        ])

    ends_early = set([8, 36])

    # midly so: 4, 12, 14, 15, 35, 61, 68, 92
    ends_late = set([
        1, 2, 3, 5, 6, 10, 11, 13, 17, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28,
        29, 30, 31, 32, 33, 34, 37, 41, 42, 43, 44, 45, 46, 47, 48, 51, 56, 60,
        63, 64, 66, 67, 75, 76, 77, 78, 79, 81, 82, 83, 84, 85, 86, 87, 88,
        89, 90, 94, 97, 99, 100, 101, 102, 104, 108,
        ])

    doc = get_doc(title='1993-Clinton1')

    for sent in doc.sentences:
        try:
            start, end = alignment_fixes['1993-Clinton1'][sent.index]
            sent.manual_start = start
            sent.manual_end = end

        except KeyError:
            # reset the values
            sent.manual_start = None
            sent.manual_end = None

            if sent.index in starts_early:
                sent.manual_start = sent.aeneas_start + 1

            if sent.index in ends_early:
                sent.manual_end = sent.aeneas_end + 1

            elif sent.index in ends_late:
                sent.manual_end = sent.aeneas_end - 1

        db.session.add(sent)

    db.session.commit()


# bulk operations -------------------------------------------------------------

def align_and_update_all():
    '''Align and update all of the addresses according to text_audio_pairs.

    For each address in text_audio_pairs, this function will:
        - Align the text to the audio in the given YouTube video
        - Update the address in the database with the aeneas timestamps
    '''
    for address_id, youtube_id in text_audio_pairs.iteritems():
        align(address_id, youtube_id)
        update(address_id, youtube_id)


def fix_all():
    '''Manually fix all of the alignments according to alignment_fixes.'''
    for address_id in alignment_fixes.keys():
        fix(address_id)

# -----------------------------------------------------------------------------


if __name__ == '__main__':
    # # in one fell swoop...
    # align_and_update_all()
    # fix_all()

    # Bush 1989
    align('1989-Bush')
    update('1989-Bush')

    # Clinton 1993
    align('1993-Clinton1')
    update('1993-Clinton1')
    fix_clinton_1993()

    # Clinton 1997
    align('1997-Clinton2')
    update('1997-Clinton2')
