import os
import base64
import tempfile
import wave
from pathlib import Path

import numpy as np
import requests
import streamlit as st


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Experiência Sonora",
    page_icon="🎧",
    layout="centered",
)


# ============================================================
# CONFIGURAÇÃO DO GITHUB
# ============================================================

GITHUB_OWNER = "elciomcs"
GITHUB_REPO = "alfa"
GITHUB_BRANCH = "main"

NOME_ARQUIVO = "parceria_ceitec_ecomcs.wav"
CAMINHO_GITHUB = f"audio/{NOME_ARQUIVO}"

GITHUB_API = (
    f"https://api.github.com/repos/"
    f"{GITHUB_OWNER}/{GITHUB_REPO}"
)

API_VERSION = "2026-03-10"


# ============================================================
# CAMINHOS LOCAIS
# ============================================================

PASTA_APP = Path(__file__).resolve().parent

# Depois que o GitHub fizer redeploy,
# o arquivo estará fisicamente aqui:
ARQUIVO_NO_REPO = (
    PASTA_APP
    / "audio"
    / NOME_ARQUIVO
)

# Na primeira geração usamos /tmp
ARQUIVO_TEMP = (
    Path(tempfile.gettempdir())
    / NOME_ARQUIVO
)


# ============================================================
# CONFIGURAÇÃO DO ÁUDIO
# ============================================================

# 8 kHz é suficiente porque a maior frequência
# utilizada é aproximadamente:
#
# 288 Hz + 40 Hz = 328 Hz
#
# Nyquist em 8 kHz = 4.000 Hz.
#
# Resultado aproximado:
# 15 min estéreo PCM16 = 28,8 MB.

TAXA_AMOSTRAGEM = 8000

# Processa 5 segundos por bloco
CHUNK_SEGUNDOS = 5

GANHO = 0.70


# ============================================================
# FASES DO SINAL
# ============================================================

FASES = [

    # --------------------------------------------------------
    # FASE 1
    # 2 minutos
    #
    # Portadora: 288 Hz
    # Diferença: 15 Hz -> 11 Hz
    # --------------------------------------------------------
    {
        "tempo": 120,
        "base_inicio": 288,
        "base_fim": 288,
        "alvo_inicio": 15,
        "alvo_fim": 11,
    },

    # --------------------------------------------------------
    # FASE 2
    # 3 minutos
    #
    # Portadora: 288 Hz
    # Diferença: 11 Hz -> 7 Hz
    # --------------------------------------------------------
    {
        "tempo": 180,
        "base_inicio": 288,
        "base_fim": 288,
        "alvo_inicio": 11,
        "alvo_fim": 7,
    },

    # --------------------------------------------------------
    # FASE 3
    # 5 minutos
    #
    # Portadora: 288 Hz
    # Diferença: 7 Hz -> 2 Hz
    # --------------------------------------------------------
    {
        "tempo": 300,
        "base_inicio": 288,
        "base_fim": 288,
        "alvo_inicio": 7,
        "alvo_fim": 2,
    },

    # --------------------------------------------------------
    # FASE 4
    # 5 minutos
    #
    # Portadora: 288 Hz
    # Diferença: 2 Hz -> 40 Hz
    # --------------------------------------------------------
    {
        "tempo": 300,
        "base_inicio": 288,
        "base_fim": 288,
        "alvo_inicio": 2,
        "alvo_fim": 40,
    },
]


# ============================================================
# TOKEN GITHUB
# ============================================================

def obter_token():

    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return os.environ.get(
            "GITHUB_TOKEN",
            ""
        )


# ============================================================
# HEADERS GITHUB
# ============================================================

def github_headers(
    token="",
    accept="application/vnd.github+json",
):

    headers = {
        "Accept": accept,
        "X-GitHub-Api-Version": API_VERSION,
    }

    if token:
        headers["Authorization"] = (
            f"Bearer {token}"
        )

    return headers


# ============================================================
# FAZ REQUISIÇÃO AO GITHUB
# ============================================================

def github_request(
    method,
    endpoint,
    token="",
    timeout=60,
    **kwargs,
):

    url = f"{GITHUB_API}{endpoint}"

    resposta = requests.request(
        method,
        url,
        headers=github_headers(token),
        timeout=timeout,
        **kwargs,
    )

    return resposta


# ============================================================
# VERIFICA SE ARQUIVO EXISTE NO GITHUB
# ============================================================

def arquivo_existe_no_github(token=""):

    endpoint = (
        f"/contents/{CAMINHO_GITHUB}"
        f"?ref={GITHUB_BRANCH}"
    )

    resposta = github_request(
        "GET",
        endpoint,
        token=token,
        timeout=30,
    )

    if resposta.status_code == 200:
        return True

    if resposta.status_code == 404:
        return False

    raise RuntimeError(
        "Erro verificando o áudio no GitHub.\n\n"
        f"HTTP {resposta.status_code}\n"
        f"{resposta.text}"
    )


# ============================================================
# BAIXA ARQUIVO DO GITHUB
# ============================================================

def baixar_audio_github(
    destino,
    token="",
):

    endpoint = (
        f"/contents/{CAMINHO_GITHUB}"
        f"?ref={GITHUB_BRANCH}"
    )

    url = f"{GITHUB_API}{endpoint}"

    resposta = requests.get(
        url,
        headers=github_headers(
            token,
            "application/vnd.github.raw+json",
        ),
        stream=True,
        timeout=(30, 300),
    )

    if resposta.status_code == 404:
        return False

    if resposta.status_code != 200:

        raise RuntimeError(
            "Erro baixando áudio do GitHub.\n\n"
            f"HTTP {resposta.status_code}\n"
            f"{resposta.text}"
        )

    destino = Path(destino)

    arquivo_parcial = Path(
        str(destino) + ".part"
    )

    with open(
        arquivo_parcial,
        "wb",
    ) as arquivo:

        for bloco in resposta.iter_content(
            chunk_size=1024 * 1024
        ):

            if bloco:
                arquivo.write(bloco)

    os.replace(
        arquivo_parcial,
        destino,
    )

    return True


# ============================================================
# GERA UM BLOCO DO SINAL
# ============================================================

def gerar_bloco(
    fase,
    indice_fase,
    inicio,
    quantidade,
):

    total_amostras = int(
        TAXA_AMOSTRAGEM
        * fase["tempo"]
    )

    # Índices globais dentro desta fase
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


    # --------------------------------------------------------
    # Equivalente ao np.linspace()
    # --------------------------------------------------------

    if total_amostras > 1:

        passo_base = (
            base_fim
            - base_inicio
        ) / (
            total_amostras - 1
        )

        passo_alvo = (
            alvo_fim
            - alvo_inicio
        ) / (
            total_amostras - 1
        )

    else:

        passo_base = 0.0
        passo_alvo = 0.0


    # --------------------------------------------------------
    # CANAL ESQUERDO
    #
    # Equivalente a:
    #
    # freq_base = np.linspace(...)
    # fase_esq =
    # 2*pi*cumsum(freq_base)/taxa
    #
    # Sem criar milhões de amostras simultaneamente.
    # --------------------------------------------------------

    soma_base = (
        (indices + 1)
        * base_inicio

        + passo_base
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


    # --------------------------------------------------------
    # CANAL DIREITO
    #
    # freq = base + alvo
    # --------------------------------------------------------

    direita_inicio = (
        base_inicio
        + alvo_inicio
    )

    passo_direita = (
        passo_base
        + passo_alvo
    )

    soma_direita = (
        (indices + 1)
        * direita_inicio

        + passo_direita
        * indices
        * (indices + 1)
        / 2
    )

    fase_direita = (
        2
        * np.pi
        * soma_direita
        / TAXA_AMOSTRAGEM
    )


    # --------------------------------------------------------
    # ONDAS SENOIDAIS
    # --------------------------------------------------------

    esquerda = np.sin(
        fase_esquerda
    )

    direita = np.sin(
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


    # --------------------------------------------------------
    # Fade-in
    # --------------------------------------------------------

    if indice_fase > 0:

        mascara = (
            indices < fade_t
        )

        if np.any(mascara):

            envelope[mascara] = (
                indices[mascara]
                / (fade_t - 1)
            )


    # --------------------------------------------------------
    # Fade-out
    # --------------------------------------------------------

    if indice_fase < len(FASES) - 1:

        inicio_fade = (
            total_amostras
            - fade_t
        )

        mascara = (
            indices >= inicio_fade
        )

        if np.any(mascara):

            envelope[mascara] = (
                total_amostras
                - 1
                - indices[mascara]
            ) / (
                fade_t - 1
            )


    esquerda *= envelope
    direita *= envelope

    return esquerda, direita


# ============================================================
# GERA O WAV COMPLETO
# ============================================================

def gerar_sinal_parceria_industrial(
    destino,
):

    destino = Path(destino)

    arquivo_parcial = Path(
        str(destino) + ".gerando"
    )

    if arquivo_parcial.exists():

        try:
            arquivo_parcial.unlink()
        except OSError:
            pass


    tamanho_chunk = int(
        TAXA_AMOSTRAGEM
        * CHUNK_SEGUNDOS
    )


    # ========================================================
    # PRIMEIRA PASSAGEM
    #
    # Descobre o maior pico de cada canal.
    #
    # Isso preserva a normalização do código original:
    #
    # sinal / max(abs(sinal)) * 0.7
    # ========================================================

    max_esquerda = 0.0
    max_direita = 0.0


    progresso = st.progress(
        0,
        text="Analisando o sinal..."
    )


    duracao_total = sum(
        fase["tempo"]
        for fase in FASES
    )

    segundos_processados = 0


    for indice_fase, fase in enumerate(FASES):

        total_amostras = int(
            TAXA_AMOSTRAGEM
            * fase["tempo"]
        )

        inicio = 0

        while inicio < total_amostras:

            quantidade = min(
                tamanho_chunk,
                total_amostras - inicio,
            )

            esquerda, direita = gerar_bloco(
                fase,
                indice_fase,
                inicio,
                quantidade,
            )

            pico_esq = float(
                np.max(
                    np.abs(esquerda)
                )
            )

            pico_dir = float(
                np.max(
                    np.abs(direita)
                )
            )

            if pico_esq > max_esquerda:
                max_esquerda = pico_esq

            if pico_dir > max_direita:
                max_direita = pico_dir

            inicio += quantidade

            segundos_processados += (
                quantidade
                / TAXA_AMOSTRAGEM
            )

            valor = int(
                (
                    segundos_processados
                    / (
                        duracao_total * 2
                    )
                )
                * 100
            )

            progresso.progress(
                min(valor, 50),
                text=(
                    "Analisando o sinal..."
                ),
            )


    # Trava contra divisão por zero
    max_esquerda += 1e-10
    max_direita += 1e-10


    # ========================================================
    # SEGUNDA PASSAGEM
    #
    # Gera e grava WAV no disco.
    # ========================================================

    segundos_gravados = 0


    with wave.open(
        str(arquivo_parcial),
        "wb",
    ) as wav:

        # Estéreo
        wav.setnchannels(2)

        # 16 bits = 2 bytes
        wav.setsampwidth(2)

        wav.setframerate(
            TAXA_AMOSTRAGEM
        )


        for indice_fase, fase in enumerate(FASES):

            total_amostras = int(
                TAXA_AMOSTRAGEM
                * fase["tempo"]
            )

            inicio = 0

            while inicio < total_amostras:

                quantidade = min(
                    tamanho_chunk,
                    total_amostras - inicio,
                )

                esquerda, direita = gerar_bloco(
                    fase,
                    indice_fase,
                    inicio,
                    quantidade,
                )


                # --------------------------------------------
                # Mesmo ganho do código original
                # --------------------------------------------

                esquerda = (
                    esquerda
                    / max_esquerda
                ) * GANHO

                direita = (
                    direita
                    / max_direita
                ) * GANHO


                # --------------------------------------------
                # Estéreo
                # --------------------------------------------

                audio_estereo = (
                    np.column_stack(
                        (
                            esquerda,
                            direita,
                        )
                    )
                )


                # --------------------------------------------
                # PCM 16 bits
                # --------------------------------------------

                audio_16bit = np.clip(
                    audio_estereo
                    * 32767,
                    -32768,
                    32767,
                ).astype("<i2")


                # --------------------------------------------
                # Grava imediatamente
                # --------------------------------------------

                wav.writeframes(
                    audio_16bit.tobytes()
                )

                inicio += quantidade

                segundos_gravados += (
                    quantidade
                    / TAXA_AMOSTRAGEM
                )


                percentual_segunda = (
                    segundos_gravados
                    / duracao_total
                )

                valor = int(
                    50
                    + (
                        percentual_segunda
                        * 50
                    )
                )

                progresso.progress(
                    min(valor, 100),
                    text=(
                        "Gerando o áudio..."
                    ),
                )


    progresso.progress(
        100,
        text="Áudio gerado."
    )

    progresso.empty()


    # Só publica o arquivo completo
    os.replace(
        arquivo_parcial,
        destino,
    )

    return destino


# ============================================================
# GITHUB - OBTÉM HEAD DA BRANCH
# ============================================================

def github_obter_head(token):

    resposta = github_request(
        "GET",
        (
            f"/git/ref/heads/"
            f"{GITHUB_BRANCH}"
        ),
        token=token,
        timeout=30,
    )

    if resposta.status_code != 200:

        raise RuntimeError(
            "Não foi possível obter a branch "
            f"{GITHUB_BRANCH}.\n\n"
            f"HTTP {resposta.status_code}\n"
            f"{resposta.text}"
        )

    return resposta.json()[
        "object"
    ]["sha"]


# ============================================================
# GITHUB - OBTÉM COMMIT
# ============================================================

def github_obter_commit(
    token,
    commit_sha,
):

    resposta = github_request(
        "GET",
        f"/git/commits/{commit_sha}",
        token=token,
        timeout=30,
    )

    if resposta.status_code != 200:

        raise RuntimeError(
            "Não foi possível consultar "
            "o commit atual.\n\n"
            f"HTTP {resposta.status_code}\n"
            f"{resposta.text}"
        )

    return resposta.json()


# ============================================================
# GITHUB - CRIA BLOB DO WAV
# ============================================================

def github_criar_blob(
    token,
    arquivo,
):

    status = st.empty()

    status.info(
        "Enviando o áudio para o GitHub..."
    )


    with open(
        arquivo,
        "rb",
    ) as f:

        dados = f.read()


    conteudo_base64 = (
        base64.b64encode(
            dados
        ).decode("ascii")
    )

    del dados


    resposta = github_request(
        "POST",
        "/git/blobs",
        token=token,
        timeout=600,
        json={
            "content": conteudo_base64,
            "encoding": "base64",
        },
    )

    del conteudo_base64


    if resposta.status_code != 201:

        raise RuntimeError(
            "O GitHub não aceitou o arquivo "
            "de áudio.\n\n"
            f"HTTP {resposta.status_code}\n"
            f"{resposta.text}"
        )


    status.empty()

    return resposta.json()["sha"]


# ============================================================
# GITHUB - CRIA TREE
# ============================================================

def github_criar_tree(
    token,
    tree_base,
    blob_sha,
):

    resposta = github_request(
        "POST",
        "/git/trees",
        token=token,
        timeout=60,
        json={
            "base_tree": tree_base,

            "tree": [
                {
                    "path": CAMINHO_GITHUB,
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha,
                }
            ],
        },
    )

    if resposta.status_code != 201:

        raise RuntimeError(
            "Erro criando a árvore Git.\n\n"
            f"HTTP {resposta.status_code}\n"
            f"{resposta.text}"
        )

    return resposta.json()["sha"]


# ============================================================
# GITHUB - CRIA COMMIT
# ============================================================

def github_criar_commit(
    token,
    tree_sha,
    parent_sha,
):

    resposta = github_request(
        "POST",
        "/git/commits",
        token=token,
        timeout=60,
        json={
            "message": (
                "Adiciona áudio binaural "
                "pré-processado"
            ),

            "tree": tree_sha,

            "parents": [
                parent_sha
            ],
        },
    )

    if resposta.status_code != 201:

        raise RuntimeError(
            "Erro criando commit.\n\n"
            f"HTTP {resposta.status_code}\n"
            f"{resposta.text}"
        )

    return resposta.json()["sha"]


# ============================================================
# GITHUB - ATUALIZA BRANCH
# ============================================================

def github_atualizar_branch(
    token,
    commit_sha,
):

    resposta = github_request(
        "PATCH",
        (
            f"/git/refs/heads/"
            f"{GITHUB_BRANCH}"
        ),
        token=token,
        timeout=60,
        json={
            "sha": commit_sha,
            "force": False,
        },
    )

    return resposta


# ============================================================
# PUBLICA WAV DIRETAMENTE NO REPOSITÓRIO
# ============================================================

def publicar_audio_no_github(
    arquivo,
    token,
):

    if not token:

        raise RuntimeError(
            "GITHUB_TOKEN não configurado. "
            "O áudio foi gerado, mas não pode "
            "ser salvo no repositório."
        )


    # --------------------------------------------------------
    # Cria o blob uma única vez
    # --------------------------------------------------------

    blob_sha = github_criar_blob(
        token,
        arquivo,
    )


    # --------------------------------------------------------
    # Duas tentativas caso a branch mude
    # simultaneamente
    # --------------------------------------------------------

    for tentativa in range(2):

        head_sha = github_obter_head(
            token
        )

        commit_atual = (
            github_obter_commit(
                token,
                head_sha,
            )
        )

        tree_base = (
            commit_atual["tree"]["sha"]
        )

        nova_tree = github_criar_tree(
            token,
            tree_base,
            blob_sha,
        )

        novo_commit = (
            github_criar_commit(
                token,
                nova_tree,
                head_sha,
            )
        )

        resposta = (
            github_atualizar_branch(
                token,
                novo_commit,
            )
        )


        if resposta.status_code == 200:

            return True


        # Branch mudou.
        # Tenta novamente usando o HEAD mais novo.
        if resposta.status_code in (
            409,
            422,
        ):

            continue


        raise RuntimeError(
            "Erro atualizando a branch "
            f"{GITHUB_BRANCH}.\n\n"
            f"HTTP {resposta.status_code}\n"
            f"{resposta.text}"
        )


    # Talvez outra instância já tenha publicado
    if arquivo_existe_no_github(
        token
    ):

        return True


    raise RuntimeError(
        "Não foi possível atualizar "
        "a branch do GitHub após duas tentativas."
    )


# ============================================================
# PREPARAÇÃO DO ÁUDIO
# ============================================================

def preparar_audio():

    token = obter_token()


    # ========================================================
    # 1. ARQUIVO JÁ VEIO JUNTO NO CLONE DO GITHUB
    #
    # Este será o caso normal depois do primeiro deploy.
    # ========================================================

    if ARQUIVO_NO_REPO.exists():

        return (
            ARQUIVO_NO_REPO,
            "repositorio",
        )


    # ========================================================
    # 2. TALVEZ JÁ ESTEJA NO GITHUB,
    # MAS ESTA INSTÂNCIA AINDA NÃO TENHA O ARQUIVO.
    # ========================================================

    try:

        if baixar_audio_github(
            ARQUIVO_TEMP,
            token,
        ):

            return (
                ARQUIVO_TEMP,
                "github",
            )

    except Exception:

        # Se houver token, erro real deve aparecer.
        if token:
            raise


    # ========================================================
    # 3. NÃO EXISTE.
    #
    # PRECISAMOS DO TOKEN PARA GERAR E PUBLICAR.
    # ========================================================

    if not token:

        raise RuntimeError(
            "O arquivo ainda não existe no GitHub "
            "e o GITHUB_TOKEN não foi configurado "
            "nos Secrets do Streamlit."
        )


    # ========================================================
    # 4. VERIFICA NOVAMENTE AUTENTICADO
    # ========================================================

    if arquivo_existe_no_github(
        token
    ):

        baixar_audio_github(
            ARQUIVO_TEMP,
            token,
        )

        return (
            ARQUIVO_TEMP,
            "github",
        )


    # ========================================================
    # 5. PRIMEIRA EXECUÇÃO:
    #
    # GERA O WAV
    # ========================================================

    st.info(
        "Primeira execução: gerando o áudio "
        "de 15 minutos. Isso ocorrerá apenas "
        "uma vez."
    )

    gerar_sinal_parceria_industrial(
        ARQUIVO_TEMP
    )


    # ========================================================
    # 6. PUBLICA NO REPOSITÓRIO
    # ========================================================

    st.info(
        "Áudio gerado. Salvando em "
        f"`{CAMINHO_GITHUB}`..."
    )

    publicar_audio_no_github(
        ARQUIVO_TEMP,
        token,
    )


    return (
        ARQUIVO_TEMP,
        "gerado",
    )


# ============================================================
# INTERFACE
# ============================================================

st.title(
    "🎧 Experiência Sonora"
)

st.caption(
    "Sessão estéreo de 15 minutos"
)


# ============================================================
# PREPARA ÁUDIO ANTES DO BOTÃO
# ============================================================

if "arquivo_audio" not in st.session_state:

    try:

        with st.spinner(
            "Preparando o áudio..."
        ):

            caminho_audio, origem = (
                preparar_audio()
            )

        st.session_state[
            "arquivo_audio"
        ] = str(caminho_audio)

        st.session_state[
            "origem_audio"
        ] = origem


        if origem == "gerado":

            st.success(
                "Áudio gerado e salvo em "
                "`audio/parceria_ceitec_ecomcs.wav` "
                "no GitHub."
            )

            st.info(
                "Como a branch main foi atualizada, "
                "o Streamlit pode reiniciar uma vez. "
                "Depois disso o áudio já estará "
                "permanentemente no repositório."
            )


    except Exception as erro:

        st.error(
            "Não foi possível preparar o áudio."
        )

        st.exception(
            erro
        )

        st.stop()


arquivo_audio = (
    st.session_state[
        "arquivo_audio"
    ]
)


# ============================================================
# CONFERE ARQUIVO
# ============================================================

if not Path(
    arquivo_audio
).exists():

    st.error(
        "O arquivo de áudio não foi encontrado."
    )

    st.stop()


# ============================================================
# BOTÃO + INSTRUÇÃO
# ============================================================

st.write("")

col_botao, col_texto = st.columns(
    [1, 2],
    vertical_alignment="center",
)


with col_botao:

    escutar = st.button(
        "🎧 ESCUTAR",
        type="primary",
        use_container_width=True,
    )


with col_texto:

    st.markdown(
        "**🎧 Coloque os fones de ouvido.**  \n"
        "Escute por **15 minutos**."
    )


# ============================================================
# PLAYER
# ============================================================

if escutar:

    st.write("")

    st.success(
        "Sessão iniciada."
    )

    st.audio(
        arquivo_audio,
        format="audio/wav",
        autoplay=True,
        loop=False,
        alt=(
            "Áudio estéreo binaural "
            "com duração de quinze minutos."
        ),
    )

    st.caption(
        "Mantenha o volume em um nível confortável."
    )
