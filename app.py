import asyncio
import base64
import html
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

try:
    import edge_tts
except ImportError:
    edge_tts = None


# ============================================================
# PÁGINA
# ============================================================

st.set_page_config(
    page_title="Manual Prático do Amor",
    page_icon="❤️",
    layout="centered",
)

st.title("❤️ Manual Prático do Amor")
st.caption("Sentir → observar → compreender → escolher → agir")


# ============================================================
# VOZ NEURAL
# ============================================================

@st.cache_data(
    show_spinner=False,
    ttl=60 * 60 * 24 * 7
)
def gerar_vozes(
    textos,
    voz,
    rate="-14%",
    pitch="-2Hz"
):
    if edge_tts is None:
        return tuple(
            b"" for _ in textos
        )

    async def executar():
        saidas = []

        for texto in textos:
            dados = bytearray()

            tts = edge_tts.Communicate(
                text=texto,
                voice=voz,
                rate=rate,
                pitch=pitch,
            )

            async for chunk in tts.stream():

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
            executar()
        )

    finally:

        loop.close()


def data_uri(dados):

    return (
        "data:audio/mpeg;base64,"
        +
        base64.b64encode(
            dados
        ).decode("ascii")
    )


# ============================================================
# PLAYER
# ============================================================

def tocar_sessao(
    etapa,
    voz
):

    textos = (
        [etapa["intro"]]
        +
        [
            texto
            for _, texto in etapa["prompts"]
        ]
    )

    if edge_tts is None:

        st.error(
            "Instale a dependência edge-tts."
        )

        return


    with st.spinner(
        "Preparando a voz..."
    ):

        try:

            clips = gerar_vozes(
                tuple(textos),
                voz
            )

        except Exception as exc:

            st.error(
                "Não foi possível gerar a narração."
            )

            st.caption(
                type(exc).__name__
            )

            return


    if not clips or not clips[0]:

        st.error(
            "A narração não foi gerada."
        )

        return


    prompts = [

        {
            "at": float(segundo),
            "src": data_uri(clip),
        }

        for (
            segundo,
            _
        ), clip in zip(
            etapa["prompts"],
            clips[1:],
        )

    ]


    template_path = (
        Path(__file__)
        .with_name(
            "player.html"
        )
    )


    if not template_path.exists():

        st.error(
            "Arquivo player.html não encontrado."
        )

        return


    template = template_path.read_text(
        encoding="utf-8"
    )


    codigo = (

        template

        .replace(
            "__TITLE__",
            html.escape(
                etapa["titulo"]
            )
        )

        .replace(
            "__INTRO__",
            json.dumps(
                data_uri(
                    clips[0]
                ),
                ensure_ascii=False
            )
        )

        .replace(
            "__PROMPTS__",
            json.dumps(
                prompts,
                ensure_ascii=False
            )
        )

        .replace(
            "__DURATION__",
            str(
                float(
                    etapa["duracao"]
                )
            )
        )

        .replace(
            "__MODE__",
            json.dumps(
                etapa["modo"]
            )
        )

    )


    components.html(
        codigo,
        height=250,
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
            "O seu anseio é: "
            +
            desejo
            +
            ". "
        )

    else:

        foco = (
            "Escolha um anseio verdadeiro "
            "e significativo. "
        )


    return {

        "titulo":
            "Anseio e Propósito",

        "modo":
            "anseio",

        "duracao":
            10 * 60,

        "intro":
            (
                "Encontre uma posição confortável. "
                "Observe a respiração e o coração. "
                +
                foco
                +
                "Pergunte por que isso "
                "é importante para você. "
                "Observe o que você acredita "
                "que sentiria se isso acontecesse. "
                "Conecte esse anseio "
                "ao Amor e ao propósito."
            ),

        "prompts":
            [

                (
                    120,

                    "Recorde algo "
                    "pelo qual você já é grato."
                ),

                (
                    300,

                    "Imagine como seria viver "
                    "de maneira coerente "
                    "com esse anseio. "
                    "Observe os pensamentos "
                    "que ajudam "
                    "e os que apenas repetem medo."
                ),

                (
                    480,

                    "Qual é o menor passo real "
                    "que depende de você?"
                ),

            ],

    }


# ============================================================
# ETAPAS
# ============================================================

ETAPAS = {

    "1 · Amor a DEUS": {

        "titulo":
            "Amor a DEUS",

        "modo":
            "amor",

        "duracao":
            12 * 60,

        "intro":
            (
                "Encontre uma posição confortável. "
                "Coloque uma das mãos sobre o coração. "
                "Feche os olhos. "
                "Inspire suavemente "
                "e expire devagar. "
                "Observe o pensamento "
                "que estava ocupando sua mente. "
                "Não lute contra ele. "
                "Apenas observe. "
                "Agora recorde algo "
                "pelo qual você agradece a Deus. "
                "Permita que a gratidão "
                "abra espaço para o Amor a Deus."
            ),

        "prompts":
            [

                (
                    120,

                    "Recorde algo concreto "
                    "pelo qual você agradece "
                    "profundamente a Deus. "
                    "Não fique apenas na ideia. "
                    "Sinta a gratidão."
                ),

                (
                    420,

                    "Se eu viver "
                    "a partir deste Amor a Deus hoje, "
                    "o que muda "
                    "na maneira como penso?"
                ),

                (
                    600,

                    "Escolha uma ação concreta "
                    "que expresse esse Amor."
                ),

            ],

    },


    "2 · Amor ao Próximo": {

        "titulo":
            "Amor ao Próximo e Empatia",

        "modo":
            "proximo",

        "duracao":
            10 * 60,

        "intro":
            (
                "Traga uma pessoa à mente. "
                "Observe o julgamento "
                "que aparece primeiro. "
                "Reconheça que essa pessoa "
                "possui uma história, "
                "medos, desejos e necessidades. "
                "Deseje sinceramente "
                "o bem dela. "
                "Permita que a empatia "
                "seja uma ponte para o Amor."
            ),

        "prompts":
            [

                (
                    120,

                    "O que você realmente sabe "
                    "sobre o que essa pessoa "
                    "está vivendo? "
                    "Separe fatos de suposições."
                ),

                (
                    300,

                    "O que ela pode estar "
                    "sentindo ou precisando?"
                ),

                (
                    480,

                    "O que significa "
                    "amar esta pessoa hoje? "
                    "Escolha uma ação concreta."
                ),

            ],

    },


    "4 · Integração Noturna": {

        "titulo":
            "Integração Noturna",

        "modo":
            "noturno",

        "duracao":
            60 * 60,

        "intro":
            (
                "Esta é a última etapa. "
                "Relaxe a testa, "
                "os olhos, "
                "a mandíbula "
                "e os ombros. "
                "Respire devagar. "
                "Recorde algo bom "
                "deste dia "
                "e agradeça. "
                "Se algum pensamento aparecer, "
                "observe sem precisar segui-lo. "
                "Agora apenas descanse."
            ),

        "prompts":
            [],

    },

}


# ============================================================
# VOZ
# ============================================================

with st.sidebar:

    voz_nome = st.radio(

        "Voz",

        [
            "Feminina",
            "Masculina"
        ],

        horizontal=True,

    )


voz = (

    "pt-BR-FranciscaNeural"

    if
    voz_nome == "Feminina"

    else

    "pt-BR-AntonioNeural"

)


# ============================================================
# ESCOLHA DA ETAPA
# ============================================================

etapa_nome = st.radio(

    "Etapa",

    [
        "1 · Amor a DEUS",
        "2 · Amor ao Próximo",
        "3 · Anseio e Propósito",
        "4 · Integração Noturna",
    ],

)


# ============================================================
# ETAPA DINÂMICA
# ============================================================

if etapa_nome.startswith(
    "3"
):

    anseio = st.text_area(

        "Qual é o seu anseio?",

        key="anseio",

    )


    etapa = roteiro_anseio(
        anseio
    )


else:

    etapa = ETAPAS[
        etapa_nome
    ]


# ============================================================
# TÍTULO
# ============================================================

st.subheader(
    etapa["titulo"]
)


# ============================================================
# PLAYER
# ============================================================

tocar_sessao(
    etapa,
    voz,
)


# ============================================================
# CAMPOS
# ============================================================

if etapa_nome.startswith(
    "1"
):

    st.text_area(

        "Pelo que você agradece "
        "a DEUS hoje?",

        key="gratidao",

    )


    st.text_input(

        "Que ação nascerá "
        "desse Amor?",

        key="acao_deus",

    )


elif etapa_nome.startswith(
    "2"
):

    st.text_input(

        "Em quem você deseja "
        "concentrar a prática?",

        key="pessoa",

    )


    st.text_input(

        "Que ação de Amor "
        "você pode realizar?",

        key="acao_proximo",

    )


elif etapa_nome.startswith(
    "3"
):

    st.text_input(

        "Qual é o próximo passo real?",

        key="proximo_passo",

    )
