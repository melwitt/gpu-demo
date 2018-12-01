# GPU-DEMO
Uses deepspeech and tensorflow to recognize voice recording in english and translate using google translate to the desired language. Output of what was recognized in the recording and translation done to stdout.

## Prerequisites
* A wave file recorded in English using 16Khz and mono. Should be saved as 16bit PCM.
* Python2
* Python2-devel
* Development tools and libraries (gcc, etc)
* Python modules
** deepspeech or deepspeech-gpu
** googletrans
** jamspell
** numpy
** webrtcvad

## Usage
The translation language can be anything supported by [google translate](https://cloud.google.com/translate/docs/languages). Use the ISO-639-1 code.
```
$ python2 stream_with_sentences.py --lang <en|de|es|pl> --file </path/to/.wav> --models </path/to/models>
```
