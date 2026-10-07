import os
import tempfile
import wave

import numpy as np
import requests
import streamlit as st


# ============================================================
# CONFIGURAÇÃO STREAMLIT
# ============================================================

st.set_page_config(
    page_title="Experiência Sonora",
    page_icon="🎧",
    layout="centered",
)


# ============================================================
# CONFIGURAÇÃO DO ÁUDIO
# ============================================================

TAXA_AMOSTRAGEM = 44100
CHUNK_SEGUNDOS = 1

NOME_ARQUIVO = "parceria_ceitec_ecomcs.wav"


# Roteiro:
# Estruturação Física do Silício
# -> Alinhamento Comercial
# -> Expansão Global

FASES = [

    # Fase 1
    # Ancoragem Industrial
    # 288 Hz portadora
    # 15 Hz -> 11 Hz
    {
        "tempo": 120,
        "base_inicio": 288,
        "base_fim": 288,
        "alvo_inicio": 15,
        "alvo_fim": 11,
    },

    # Fase 2
    # 11 Hz -> 7 Hz
    {
        "tempo": 180,
        "base_inicio": 288,
        "base_fim": 288,
        "alvo_inicio": 11,
        "alvo_fim": 7,
    },

    # Fase 3
    # 7 Hz -> 2 Hz
    {
        "tempo": 300,
        "base_inicio": 288,
        "base_fim": 288,
        "alvo_inicio": 7,
        "alvo_fim": 2,
    },

    # Fase 4
    # 2 Hz -> 40 Hz
    {
        "tempo": 300,
        "base_inicio": 288,
        "base_fim": 288,
        "alvo_inicio": 2,
        "alvo_fim": 40,
    },
]


# ============================================================
# CONFIGURAÇÃO DO GITHUB
# ============================================================

GITHUB_OWNER = "elciomcs"
GITHUB_REPO = "alfa"

# Usaremos uma Release, não um arquivo da branch.
RELEASE_TAG = "audio-cache-v1"
RELEASE_NAME = "Audio Cache"

API = (
    f"https://api.github.com/repos/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}"
)


try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
except KeyError:
    st.error(
        "GITHUB_TOKEN não encontrado nos Secrets do Streamlit."
    )
    st.stop()


def github_headers(
    accept="application/vnd.github+json"
):
    return {
        "Accept": accept,
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2026-03-10",
    }


# ============================================================
# GERAÇÃO MATEMÁTICA
# ============================================================

def gerar_bloco(
    fase,
    indice_fase,
    inicio,
    quantidade,
):

    """
    Reproduz matematicamente a lógica:

        freq_base = np.linspace(...)
        freq_alvo = np.linspace(...)

        fase_esq =
            2*pi*cumsum(freq_base)/taxa

        fase_dir =
            2*pi*cumsum(freq_base + freq_alvo)/taxa

    mas sem criar a fase inteira na memória.
    """

    total = int(
        TAXA_AMOSTRAGEM
        * fase["tempo"]
    )

    indices = (
        inicio
        + np.arange(
            quantidade,
            dtype=np.float64,
        )
    )

    base_inicio = float(
        fase["base_inicio"]
    )

    base_fim = float(
        fase["base_fim"]
    )

    alvo_inicio = float(
        fase["alvo_inicio"]
    )

    alvo_fim = float(
        fase["alvo_fim"]
    )


    # np.linspace inclui os dois extremos.
    if total > 1:

        passo_base = (
            base_fim - base_inicio
        ) / (total - 1)

        passo_alvo = (
            alvo_fim - alvo_inicio
        ) / (total - 1)

    else:

        passo_base = 0.0
        passo_alvo = 0.0


    # ========================================================
    # SOMA ACUMULADA ANALÍTICA
    #
    # Para:
    #
    # f(j) = a + d*j
    #
    # soma de j=0 até k:
    #
    # (k+1)*a + d*k*(k+1)/2
    #
    # Isso substitui np.cumsum sem carregar tudo na memória.
    # ========================================================

    soma_base = (
        (indices + 1) * base_inicio
        + passo_base
        * indices
        * (indices + 1)
        / 2
    )


    inicio_direita = (
        base_inicio
        + alvo_inicio
    )

    passo_direita = (
        passo_base
        + passo_alvo
    )

    soma_direita = (
        (indices + 1)
        * inicio_direita
        + passo_direita
        * indices
        * (indices + 1)
        / 2
    )


    fase_esquerda = (
        2
        * np.pi
        * soma_base
        / TAXA_AMOSTRAGEM
    )

    fase_direita = (
        2
        * np.pi
        * soma_direita
        / TAXA_AMOSTRAGEM
    )


    onda_esquerda = np.sin(
        fase_esquerda
    )

    onda_direita = np.sin(
        fase_direita
    )


    # ========================================================
    # FADE DE 2 SEGUNDOS
    # ========================================================

    fade_t = int(
        TAXA_AMOSTRAGEM * 2
    )

    envelope = np.ones(
        quantidade,
        dtype=np.float64,
    )


    # Fade-in
    if indice_fase > 0:

        mascara = (
            indices < fade_t
        )

        if fade_t > 1:

            envelope[mascara] = (
                indices[mascara]
                / (fade_t - 1)
            )


    # Fade-out
    if indice_fase < len(FASES) - 1:

        inicio_fade = (
            total - fade_t
        )

        mascara = (
            indices >= inicio_fade
        )

        if fade_t > 1:

            envelope[mascara] = (
                total
                - 1
                - indices[mascara]
            ) / (fade_t - 1)


    onda_esquerda *= envelope
    onda_direita *= envelope


    return (
        onda_esquerda,
        onda_direita,
    )


# ============================================================
# GERA O WAV COMPLETO
# ============================================================

def gerar_sinal_parceria_industrial(
    filename
):

    chunk = (
        TAXA_AMOSTRAGEM
        * CHUNK_SEGUNDOS
    )


    # ========================================================
    # PRIMEIRA PASSAGEM
    #
    # Descobre o pico máximo, preservando sua normalização:
    #
    # sinal / max(abs(sinal)) * 0.7
    # ========================================================

    max_esquerda = 0.0
    max_direita = 0.0


    for indice_fase, fase in enumerate(FASES):

        total = int(
            TAXA_AMOSTRAGEM
            * fase["tempo"]
        )

        inicio = 0

        while inicio < total:

            quantidade = min(
                chunk,
                total - inicio,
            )

            esquerda, direita = gerar_bloco(
                fase,
                indice_fase,
                inicio,
                quantidade,
            )

            max_esquerda = max(
                max_esquerda,
                float(
                    np.max(
                        np.abs(esquerda)
                    )
                ),
            )

            max_direita = max(
                max_direita,
                float(
                    np.max(
                        np.abs(direita)
                    )
                ),
            )

            inicio += quantidade


    # Trava contra divisão por zero
    max_esquerda += 1e-10
    max_direita += 1e-10


    # ========================================================
    # SEGUNDA PASSAGEM
    #
    # Gera e grava diretamente no WAV.
    # Apenas 1 segundo fica em RAM.
    # ========================================================

    with wave.open(
        filename,
        "wb",
    ) as wav:

        # Estéreo
        wav.setnchannels(2)

        # PCM 16 bit
        wav.setsampwidth(2)

        wav.setframerate(
            TAXA_AMOSTRAGEM
        )


        for indice_fase, fase in enumerate(FASES):

            total = int(
                TAXA_AMOSTRAGEM
                * fase["tempo"]
            )

            inicio = 0

            while inicio < total:

                quantidade = min(
                    chunk,
                    total - inicio,
                )


                esquerda, direita = gerar_bloco(
                    fase,
                    indice_fase,
                    inicio,
                    quantidade,
                )


                # Mesma normalização do seu código
                esquerda = (
                    esquerda
                    / max_esquerda
                ) * 0.7

                direita = (
                    direita
                    / max_direita
                ) * 0.7


                # Estéreo L/R
                audio_estereo = np.column_stack(
                    (
                        esquerda,
                        direita,
                    )
                )


                # PCM 16 bits
                audio_16bit = (
                    audio_estereo
                    * 32767
                ).astype("<i2")


                wav.writeframes(
                    audio_16bit.tobytes()
                )


                inicio += quantidade


    return filename


# ============================================================
# GITHUB RELEASE
# ============================================================

def obter_release():

    url = (
        f"{API}/releases/tags/"
        f"{RELEASE_TAG}"
    )

    resposta = requests.get(
        url,
        headers=github_headers(),
        timeout=30,
    )


    if resposta.status_code == 200:
        return resposta.json()


    if resposta.status_code != 404:
        resposta.raise_for_status()


    # Ainda não existe.
    # Cria a Release.
    url = f"{API}/releases"

    resposta = requests.post(
        url,
        headers=github_headers(),
        json={
            "tag_name": RELEASE_TAG,
            "target_commitish": "main",
            "name": RELEASE_NAME,
            "body": (
                "Arquivo de áudio pré-processado "
                "utilizado pelo aplicativo Streamlit."
            ),
            "draft": False,
            "prerelease": True,
            "make_latest": "false",
        },
        timeout=30,
    )


    if resposta.status_code == 201:
        return resposta.json()


    # Pode acontecer se duas instâncias
    # tentarem criar ao mesmo tempo.
    if resposta.status_code == 422:

        resposta = requests.get(
            (
                f"{API}/releases/tags/"
                f"{RELEASE_TAG}"
            ),
            headers=github_headers(),
            timeout=30,
        )

        resposta.raise_for_status()

        return resposta.json()


    resposta.raise_for_status()


# ============================================================
# LOCALIZA O WAV DENTRO DA RELEASE
# ============================================================

def procurar_asset(release):

    for asset in release.get(
        "assets",
        []
    ):

        if asset.get("name") == NOME_ARQUIVO:

            return asset

    return None


# ============================================================
# BAIXA O WAV DO GITHUB
# ============================================================

def baixar_asset(
    asset,
    destino,
):

    resposta = requests.get(
        asset["url"],
        headers=github_headers(
            "application/octet-stream"
        ),
        stream=True,
        timeout=(30, 600),
    )

    resposta.raise_for_status()


    with open(
        destino,
        "wb",
    ) as arquivo:

        for bloco in resposta.iter_content(
            chunk_size=1024 * 1024
        ):

            if bloco:
                arquivo.write(bloco)


    return destino


# ============================================================
# ENVIA WAV PARA A RELEASE
# ============================================================

def enviar_asset(
    release,
    filename,
):

    upload_url = (
        release["upload_url"]
        .split("{")[0]
    )


    headers = github_headers()

    headers["Content-Type"] = (
        "audio/wav"
    )


    tamanho = os.path.getsize(
        filename
    )

    headers["Content-Length"] = str(
        tamanho
    )


    with open(
        filename,
        "rb",
    ) as arquivo:

        resposta = requests.post(
            upload_url,
            headers=headers,
            params={
                "name": NOME_ARQUIVO
            },
            data=arquivo,
            timeout=(30, 1800),
        )


    if resposta.status_code == 201:
        return resposta.json()


    # 422 = outra instância pode
    # ter acabado de enviar o mesmo arquivo.
    if resposta.status_code == 422:

        release = obter_release()

        asset = procurar_asset(
            release
        )

        if asset:
            return asset


    raise RuntimeError(
        "Erro enviando áudio ao GitHub:\n"
        f"{resposta.status_code}\n"
        f"{resposta.text}"
    )


# ============================================================
# PREPARA O ÁUDIO
# ============================================================

@st.cache_resource(
    show_spinner=False
)
def preparar_audio():

    release = obter_release()

    asset = procurar_asset(
        release
    )


    # --------------------------------------------------------
    # JÁ EXISTE NO GITHUB
    # --------------------------------------------------------

    if asset:

        fd, caminho = tempfile.mkstemp(
            suffix=".wav"
        )

        os.close(fd)

        baixar_asset(
            asset,
            caminho,
        )

        return caminho


    # --------------------------------------------------------
    # PRIMEIRA EXECUÇÃO
    #
    # Não existe no GitHub:
    # gera -> envia -> usa arquivo local.
    # --------------------------------------------------------

    fd, caminho = tempfile.mkstemp(
        suffix=".wav"
    )

    os.close(fd)


    gerar_sinal_parceria_industrial(
        caminho
    )


    enviar_asset(
        release,
        caminho,
    )


    return caminho


# ============================================================
# INTERFACE
# ============================================================

st.markdown(
    """
    <div style="
        text-align:center;
        padding-top:25px;
    ">

        <div style="font-size:70px;">
            🎧
        </div>

        <h1>
            Experiência Sonora
        </h1>

        <p style="
            font-size:19px;
            opacity:0.75;
        ">
            Sessão estéreo de 15 minutos
        </p>

    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PREPARAÇÃO AUTOMÁTICA
# ============================================================

try:

    with st.spinner(
        "Preparando o áudio..."
    ):

        arquivo_audio = preparar_audio()


except Exception as erro:

    st.error(
        "Não foi possível preparar o áudio."
    )

    st.exception(
        erro
    )

    st.stop()


# ============================================================
# BOTÃO + INSTRUÇÃO
# ============================================================

col_botao, col_instrucao = st.columns(
    [1.2, 2.3],
    vertical_alignment="center",
)


with col_botao:

    escutar = st.button(
        "🎧 ESCUTAR",
        type="primary",
        use_container_width=True,
    )


with col_instrucao:

    st.markdown(
        """
        <div style="
            font-size:18px;
            line-height:1.5;
        ">

            <b>
                Coloque os fones de ouvido.
            </b>

            <br>

            Escute por
            <b>15 minutos</b>.

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# PLAYER
# ============================================================

if escutar:

    st.write("")

    st.audio(
        arquivo_audio,
        format="audio/wav",
        autoplay=True,
        loop=False,
        alt=(
            "Sinal de áudio estéreo "
            "com duração de quinze minutos."
        ),
    )

    st.caption(
        "🎧 Mantenha o volume em um nível confortável."
    )
