# GPU-DEMO
Uses deepspeech and tensorflow to recognize voice recording and translate using google translate to the desired language. Output of what was recognized in the recording and translation done to stdout. The source language can be anything but the model we are using only supports English.

## Prerequisites
* A wave 16-bit file recorded in English using 16Khz and mono.
* Python2
* Python2-devel
* Development tools and libraries (gcc, etc)
* Python modules
  * deepspeech or deepspeech-gpu
  * googletrans
  * jamspell
  * numpy
  * webrtcvad
* Models
  * Deepspeech model
  * Jamspell model

## Usage
The translation language can be anything supported by [google translate](https://cloud.google.com/translate/docs/languages). Use the ISO-639-1 code but ensure the locale exists in Dockerfile.
```
$ python2 stream_with_sentences.py --slang <en|fr|ru> --tlang <en|fr|ru|pl> --file </path/to/.wav> --models </path/to/models>
```
