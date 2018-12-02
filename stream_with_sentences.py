import deepspeech as ds
import numpy as np
import jamspell
import googletrans
import sys
import wave
import webrtcvad
import collections
import time
import curses
import textwrap
import sys
import getopt
import locale

TRANSLATION_LANGUAGE = ''
WAVE_FILE = ''
MODEL_DIR = ''

def usage():
    print "Usage:" + sys.argv[0] + " --lang <en|de|es|fr|pl> --file </path/to/.wav> --models </path/to/models>"

try:
    opts, args = getopt.getopt(sys.argv[1:], 'l:f:m:h', ['lang=', 'file=', 'models=', 'help'])
except getopt.GetoptError:
    usage()
    sys.exit(2)

for opt, arg in opts:
    if opt in ('-h', '--help'):
        usage()
        sys.exit(2)
    elif opt in ('-l', '--lang'):
        TRANSLATION_LANGUAGE = arg
    elif opt in ('-f', '--file'):
        WAVE_FILE = arg
    elif opt in ('-m', '--models'):
        MODEL_DIR = arg
    else:
        usage()
        sys.exit(2)

# Set locale for translated language or use default locale
LOCALE = TRANSLATION_LANGUAGE + "_" + TRANSLATION_LANGUAGE.upper() + ".utf8"
print "Locale set to " + LOCALE

try: 
    locale.setlocale(locale.LC_ALL, LOCALE)
except locale.Error:
    print "WARNING: Locale " + LOCALE + " not found. Ensure you have language pack installed! Falling back to default LOCALE" 
    locale.setlocale(locale.LC_ALL, '')

MODEL = MODEL_DIR + "/output_graph.pbmm"
ALPHABET = MODEL_DIR + "/alphabet.txt"
LM = MODEL_DIR + "/lm.binary"
TRIE = MODEL_DIR + "/trie"

LM_WEIGHT = 1.50
VALID_WORD_COUNT_WEIGHT = 2.25
N_FEATURES = 26
N_CONTEXT = 9
BEAM_WIDTH = 512


# Methods copied from:
# https://github.com/wiseman/py-webrtcvad/blob/master/example.py
class Frame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes, timestamp, duration):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration


def frame_generator(frame_duration_ms, audio, sample_rate):
    """Generates audio frames from PCM audio data.
    Takes the desired frame duration in milliseconds, the PCM data, and
    the sample rate.
    Yields Frames of the requested duration.
    """
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    timestamp = 0.0
    duration = (float(n) / sample_rate) / 2.0
    while offset + n < len(audio):
        yield Frame(audio[offset:offset + n], timestamp, duration)
        timestamp += duration
        offset += n


def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
    """Filters out non-voiced audio frames.
    Given a webrtcvad.Vad and a source of audio frames, yields only
    the voiced audio.
    Uses a padded, sliding window algorithm over the audio frames.
    When more than 90% of the frames in the window are voiced (as
    reported by the VAD), the collector triggers and begins yielding
    audio frames. Then the collector waits until 90% of the frames in
    the window are unvoiced to detrigger.
    The window is padded at the front and back to provide a small
    amount of silence or the beginnings/endings of speech around the
    voiced frames.
    Arguments:
    sample_rate - The audio sample rate, in Hz.
    frame_duration_ms - The frame duration in milliseconds.
    padding_duration_ms - The amount to pad the window, in milliseconds.
    vad - An instance of webrtcvad.Vad.
    frames - a source of audio frames (sequence or generator).
    Returns: A generator that yields PCM audio data.
    """
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    # We use a deque for our sliding window/ring buffer.
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
    # NOTTRIGGERED state.
    triggered = False

    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame.bytes, sample_rate)

        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            # If we're NOTTRIGGERED and more than 90% of the frames in
            # the ring buffer are voiced frames, then enter the
            # TRIGGERED state.
            if num_voiced > 0.90 * ring_buffer.maxlen:
                triggered = True
                # We want to yield all the audio we see from now until
                # we are NOTTRIGGERED, but we have to start with the
                # audio that's already in the ring buffer.
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            # We're in the TRIGGERED state, so collect the audio data
            # and add it to the ring buffer.
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            # If more than 90% of the frames in the ring buffer are
            # unvoiced, then enter NOTTRIGGERED and yield whatever
            # audio we've collected.
            if num_unvoiced > 0.90 * ring_buffer.maxlen:
                triggered = False
                yield b''.join([f.bytes for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []
    # If we have any leftover voiced audio when we run out of input,
    # yield it.
    if voiced_frames:
        yield b''.join([f.bytes for f in voiced_frames])


translator = googletrans.Translator()

print('Initializing model...')

corrector = jamspell.TSpellCorrector()
corrector.LoadLangModel('en.bin')

model = ds.Model(MODEL, N_FEATURES, N_CONTEXT, ALPHABET, BEAM_WIDTH)
model.enableDecoderWithLM(ALPHABET, LM, TRIE, LM_WEIGHT,
                          VALID_WORD_COUNT_WEIGHT)

fin = wave.open(WAVE_FILE, 'rb')

frame_rate = fin.getframerate()
bit_depth = fin.getsampwidth()
channels = fin.getnchannels()
frames_per_second = frame_rate * bit_depth * channels

# "Aggressiveness" = 3 for detecting voice activity
vad = webrtcvad.Vad(3)

# Accumulate all data bytes as we go
data_array = bytearray()

stdscr = curses.initscr()
curses.start_color()
# This is needed in order to use -1 to mean the default color
curses.use_default_colors()
# Map pair 1 to the color green
curses.init_pair(1, curses.COLOR_GREEN, -1)
curses.noecho()
curses.cbreak()
win_height, win_width = stdscr.getmaxyx()

# cache format, keyed by segment number:
# {1: {'length': x, 'corrected': y, 'translated': z}}
segment_cache = {}

try:
    while True:
        data = fin.readframes(frames_per_second)
        if not data:
            break
        data_array.extend(data)
        # Generate frames from data we have accumulated
        frames = list(frame_generator(10, bytes(data_array), frame_rate))
        # Receive sentence-based segments from accumulated data
        segments = list(vad_collector(frame_rate, 10, 300, vad, frames))

        text = ''
        translated_text = ''
        for i, segment in enumerate(segments):
            # If the segment is longer than it was last iteration, re-calculate
            # the speech-to-text and translation.
            segment_len = len(segment)
            if (i not in segment_cache or
                    segment_cache[i]['length'] < segment_len):
                segment_cache[i] = {'length': segment_len}
                new_text = model.stt(np.frombuffer(segment, np.int16),
                                     frame_rate)
                corrected = corrector.FixFragment(new_text)
                segment_cache[i]['corrected'] = corrected
                translated = translator.translate(corrected, src='en',
                                                  dest=TRANSLATION_LANGUAGE).text
                segment_cache[i]['translated'] = translated.encode('utf-8')
            text = ''.join([text, '' if not text else ' ',
                            segment_cache[i]['corrected']])
            translated_text = ''.join([translated_text,
                                       '' if not translated_text else ' ',
                                       segment_cache[i]['translated']])

        if not text:
            continue

        # Need to do this because the German translation is sometimes shorter
        # than it was during the last iteration.
        stdscr.erase()
        wrapped_text = textwrap.fill(text, win_width - 2)
        wrapped_translated_text = textwrap.fill(translated_text, win_width - 2)
        stdscr.addstr(0, 0, wrapped_text)
        stdscr.addstr(15, 0, wrapped_translated_text, curses.color_pair(1))
        stdscr.refresh()
    # Show the final output and re-translate
    stdscr.erase()
    translated_text = translator.translate(text, src='en', dest=TRANSLATION_LANGUAGE).text
    wrapped_translated_text = textwrap.fill(translated_text.encode('utf8'),
                                            win_width)
    stdscr.addstr(0, 0, wrapped_text)
    stdscr.addstr(15, 0, wrapped_translated_text, curses.color_pair(1))
    stdscr.refresh()
    time.sleep(20)
except KeyboardInterrupt:
    pass
finally:
    curses.echo()
    curses.nocbreak()
    curses.endwin()
