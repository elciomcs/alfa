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


st.set_page_config(
    page_title="Manual Prático do Amor",
    page_icon="❤️",
    layout="centered",
)

st.title("❤️ Manual Prático do Amor")
st.caption("Sentir → observar → compreender → escolher → agir")


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24 * 7)
def gerar_vozes(textos, voz, rate="-14%", pitch="-2Hz"):
    if edge_tts is None:
        return tuple(b"" for _ in textos)

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
                    dados.extend(chunk.get("data", b""))

            saidas.append(bytes(dados))

        return tuple(saidas)

    loop = asyncio.new_event_loop()

    try:
        return loop.run_until_complete(executar())
    finally:
        loop.close()


def data_uri(dados):
    return (
        "data:audio/mpeg;base64,"
        + base64.b64encode(dados).decode("ascii")
    )


def tocar_sessao(etapa, voz):
    intros = etapa.get("intros")

    if intros:
        intro_chaves = list(intros.keys())
        intro_textos = [intros[chave] for chave in intro_chaves]
    else:
        intro_chaves = ["padrao"]
        intro_textos = [etapa["intro"]]

    textos = intro_textos + [
        texto for _, texto in etapa["prompts"]
    ]

    if edge_tts is None:
        st.error("Instale a dependência edge-tts.")
        return

    with st.spinner("Preparando a voz..."):
        try:
            clips = gerar_vozes(tuple(textos), voz)
        except Exception as exc:
            st.error("Não foi possível gerar a narração.")
            st.caption(type(exc).__name__)
            return

    if not clips or not clips[0]:
        st.error("A narração não foi gerada.")
        return

    intro_clips = clips[:len(intro_textos)]
    prompt_clips = clips[len(intro_textos):]

    intro_sources = {
        chave: data_uri(clip)
        for chave, clip in zip(intro_chaves, intro_clips)
    }

    prompts = [
        {
            "at": float(segundo),
            "src": data_uri(clip),
        }
        for (segundo, _), clip in zip(
            etapa["prompts"],
            prompt_clips,
        )
    ]

    template_path = Path(__file__).with_name("player.html")

    if not template_path.exists():
        st.error("Arquivo player.html não encontrado.")
        return

    template = template_path.read_text(encoding="utf-8")

    musica_src = None
    musica_arquivo = etapa.get("musica_arquivo")

    # Música de espera global.
    # O arquivo alfaeomega.mp3 deve permanecer no mesmo diretório
    # de app.py no repositório do GitHub.
    waiting_music_path = Path(__file__).with_name("alfaeomega.mp3")

    waiting_music_src = (
        data_uri(waiting_music_path.read_bytes())
        if waiting_music_path.exists()
        else None
    )

    if musica_arquivo:
        musica_path = Path(__file__).with_name(musica_arquivo)

        if not musica_path.exists():
            st.error(f"Arquivo de música não encontrado: {musica_arquivo}")
            return

        musica_src = data_uri(musica_path.read_bytes())

    codigo = (
        template
        .replace("__TITLE__", html.escape(etapa["titulo"]))
        .replace(
            "__INTROS__",
            json.dumps(intro_sources, ensure_ascii=False),
        )
        .replace(
            "__PROMPTS__",
            json.dumps(prompts, ensure_ascii=False),
        )
        .replace(
            "__DURATION__",
            str(float(etapa["duracao"])),
        )
        .replace(
            "__MODE__",
            json.dumps(etapa["modo"]),
        )
        .replace(
            "__BACKGROUND_MUSIC__",
            json.dumps(musica_src, ensure_ascii=False),
        )
        .replace(
            "__WAITING_MUSIC__",
            json.dumps(waiting_music_src, ensure_ascii=False),
        )
    )

    components.html(codigo, height=500)


def roteiro_anseio(anseio):
    desejo = (anseio or "").strip()

    foco = (
        f"O seu anseio é: {desejo}. "
        if desejo
        else "Escolha um anseio verdadeiro e significativo. "
    )

    return {
        "titulo": "Anseio e Propósito",
        "modo": "anseio",
        "duracao": 5 * 60,
        "musica_arquivo": "conexao_arcanjo_miguel_item3_96k.mp3",
        "intro": (
            "Encontre uma posição confortável. "
            "Observe a respiração e o coração. "
            + foco
            + "Agora entre nessa realidade pelos seus próprios olhos. "
            "Não se veja de fora. "
            "Observe o ambiente, os sons, sua postura e sua respiração. "
            "Sinta como é viver essa realidade. "
            "Permaneça dentro dessa experiência."
        ),
        "prompts": [
            (
                75,
                "Permaneça dentro da cena. "
                "Observe os detalhes ao seu redor e sinta essa realidade no corpo.",
            ),
            (
                175,
                "Aprofunde essa sensação. "
                "Sinta como você pensa, respira e vive estando nessa realidade.",
            ),
            (
                255,
                "Permaneça nessa realidade. "
                "Sinta o que tem que acontecer hoje.",
            ),
        ],
    }


ETAPAS = {
    "1 · Amor a DEUS": {
        "titulo": "Amor a DEUS",
        "modo": "amor",
        "duracao": 7 * 60,
        "musica_arquivo": "yeshua_item1.mp3",
        "intros": {
            "manha": (
                "Encontre uma posição confortável. "
                "Coloque uma das mãos sobre o coração. "
                "Feche os olhos. "
                "Inspire suavemente e expire devagar. "
                "Agradeça a Deus por ter dado mais um dia em sua vida. "
                "Sinta esta gratidão pelas coisas boas que já aconteceram neste dia, "
                "com Deus ao seu lado. "
                "Converse com Ele agora e expresse esta gratidão."
            ),
            "tarde": (
                "Encontre uma posição confortável. "
                "Coloque uma das mãos sobre o coração. "
                "Feche os olhos. "
                "Inspire suavemente e expire devagar. "
                "Agradeça a Deus por tudo que já aconteceu até este momento do dia "
                "e por quanto Deus é bom. "
                "Sinta a presença Dele o tempo todo ao seu lado. "
                "Converse com Ele agora e expresse esta gratidão."
            ),
            "noite": (
                "Encontre uma posição confortável. "
                "Coloque uma das mãos sobre o coração. "
                "Feche os olhos. "
                "Inspire suavemente e expire devagar. "
                "Agradeça a Deus por mais um dia maravilhoso em sua vida. "
                "Veja os pequenos detalhes que Deus proporcionou em seu dia. "
                "Converse com Ele agora e expresse esta gratidão. "
                "Sinta Ele cuidando de você durante o seu descanso."
            ),
        },
        "prompts": [
            (
                120,
                "Recorde algo concreto pelo qual você agradece profundamente a Deus. "
                "Não fique apenas na ideia. Sinta a gratidão.",
            ),
            (
                270,
                "Se eu viver a partir deste Amor a Deus hoje, "
                "o que muda na maneira como penso?",
            ),
            (
                375,
                "Permaneça nesse Amor. "
                "Sinta como ele quer se expressar em você hoje.",
            ),
        ],
    },

    "2 · Amor ao Próximo": {
        "titulo": "Amor ao Próximo e Empatia",
        "modo": "proximo",
        "duracao": 5 * 60,
        "musica_arquivo": "for_the_one_item2_96k.mp3",
        "intro": (
            "Traga uma pessoa à mente. "
            "Observe o julgamento que aparece primeiro. "
            "Reconheça que essa pessoa possui uma história, "
            "medos, desejos e necessidades. "
            "Deseje sinceramente o bem dela. "
            "Permita que a empatia seja uma ponte para o Amor."
        ),
        "prompts": [
            (
                75,
                "O que você realmente sabe sobre o que essa pessoa está vivendo? "
                "Separe fatos de suposições.",
            ),
            (
                175,
                "O que ela pode estar sentindo ou precisando?",
            ),
            (
                255,
                "Permaneça no Amor. "
                "Sinta como esse Amor pode chegar até essa pessoa hoje.",
            ),
        ],
    },

    "4 · Integração Noturna": {
        "titulo": "Integração Noturna",
        "modo": "noturno",
        "duracao": 60 * 60,
        "intro": (
            "Esta é a última etapa. "
            "Você não precisa usar fones de ouvido nesta etapa. "
            "Pode deixar o volume baixo para dormir. "
            "Relaxe a testa, os olhos, a mandíbula e os ombros. "
            "Respire devagar. "
            "Recorde algo bom deste dia e agradeça. "
            "Se algum pensamento aparecer, observe sem precisar segui-lo. "
            "Agora apenas descanse."
        ),
        "prompts": [],
    },
}


with st.sidebar:
    voz_nome = st.radio(
        "Voz",
        ["Feminina", "Masculina"],
        horizontal=True,
    )

voz = (
    "pt-BR-FranciscaNeural"
    if voz_nome == "Feminina"
    else "pt-BR-AntonioNeural"
)

etapa_nome = st.radio(
    "Etapa",
    [
        "1 · Amor a DEUS",
        "2 · Amor ao Próximo",
        "3 · Anseio e Propósito",
        "4 · Integração Noturna",
    ],
)

if etapa_nome.startswith("3"):
    anseio = st.text_area(
        "Qual é o seu anseio?",
        key="anseio",
    )
    etapa = roteiro_anseio(anseio)
else:
    etapa = ETAPAS[etapa_nome]

st.subheader(etapa["titulo"])

tocar_sessao(etapa, voz)


if etapa_nome.startswith("1"):
    st.text_area(
        "Pelo que você agradece a DEUS hoje?",
        key="gratidao",
    )

    st.text_input(
        "Que ação nascerá desse Amor?",
        key="acao_deus",
    )


elif etapa_nome.startswith("2"):
    st.text_input(
        "Em quem você deseja concentrar a prática?",
        key="pessoa",
    )

    st.text_input(
        "Que ação de Amor você pode realizar?",
        key="acao_proximo",
    )


elif etapa_nome.startswith("3"):
    st.text_input(
        "O que você sente que tem que acontecer hoje?",
        key="proximo_passo",
    )
