FROM docker.io/fedora:27


LABEL ios.k8s.display-name="deepspeech" \
    maintainer="Keith Tenzer <ktenzer@redhat.com>"

RUN dnf groupinstall -y 'C Development Tools and Libraries'
RUN dnf install -y python2 \
    python2-devel \
    git \
    wget \
    swig \
    langpacks-de \
    langpacks-es \
    langpacks-fr \
    langpacks-pl

RUN mkdir /deepspeech

RUN pip2 install 'deepspeech==0.3.0' \
    jamspell \
    webrtcvad \
    requests \
    certifi \
    urllib3 \
    idna \
    chardet

RUN cd /deepspeech && \
    git clone https://github.com/BoseCorp/py-googletrans.git && \
    cd /deepspeech/py-googletrans && \
    python2 /deepspeech/py-googletrans/setup.py install && \
    rm -rf /deepspeech/py-googletrans

RUN wget https://github.com/mozilla/DeepSpeech/releases/download/v0.3.0/deepspeech-0.3.0-models.tar.gz -P /deepspeech && \
    tar xzf /deepspeech/deepspeech-0.3.0-models.tar.gz -C /deepspeech && \
    rm -f /deepspeech/deepspeech-0.3.0-models.tar.gz

RUN wget https://github.com/bakwc/JamSpell-models/raw/master/en.tar.gz -P /deepspeech && \
    tar xzf /deepspeech/en.tar.gz -C /deepspeech/models && \
    rm -f /deepspeech/en.tar.gz

RUN wget https://github.com/bakwc/JamSpell-models/raw/master/fr.tar.gz -P /deepspeech && \
    tar xzf /deepspeech/fr.tar.gz -C /deepspeech/models && \
    rm -f /deepspeech/fr.tar.gz

RUN  wget https://github.com/bakwc/JamSpell-models/raw/master/ru.tar.gz -P /deepspeech && \
    tar xzf /deepspeech/ru.tar.gz -C /deepspeech/models && \
    rm -f /deepspeech/ru.tar.gz

RUN mv /deepspeech/models/ru_small.bin /deepspeech/models/ru.bin

RUN git clone https://github.com/ktenzer/gpu-demo.git /deepspeech/gpu-demo

COPY demo.wav /deepspeech

RUN chown -R 1001:0 /deepspeech && \
    chown -R 1001:0 $HOME

RUN echo "1.0" > /etc/imageversion

USER 1001

CMD ["-c", "--", "while true; do sleep 30; done;"]
