#-*- encoding: utf-8 -*-

from collections import OrderedDict
import os

###
import sys
sys.path.append('../')
###
import utils


MIN_TEXT_LINES = 12
MIN_CHUNK_LINES = 6
MAX_CHUNK_WORDS = 200

def make_chunks(num_links, trim_ending=True, moderator=None,
                min_chunk_lines=MIN_CHUNK_LINES):
    text_fns = utils.get_file_list(utils.TEXTS_DIR, num_links)
    max_chunks = min(utils.CHUNKS_FOR_SOURCE, len(text_fns))
    texts_processed = 0
    for text_idx, text_fn in enumerate(text_fns[:utils.CHUNKS_FOR_SOURCE],
                                       start=1):
        chunk_fn = text_fn.replace(utils.TEXTS_DIR, utils.CHUNKS_DIR)
        assert chunk_fn != text_fn, 'ERROR: invalid path to text file'
        if not os.path.isfile(chunk_fn):
            with open(text_fn, 'rt', encoding='utf-8') as f_in:
                text = \
                    [x.split('\t') for x in f_in.read().split('\n') if x][1:]
            with open(chunk_fn, 'wt', encoding='utf-8') as f_out:
                moder_ = None
                for start_idx, (speaker, _) in enumerate(text):
                    if speaker and (not moderator or speaker == moderator):
                        moder_ = speaker
                        break
                if moderator:
                    moder = moderator
                else:
                    assert moder_, 'ERROR: invalid file content'
                    speaker_lines, speaker_words = {}, {}
                    curr_speaker = None
                    for speaker, line in text:
                        if speaker:
                            curr_speaker = speaker
                            speaker_lines[speaker] = \
                                speaker_lines.get(speaker, 0) + 1
                        if curr_speaker:
                            speaker_words[curr_speaker] = \
                                speaker_words.get(curr_speaker, 0)\
                              + len(line.split())
                    max_lines = max(speaker_lines.values())
                    moder = \
                        min({x: y / speaker_lines[x]
                                 for x, y in speaker_words.items()
                                 if speaker_lines[x] > max_lines / 2}.items(),
                            key=lambda x: x[1])[0]

                if trim_ending:
                    end_idx, next_id = 0, 0
                    for idx, (speaker, _) in reversed(list(enumerate(text))):
                        if speaker:
                            if not end_idx:
                                end_idx = idx + 1
                            if speaker == moder:
                                end_idx = idx
                                break
                            if next_id > 2:
                                break
                            next_id += 1
                else:
                    end_idx = len(text)

                text = text[start_idx:end_idx]
                eff_start_idx = len(text) * 2 // 3
                for i, (speaker, _) in \
                        enumerate(reversed(text[:eff_start_idx + 1])):
                    if speaker == moder:
                        eff_start_idx -= i
                        break
                else:
                    for i, (speaker, _) in enumerate(text[eff_start_idx:]):
                        if speaker == moder:
                            eff_start_idx += i
                            break
                    else:
                        eff_start_idx = start_idx

                lines, buffer = [], []
                speaker_no, chunk_words = 0, 0
                for speaker, line in text[eff_start_idx:]:
                    if speaker:
                        speaker_no += 1
                        if buffer:
                            lines.extend(buffer)
                            buffer = []
                    chunk_words += len(line.split())
                    line = '\t'.join([speaker, line])
                    if speaker_no <= min_chunk_lines:
                        lines.append(line)
                    elif chunk_words > MAX_CHUNK_WORDS:
                        break
                    else:
                        buffer.append(line)
                else:
                    lines.extend(buffer)
                    buffer = []
                    for speaker, line in reversed(text[:eff_start_idx]):
                        chunk_words += len(line.split())
                        line = '\t'.join([speaker, line])
                        if speaker_no < min_chunk_lines:
                            lines.insert(0, line)
                        elif chunk_words > MAX_CHUNK_WORDS:
                            break
                        else:
                            buffer.insert(0, line)
                        if speaker:
                            speaker_no += 1
                            if buffer:
                                lines = buffer + lines
                                buffer = []
                    else:
                        lines = buffer + lines
                f_out.write('\n'.join(lines))
                print('\r{} (of {})'.format(text_idx, max_chunks),
                      end='')
                texts_processed += 1
    if texts_processed:
        print()
