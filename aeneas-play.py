#!/usr/bin/env python
# coding=utf-8

import json
import os

from aeneas.executetask import ExecuteTask
from aeneas.task import Task
from aeneas.downloader import Downloader

from app import db, get_doc

D = Downloader()

# missing 1937-Roosevelt2, 1989-Bush, and 1997-Clinton2
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
    '1993-Clinton1': '7LdagSzK2VI',
    '2001-Bush1': 'rXzgMdj5urs',
    '2005-Bush2': 'ceSJLivxk2k',
    '2009-Obama1': 'n_94YT46yFg',

    # fix first two alignments
    '2013-Obama2': 'g5bIT5JJX5U',
    }

alignment_fixes = {
    '1933-Roosevelt1': {
        # index: (start, end)
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
    '1941-Roosevelt3': {},
    '1945-Roosevelt4': {
        1: (0, 0),
        2: (0, 11.520),
        },
    '1949-Truman': {
        1: (0, 0),
        2: (0, 8.840),
        },
    '1953-Eisenhower1': {},
    '1957-Eisenhower2': {},
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
    '1993-Clinton1': {},
    '2001-Bush1': {
        1: (13, 15),
        2: (15, 38.320),
        },
    '2005-Bush2': {},
    '2009-Obama1': {},
    '2013-Obama2': {
        1: (3, 10),
        2: (20, 23.440),
        119: (1107.800, 1120),
        120: (1120, 1120.5),
        121: (1120.5, 1130),
        },
    }


def get_alignments():
    config = u'task_language=eng|is_text_type=plain|os_task_file_format=json'

    for address, youtube_id in text_audio_pairs.iteritems():

        # download youtube video
        print D.audio_from_youtube(
            'https://youtu.be/' + youtube_id,
            output_file_path=u'alignment/audio/' + address + '.webm',
            preferred_format=u'webm'
            )

        # designate text, audio, and syncmap files
        text = os.path.abspath(u'alignment/text/' + address + '.txt')
        audio = os.path.abspath(u'alignment/audio/' + address + '.webm')
        syncmap = os.path.abspath(u'alignment/syncmaps/' + address + '.json')

        # align text to audio
        task = Task(config_string=config)
        task.text_file_path_absolute = text
        task.audio_file_path_absolute = audio
        task.sync_map_file_path_absolute = syncmap
        ExecuteTask(task).execute()
        task.output_sync_map_file()


def update_database_with_alignments():
    for address, youtube_id in text_audio_pairs.iteritems():
        doc = get_doc(title=address)
        doc.youtube_id = youtube_id

        syncmap = os.path.abspath(u'alignment/syncmaps/' + address + '.json')
        syncmap = json.load(open(syncmap))['fragments']

        for sent, sync in zip(doc.sentences, syncmap):
            sent.youtube_id = youtube_id
            sent.aeneas_start = float(sync['begin'])
            sent.aeneas_end = float(sync['end'])

            try:
                sent.manual_start = alignment_fixes[address][sent.index][0]

            except KeyError:
                pass

            try:
                sent.manual_end = alignment_fixes[address][sent.index][1]

            except KeyError:
                pass

            db.session.add(sent)

        db.session.add(doc)
        db.session.commit()

if __name__ == '__main__':
    # get_alignments()
    update_database_with_alignments()
