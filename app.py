import asyncio
import base64
import json

import streamlit as st
import streamlit.components.v1 as components

try:
    import edge_tts
except ImportError:
    edge_tts = None


st.set_page_config(
    page_title="Laboratório do Amor",
    page_icon="❤️",
    layout="centered",
)

st.title("❤️ Laboratório do Amor")
st.caption("Sentir → observar → compreender → escolher → agir")

st.markdown(
    """
Uma jornada guiada em quatro etapas:

**1. Amor a DEUS → 2. Amor ao Próximo → 3. Anseio e Propósito → 4. Integração Noturna de 1 hora**

Cada sessão funciona com um único botão:

**narração → cerca de 0,2 segundo → áudio automático**

Nas três primeiras etapas, a voz reaparece em momentos-chave enquanto o som abaixa suavemente.

Na última etapa, a voz faz a preparação inicial e depois o áudio monaural + isocrônico segue sozinho por 1 hora.
"""
)


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24 * 7)
def gerar_clipes_neurais(textos, voz, rate="-14%", pitch="-2Hz"):
    if edge_tts is None:
        return tuple(b"" for _ in textos)

    async def _run():
        saidas = []

        for texto in textos:
            dados = bytearray()

            communicate = edge_tts.Communicate(
                text=texto,
                voice=voz,
                rate=rate,
                pitch=pitch,
            )

            async for chunk in communicate.stream():

                if chunk.get("type") == "audio":

                    dados.extend(
                        chunk.get(
                            "data",
                            b""
                        )
                    )

            saidas.append(
                bytes(dados)
            )

        return tuple(saidas)

    loop = asyncio.new_event_loop()

    try:

        return loop.run_until_complete(
            _run()
        )

    finally:

        loop.close()


def mp3_data_uri(data):

    if not data:
        return ""

    encoded = base64.b64encode(
        data
    ).decode("ascii")

    return (
        "data:audio/mpeg;base64,"
        + encoded
    )


def sessao_guiada(
    titulo,
    intro_texto,
    prompts,
    duracao_seg,
    modo,
    voz,
    pausa_apos_voz=0.2,
    altura=330,
):

    textos = (
        [intro_texto]
        +
        [item[1] for item in prompts]
    )

    if edge_tts is None:

        st.error(
            "A dependência edge-tts não está instalada."
        )

        return

    with st.spinner(
        "Preparando a voz neural em português..."
    ):

        try:

            clips = gerar_clipes_neurais(
                tuple(textos),
                voz
            )

        except Exception as exc:

            st.error(
                "Não foi possível carregar a voz neural. "
                "Verifique a conexão do servidor Streamlit "
                "com a internet."
            )

            st.caption(
                "Detalhe técnico: "
                + type(exc).__name__
            )

            return

    if not clips or not clips[0]:

        st.error(
            "A voz neural não retornou áudio."
        )

        return

    intro_uri = mp3_data_uri(
        clips[0]
    )

    prompt_payload = []

    for (
        segundo,
        texto
    ), clip in zip(
        prompts,
        clips[1:]
    ):

        prompt_payload.append(
            {
                "at": float(segundo),
                "text": texto,
                "src": mp3_data_uri(
                    clip
                ),
            }
        )

    # Não é f-string.
    # Assim, as chaves do JavaScript são seguras.

    html_code = r'''
<div style="
    font-family:Arial,sans-serif;
    padding:16px;
    border:1px solid rgba(128,128,128,.28);
    border-radius:16px;
    background:rgba(128,128,128,.05)
">

    <div style="
        font-size:18px;
        font-weight:700;
        margin-bottom:4px
    ">
        🎧 __TITLE__
    </div>

    <div style="
        font-size:13px;
        opacity:.78;
        margin-bottom:14px
    ">
        Um toque inicia toda a sequência automaticamente.
    </div>

    <div style="
        display:flex;
        gap:8px;
        flex-wrap:wrap;
        margin-bottom:12px
    ">

        <button
            onclick="startSession()"
            style="
                padding:10px 16px;
                border-radius:9px;
                border:0;
                cursor:pointer;
                font-weight:700
            "
        >
            ▶ Iniciar sessão
        </button>

        <button
            onclick="pauseSession()"
            style="
                padding:9px 12px;
                border-radius:9px;
                cursor:pointer
            "
        >
            ⏸ Pausar
        </button>

        <button
            onclick="resumeSession()"
            style="
                padding:9px 12px;
                border-radius:9px;
                cursor:pointer
            "
        >
            ⏯ Continuar
        </button>

        <button
            onclick="stopSession()"
            style="
                padding:9px 12px;
                border-radius:9px;
                cursor:pointer
            "
        >
            ⏹ Parar
        </button>

    </div>

    <div style="
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:14px;
        margin:10px 0 12px
    ">

        <label style="font-size:12px">

            Voz

            <br>

            <input
                id="voiceVol"
                type="range"
                min="0.25"
                max="1"
                value="0.88"
                step="0.05"
                style="width:100%"
            >

        </label>

        <label style="font-size:12px">

            Som

            <br>

            <input
                id="soundVol"
                type="range"
                min="0.02"
                max="0.30"
                value="0.12"
                step="0.01"
                style="width:100%"
            >

        </label>

    </div>

    <div
        id="status"
        style="
            font-size:13px;
            margin-bottom:8px
        "
    >
        Pronto para iniciar.
    </div>

    <div style="
        height:8px;
        border-radius:8px;
        background:rgba(128,128,128,.18);
        overflow:hidden
    ">

        <div
            id="bar"
            style="
                height:100%;
                width:0%;
                background:currentColor;
                opacity:.55;
                transition:width .4s linear
            "
        >
        </div>

    </div>

    <div
        id="clock"
        style="
            font-size:12px;
            opacity:.70;
            margin-top:6px
        "
    >
        00:00
    </div>

</div>


<script>

const introSrc =
    __INTRO__;

const prompts =
    __PROMPTS__;

const duration =
    __DURATION__;

const mode =
    __MODE__;

const pauseAfterVoice =
    __PAUSE_MS__;


let ctx = null;

let master = null;

let nodes = [];

let introAudio = null;

let activeVoice = null;

let startCtxTime = null;

let timer = null;

let keepAliveOsc = null;

let keepAliveGain = null;

let stopped = true;

let paused = false;


prompts.forEach(
    function (p) {

        p.played =
            false;

    }
);


function fmt(sec) {

    sec = Math.max(
        0,
        Math.floor(sec)
    );

    const m =
        String(
            Math.floor(
                sec / 60
            )
        ).padStart(
            2,
            "0"
        );

    const s =
        String(
            sec % 60
        ).padStart(
            2,
            "0"
        );

    return (
        m
        +
        ":"
        +
        s
    );

}


function status(texto) {

    document.getElementById(
        "status"
    ).innerText =
        texto;

}


function makeContext() {

    if (
        !ctx
        ||
        ctx.state === "closed"
    ) {

        ctx = new (
            window.AudioContext
            ||
            window.webkitAudioContext
        )();

    }

}


function startKeepAlive() {

    if (
        !ctx
        ||
        keepAliveOsc
    ) {

        return;

    }

    keepAliveOsc =
        ctx.createOscillator();

    keepAliveGain =
        ctx.createGain();


    keepAliveOsc.frequency.value =
        20;

    keepAliveGain.gain.value =
        0.000001;


    keepAliveOsc.connect(
        keepAliveGain
    );

    keepAliveGain.connect(
        ctx.destination
    );


    keepAliveOsc.start();

}


function stopKeepAlive() {

    if (keepAliveOsc) {

        try {

            keepAliveOsc.stop();

        }

        catch (e) {}


        try {

            keepAliveOsc.disconnect();

        }

        catch (e) {}

    }


    if (keepAliveGain) {

        try {

            keepAliveGain.disconnect();

        }

        catch (e) {}

    }


    keepAliveOsc =
        null;

    keepAliveGain =
        null;

}


function createBinaural(
    base,
    points
) {

    const merger =
        ctx.createChannelMerger(2);

    const gL =
        ctx.createGain();

    const gR =
        ctx.createGain();

    const left =
        ctx.createOscillator();

    const right =
        ctx.createOscillator();


    gL.gain.value =
        0.46;

    gR.gain.value =
        0.46;


    left.type =
        "sine";

    right.type =
        "sine";


    left.frequency.value =
        base;


    right.frequency.setValueAtTime(
        base
        +
        points[0][1],
        ctx.currentTime
    );


    points
        .slice(1)
        .forEach(
            function (p) {

                const t =
                    ctx.currentTime
                    +
                    p[0];

                const value =
                    base
                    +
                    p[1];


                if (
                    p[2]
                    ===
                    "ramp"
                ) {

                    right.frequency
                        .linearRampToValueAtTime(
                            value,
                            t
                        );

                }

                else {

                    right.frequency
                        .setValueAtTime(
                            value,
                            t
                        );

                }

            }
        );


    left.connect(
        gL
    );

    right.connect(
        gR
    );


    gL.connect(
        merger,
        0,
        0
    );

    gR.connect(
        merger,
        0,
        1
    );


    merger.connect(
        master
    );


    left.start();

    right.start();


    left.stop(
        ctx.currentTime
        +
        duration
        +
        1
    );

    right.stop(
        ctx.currentTime
        +
        duration
        +
        1
    );


    nodes.push(
        left,
        right,
        gL,
        gR,
        merger
    );

}


function createMonauralIso() {

    const mix =
        ctx.createGain();

    const o1 =
        ctx.createOscillator();

    const o2 =
        ctx.createOscillator();

    const mod =
        ctx.createGain();

    const lfo =
        ctx.createOscillator();

    const lfoDepth =
        ctx.createGain();


    mix.gain.value =
        0.50;


    o1.type =
        "sine";

    o2.type =
        "sine";


    o1.frequency.value =
        100;


    o2.frequency.setValueAtTime(
        106,
        ctx.currentTime
    );


    o2.frequency.setValueAtTime(
        106,
        ctx.currentTime
        +
        1770
    );


    o2.frequency
        .linearRampToValueAtTime(
            102.5,
            ctx.currentTime
            +
            1830
        );


    o2.frequency.setValueAtTime(
        102.5,
        ctx.currentTime
        +
        3600
    );


    mod.gain.value =
        0.59;


    lfo.type =
        "sine";


    lfo.frequency.setValueAtTime(
        6,
        ctx.currentTime
    );


    lfo.frequency.setValueAtTime(
        6,
        ctx.currentTime
        +
        1770
    );


    lfo.frequency
        .linearRampToValueAtTime(
            2.5,
            ctx.currentTime
            +
            1830
        );


    lfo.frequency.setValueAtTime(
        2.5,
        ctx.currentTime
        +
        3600
    );


    lfoDepth.gain.value =
        0.41;


    lfo.connect(
        lfoDepth
    );


    lfoDepth.connect(
        mod.gain
    );


    o1.connect(
        mix
    );


    o2.connect(
        mix
    );


    mix.connect(
        mod
    );


    mod.connect(
        master
    );


    o1.start();

    o2.start();

    lfo.start();


    o1.stop(
        ctx.currentTime
        +
        duration
        +
        1
    );


    o2.stop(
        ctx.currentTime
        +
        duration
        +
        1
    );


    lfo.stop(
        ctx.currentTime
        +
        duration
        +
        1
    );


    nodes.push(
        o1,
        o2,
        lfo,
        mix,
        mod,
        lfoDepth
    );

}


function createSound() {

    master =
        ctx.createGain();


    const requested =
        parseFloat(
            document
                .getElementById(
                    "soundVol"
                )
                .value
        );


    master.gain.setValueAtTime(
        0.0001,
        ctx.currentTime
    );


    master.gain
        .exponentialRampToValueAtTime(
            Math.max(
                requested,
                0.001
            ),
            ctx.currentTime
            +
            0.45
        );


    master.connect(
        ctx.destination
    );


    if (
        mode
        ===
        "amor"
    ) {

        createBinaural(
            150,
            [
                [
                    0,
                    8,
                    "set"
                ],
                [
                    120,
                    10,
                    "set"
                ],
                [
                    600,
                    10,
                    "set"
                ],
                [
                    duration,
                    20,
                    "ramp"
                ]
            ]
        );

    }


    else if (
        mode
        ===
        "proximo"
    ) {

        createBinaural(
            145,
            [
                [
                    0,
                    10,
                    "set"
                ],
                [
                    Math.max(
                        duration
                        -
                        120,
                        0
                    ),
                    10,
                    "set"
                ],
                [
                    duration,
                    12,
                    "ramp"
                ]
            ]
        );

    }


    else if (
        mode
        ===
        "anseio"
    ) {

        const p1 =
            duration
            *
            0.20;

        const p2 =
            duration
            *
            0.50;

        const p3 =
            duration
            *
            0.80;


        createBinaural(
            110,
            [
                [
                    0,
                    8,
                    "set"
                ],
                [
                    p1,
                    10,
                    "set"
                ],
                [
                    p2,
                    10,
                    "set"
                ],
                [
                    p3,
                    14,
                    "ramp"
                ],
                [
                    duration,
                    18,
                    "ramp"
                ]
            ]
        );

    }


    else if (
        mode
        ===
        "noturno"
    ) {

        createMonauralIso();

    }

}


function playVoice(
    src,
    label
) {

    return new Promise(
        function (resolve) {

            if (!src) {

                resolve();

                return;

            }


            if (activeVoice) {

                try {

                    activeVoice.pause();

                }

                catch (e) {}

            }


            const audio =
                new Audio(src);


            activeVoice =
                audio;


            audio.volume =
                parseFloat(
                    document
                        .getElementById(
                            "voiceVol"
                        )
                        .value
                );


            if (
                master
                &&
                ctx
            ) {

                const atual =
                    Math.max(
                        master.gain.value,
                        0.001
                    );


                master.gain
                    .cancelScheduledValues(
                        ctx.currentTime
                    );


                master.gain
                    .setValueAtTime(
                        atual,
                        ctx.currentTime
                    );


                master.gain
                    .linearRampToValueAtTime(
                        0.018,
                        ctx.currentTime
                        +
                        0.25
                    );

            }


            status(
                label
            );


            audio.onended =
                function () {

                    if (
                        master
                        &&
                        ctx
                        &&
                        !stopped
                    ) {

                        const volume =
                            parseFloat(
                                document
                                    .getElementById(
                                        "soundVol"
                                    )
                                    .value
                            );


                        master.gain
                            .cancelScheduledValues(
                                ctx.currentTime
                            );


                        master.gain
                            .setValueAtTime(
                                Math.max(
                                    master.gain.value,
                                    0.001
                                ),
                                ctx.currentTime
                            );


                        master.gain
                            .linearRampToValueAtTime(
                                Math.max(
                                    volume,
                                    0.001
                                ),
                                ctx.currentTime
                                +
                                0.45
                            );

                    }


                    activeVoice =
                        null;


                    status(
                        "🎵 Continue a prática..."
                    );


                    resolve();

                };


            audio.onerror =
                function () {

                    activeVoice =
                        null;

                    resolve();

                };


            audio
                .play()
                .catch(
                    function () {

                        activeVoice =
                            null;

                        resolve();

                    }
                );

        }
    );

}


async function beginTone() {

    if (stopped)
        return;


    if (
        !ctx
        ||
        ctx.state
        ===
        "closed"
    ) {

        makeContext();

    }


    try {

        if (
            ctx.state
            !==
            "running"
        ) {

            await ctx.resume();

        }

    }

    catch (e) {}


    stopKeepAlive();


    createSound();


    startCtxTime =
        ctx.currentTime;


    status(
        "🎵 Áudio iniciado automaticamente."
    );


    prompts.forEach(
        function (p) {

            p.played =
                false;

        }
    );


    timer =
        setInterval(
            function () {

                if (
                    !ctx
                    ||
                    startCtxTime
                    ===
                    null
                    ||
                    stopped
                ) {

                    return;

                }


                const elapsed =
                    Math.min(
                        duration,
                        ctx.currentTime
                        -
                        startCtxTime
                    );


                document
                    .getElementById(
                        "clock"
                    )
                    .innerText =
                        fmt(elapsed)
                        +
                        " / "
                        +
                        fmt(duration);


                document
                    .getElementById(
                        "bar"
                    )
                    .style
                    .width =
                        (
                            (
                                elapsed
                                /
                                duration
                            )
                            *
                            100
                        )
                        .toFixed(2)
                        +
                        "%";


                prompts.forEach(
                    function (p) {

                        if (
                            !p.played
                            &&
                            elapsed
                            >=
                            p.at
                        ) {

                            p.played =
                                true;


                            playVoice(
                                p.src,
                                "🎙️ Orientação durante a prática"
                            );

                        }

                    }
                );


                if (
                    elapsed
                    >=
                    duration
                ) {

                    finishSession();

                }

            },
            500
        );

}


async function startSession() {

    stopSession(
        false
    );


    stopped =
        false;

    paused =
        false;


    makeContext();


    try {

        await ctx.resume();

    }

    catch (e) {}


    startKeepAlive();


    status(
        "🎙️ Narração inicial..."
    );


    document
        .getElementById(
            "bar"
        )
        .style
        .width =
            "0%";


    document
        .getElementById(
            "clock"
        )
        .innerText =
            "Narração inicial";


    introAudio =
        new Audio(
            introSrc
        );


    introAudio.volume =
        parseFloat(
            document
                .getElementById(
                    "voiceVol"
                )
                .value
        );


    introAudio.onended =
        function () {

            if (stopped)
                return;


            status(
                "🎵 Entrando no áudio..."
            );


            setTimeout(
                function () {

                    beginTone();

                },
                pauseAfterVoice
            );

        };


    introAudio.onerror =
        function () {

            setTimeout(
                function () {

                    beginTone();

                },
                pauseAfterVoice
            );

        };


    introAudio
        .play()
        .catch(
            function () {

                status(
                    "O navegador bloqueou a voz. "
                    +
                    "Toque novamente em Iniciar sessão."
                );

            }
        );

}


// ========================================================
// PAUSAR
// ========================================================

function pauseSession() {

    if (stopped)
        return;


    paused =
        true;


    if (
        introAudio
        &&
        !introAudio.paused
    ) {

        introAudio.pause();

    }


    if (
        activeVoice
        &&
        !activeVoice.paused
    ) {

        activeVoice.pause();

    }


    if (
        ctx
        &&
        ctx.state
        ===
        "running"
    ) {

        ctx.suspend();

    }


    status(
        "⏸ Sessão pausada."
    );

}


// ========================================================
// CONTINUAR
// ========================================================

function resumeSession() {

    if (stopped)
        return;


    paused =
        false;


    if (
        ctx
        &&
        ctx.state
        ===
        "suspended"
    ) {

        ctx.resume();

    }


    if (
        activeVoice
        &&
        activeVoice.paused
    ) {

        activeVoice
            .play()
            .catch(
                function () {}
            );

    }


    else if (
        introAudio
        &&
        introAudio.paused
        &&
        startCtxTime
        ===
        null
    ) {

        introAudio
            .play()
            .catch(
                function () {}
            );

    }


    status(
        "▶ Sessão retomada."
    );

}


// ========================================================
// PARAR
// ========================================================

function stopSession(
    showStatus
) {

    if (
        typeof showStatus
        ===
        "undefined"
    ) {

        showStatus =
            true;

    }


    stopped =
        true;

    paused =
        false;


    if (timer) {

        clearInterval(
            timer
        );

        timer =
            null;

    }


    if (introAudio) {

        try {

            introAudio.pause();

            introAudio.currentTime =
                0;

        }

        catch (e) {}

    }


    if (activeVoice) {

        try {

            activeVoice.pause();

            activeVoice.currentTime =
                0;

        }

        catch (e) {}

    }


    nodes.forEach(
        function (node) {

            try {

                if (node.stop) {

                    node.stop();

                }

            }

            catch (e) {}


            try {

                if (node.disconnect) {

                    node.disconnect();

                }

            }

            catch (e) {}

        }
    );


    nodes =
        [];


    stopKeepAlive();


    if (
        ctx
        &&
        ctx.state
        !==
        "closed"
    ) {

        try {

            ctx.close();

        }

        catch (e) {}

    }


    ctx =
        null;

    master =
        null;

    startCtxTime =
        null;

    introAudio =
        null;

    activeVoice =
        null;


    if (showStatus) {

        status(
            "⏹ Sessão encerrada."
        );


        document
            .getElementById(
                "bar"
            )
            .style
            .width =
                "0%";


        document
            .getElementById(
                "clock"
            )
            .innerText =
                "00:00";

    }

}


function finishSession() {

    if (timer) {

        clearInterval(
            timer
        );

        timer =
            null;

    }


    if (
        master
        &&
        ctx
    ) {

        const atual =
            Math.max(
                master.gain.value,
                0.001
            );


        master.gain
            .cancelScheduledValues(
                ctx.currentTime
            );


        master.gain
            .setValueAtTime(
                atual,
                ctx.currentTime
            );


        master.gain
            .exponentialRampToValueAtTime(
                0.0001,
                ctx.currentTime
                +
                4
            );

    }


    status(
        "✅ Sessão concluída."
    );


    document
        .getElementById(
            "bar"
        )
        .style
        .width =
            "100%";


    setTimeout(
        function () {

            stopSession(
                false
            );

        },
        4500
    );

}


document
    .getElementById(
        "soundVol"
    )
    .addEventListener(

        "input",

        function (event) {

            if (
                master
                &&
                ctx
                &&
                !stopped
            ) {

                master.gain
                    .setTargetAtTime(
                        parseFloat(
                            event.target.value
                        ),
                        ctx.currentTime,
                        0.2
                    );

            }

        }

    );

</script>
'''

    html_code = (
        html_code
        .replace(
            "__TITLE__",
            titulo
        )
        .replace(
            "__INTRO__",
            json.dumps(
                intro_uri,
                ensure_ascii=False
            )
        )
        .replace(
            "__PROMPTS__",
            json.dumps(
                prompt_payload,
                ensure_ascii=False
            )
        )
        .replace(
            "__DURATION__",
            str(
                float(
                    duracao_seg
                )
            )
        )
        .replace(
            "__MODE__",
            json.dumps(
                modo
            )
        )
        .replace(
            "__PAUSE_MS__",
            str(
                float(
                    pausa_apos_voz
                )
                *
                1000
            )
        )
    )

    components.html(
        html_code,
        height=altura
    )


# ============================================================
# ETAPA 1 — AMOR A DEUS
# ============================================================

INTRO_AMOR = (
    "Encontre uma posição confortável. "
    "Coloque uma das mãos sobre o coração. "
    "Feche os olhos, se isso for confortável. "
    "Inspire suavemente e expire devagar. "
    "Não tente fabricar nenhuma emoção. "
    "Apenas desacelere. "
    "Observe também o pensamento que estava ocupando sua mente antes de começar. "
    "Não lute contra ele. Apenas perceba. "
    "Daqui a pouco o som começará sozinho. "
    "Permaneça presente e permita que a gratidão "
    "abra espaço para o Amor a Deus."
)


PROMPTS_AMOR = [

    (
        120,

        "Agora recorde algo concreto "
        "pelo qual você agradece profundamente a Deus. "
        "Não fique apenas na ideia. "
        "Permita que a gratidão seja sentida. "
        "Observe o que acontece com sua mente "
        "enquanto permanece na gratidão."
    ),

    (
        420,

        "Pergunte em silêncio: "
        "se eu viver a partir deste Amor a Deus hoje, "
        "o que muda na maneira como penso? "
        "Que pensamento pode ser visto "
        "de uma nova maneira?"
    ),

    (
        600,

        "Compare seu estado atual "
        "com o início da prática. "
        "Agora escolha uma ação concreta "
        "que expresse esse Amor. "
        "Agradecer, ajudar, pedir perdão, "
        "escutar, acolher ou servir."
    ),

]


# ============================================================
# ETAPA 2 — AMOR AO PRÓXIMO
# ============================================================

INTRO_PROXIMO = (
    "Traga à mente uma pessoa. "
    "Antes de pensar sobre o que ela fez "
    "ou deixou de fazer, "
    "observe qual julgamento aparece primeiro em sua mente. "
    "Não lute contra ele. Apenas perceba. "
    "Agora comece não pelo problema dessa pessoa, "
    "mas pelo Amor. "
    "Reconheça que diante de você existe "
    "uma vida com valor, história, medos, "
    "desejos e necessidades. "
    "Respire lentamente e deseje sinceramente "
    "o bem dessa pessoa. "
    "O som começará sozinho. "
    "Use a empatia como ponte "
    "para transformar Amor em presença e ação."
)


PROMPTS_PROXIMO = [

    (
        120,

        "Pergunte: "
        "o que eu realmente sei "
        "sobre o que essa pessoa está vivendo? "
        "Separe fatos de suposições."
    ),

    (
        300,

        "O que ela pode estar sentindo "
        "ou precisando? "
        "Ser ouvida, respeitada, compreendida, "
        "ajudada ou simplesmente não estar sozinha?"
    ),

    (
        480,

        "Observe novamente seu julgamento inicial. "
        "Você percebe algo diferente agora? "
        "Pergunte: "
        "o que significa amar esta pessoa hoje? "
        "Escolha um gesto concreto de cuidado."
    ),

]


# ============================================================
# ETAPA 4 — INTEGRAÇÃO NOTURNA
# ============================================================

INTRO_NOTURNO = (
    "Esta é a última etapa. "
    "Não há mais nada para conquistar agora. "
    "Relaxe a testa, os olhos, "
    "a mandíbula e os ombros. "
    "Inspire suavemente "
    "e expire um pouco mais devagar. "
    "Recorde algo bom deste dia "
    "e agradeça. "
    "Se algum pensamento aparecer, "
    "observe sem precisar segui-lo. "
    "Quando minha voz terminar, "
    "o áudio de uma hora começará "
    "quase imediatamente. "
    "Depois disso, a voz não voltará. "
    "Apenas descanse."
)


# ============================================================
# ETAPA 3 — ANSEIO E PROPÓSITO
# ============================================================

def roteiro_anseio(
    anseio
):

    desejo = (
        anseio
        or
        ""
    ).strip()


    if desejo:

        foco = (
            "O seu anseio escolhido é: "
            +
            desejo
            +
            ". "
        )

    else:

        foco = (
            "Escolha agora um anseio verdadeiro "
            "e significativo para a sua vida. "
        )


    intro = (

        "Encontre uma posição confortável "
        "e volte ao presente. "

        "Perceba a respiração "
        "e o coração. "

        +
        foco

        +
        "Pergunte por que isso "
        "é realmente importante para você. "

        "Pergunte também "
        "o que você acredita que sentiria "
        "se isso acontecesse. "

        "Conecte esse anseio ao Amor. "

        "Como ele pode produzir "
        "mais vida, crescimento, "
        "cuidado ou contribuição? "

        "O som começará sozinho "
        "e conduzirá a passagem "
        "do desejo para clareza e ação."

    )


    prompts = [

        (
            120,

            "Recorde algo "
            "pelo qual você já é grato. "
            "Gratidão ajuda a sair "
            "da sensação de falta "
            "e voltar à presença."
        ),

        (
            300,

            "Imagine como seria viver "
            "de maneira coerente "
            "com esse anseio. "
            "Observe os pensamentos "
            "e possibilidades que surgem. "
            "Quais pensamentos ajudam você a caminhar "
            "e quais apenas repetem medo?"
        ),

        (
            480,

            "Agora transforme "
            "a visão em compromisso. "
            "Qual é o menor passo real "
            "que depende de você?"
        ),

    ]


    return (
        intro,
        prompts
    )


# ============================================================
# VOZ
# ============================================================

with st.sidebar:

    st.header(
        "🎙️ Voz"
    )


    voz_label = st.radio(

        "Escolha a narração",

        [
            "Feminina suave",
            "Masculina suave"
        ],

        index=0,

    )


    voz = (

        "pt-BR-FranciscaNeural"

        if
        voz_label
        ==
        "Feminina suave"

        else
        "pt-BR-AntonioNeural"

    )


    st.caption(
        "A voz neural precisa de conexão "
        "com a internet no servidor Streamlit "
        "na primeira geração. "
        "Depois fica em cache."
    )


# ============================================================
# ESCOLHA DA ETAPA
# ============================================================

etapa = st.radio(

    "Escolha a etapa",

    [
        "1 · Amor a DEUS",
        "2 · Amor ao Próximo",
        "3 · Anseio e Propósito",
        "4 · Integração Noturna — 1h",
    ],

    horizontal=True,

)


st.divider()


# ============================================================
# ETAPA 1 — AMOR A DEUS
# ============================================================

if etapa.startswith(
    "1"
):

    st.subheader(
        "1. A Volta ao Amor Principal"
    )


    st.markdown(
        """
### Amor a DEUS

**presença → gratidão → sentir o Amor a DEUS → pensamento → ação**
"""
    )


    sessao_guiada(

        titulo=
            "Amor a DEUS e Gratidão",

        intro_texto=
            INTRO_AMOR,

        prompts=
            PROMPTS_AMOR,

        duracao_seg=
            12
            *
            60,

        modo=
            "amor",

        voz=
            voz,

        pausa_apos_voz=
            0.2,

    )


    st.text_area(
        "Por quais três coisas "
        "você agradece a DEUS hoje?",
        key="gratidao"
    )


    st.text_input(
        "Que ação nascerá "
        "desse Amor a DEUS?",
        key="acao_deus"
    )


# ============================================================
# ETAPA 2 — AMOR AO PRÓXIMO
# ============================================================

elif etapa.startswith(
    "2"
):

    st.subheader(
        "2. Amor ao Próximo e Empatia"
    )


    st.markdown(
        """
**Amor → empatia → compreensão → pensamento → escolha → ação → bem-estar do outro**

A empatia é a ponte.

**Amar o próximo é o objetivo.**
"""
    )


    sessao_guiada(

        titulo=
            "Amor ao Próximo e Empatia",

        intro_texto=
            INTRO_PROXIMO,

        prompts=
            PROMPTS_PROXIMO,

        duracao_seg=
            10
            *
            60,

        modo=
            "proximo",

        voz=
            voz,

        pausa_apos_voz=
            0.2,

    )


    st.text_input(
        "Em quem você deseja "
        "concentrar a prática?",
        key="pessoa"
    )


    st.text_area(
        "O que você realmente sabe "
        "sobre o que essa pessoa vive?",
        key="situacao"
    )


    st.text_area(
        "Que necessidade humana "
        "pode estar presente?",
        key="necessidade"
    )


    st.text_input(
        "Que ação concreta "
        "pode expressar Amor ao próximo?",
        key="acao_empatia"
    )


# ============================================================
# ETAPA 3 — ANSEIO E PROPÓSITO
# ============================================================

elif etapa.startswith(
    "3"
):

    st.subheader(
        "3. Anseio e Propósito"
    )


    st.markdown(
        """
**anseio → sentimento → pensamento → visão → escolha → ação**
"""
    )


    anseio = st.text_area(

        "Qual é o seu anseio "
        "neste momento?",

        placeholder=(
            "Ex.: reconstruir uma relação, "
            "realizar um projeto, "
            "encontrar um trabalho com propósito..."
        ),

        key="anseio",

    )


    st.text_area(
        "Por que isso "
        "é importante para você?",
        key="sentido_anseio"
    )


    intro_anseio, prompts_anseio = (
        roteiro_anseio(
            anseio
        )
    )


    sessao_guiada(

        titulo=
            "Anseio, Fé, Visão e Ação",

        intro_texto=
            intro_anseio,

        prompts=
            prompts_anseio,

        duracao_seg=
            10
            *
            60,

        modo=
            "anseio",

        voz=
            voz,

        pausa_apos_voz=
            0.2,

    )


    st.text_area(
        "Se esse anseio avançar, "
        "o que muda concretamente?",
        key="visao_anseio"
    )


    st.text_input(
        "Qual é o próximo passo real "
        "que depende de você?",
        key="proximo_passo_anseio"
    )


# ============================================================
# ETAPA 4 — INTEGRAÇÃO NOTURNA
# ============================================================

else:

    st.subheader(
        "4. Integração Noturna — 1 Hora"
    )


    st.markdown(
        """
Esta é **sempre a última etapa**.

Primeiro vem uma preparação narrada curta.

Assim que a narração termina, o áudio começa quase imediatamente e a voz não volta.

### Estrutura do som

**0:00–29:30:** 6 Hz

**29:30–30:30:** transição suave de 6 Hz para 2,5 Hz

**30:30–60:00:** 2,5 Hz

O sinal combina **batimento monaural + modulação isocrônica**.
"""
    )


    sessao_guiada(

        titulo=
            "Integração Noturna — 1 hora",

        intro_texto=
            INTRO_NOTURNO,

        prompts=
            [],

        duracao_seg=
            60
            *
            60,

        modo=
            "noturno",

        voz=
            voz,

        pausa_apos_voz=
            0.2,

    )


    st.info(
        "Durante a sessão de 1 hora, "
        "evite bloquear ou suspender "
        "o navegador, pois isso pode "
        "interromper o áudio."
    )


# ============================================================
# FECHAMENTO
# ============================================================

st.divider()


st.markdown(
    """
## O ciclo completo

**DEUS → Amor a DEUS → coração → gratidão → pensamento → Amor ao Próximo → empatia → propósito → ação → integração → descanso**
"""
)
