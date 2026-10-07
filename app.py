import base64
import os
import tempfile
import wave
from pathlib import Path

import numpy as np
import requests
import streamlit as st

# ============================================================
# PÁGINA
# ============================================================

st.set_page_config(
    page_title="Experiência Sonora Alfa + Theta",
    page_icon="🎧",
    layout="centered",
)

# ============================================================
# GITHUB
# ============================================================

GITHUB_OWNER = "elciomcs"
GITHUB_REPO = "alfa"
GITHUB_BRANCH = "main"

NOME_ARQUIVO = "parceria_ceitec_ecomcs.wav"
CAMINHO_GITHUB = f"audio/{NOME_ARQUIVO}"

GITHUB_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
GITHUB_API_VERSION = "2026-03-10"

# ============================================================
# ARQUIVOS LOCAIS
# ============================================================

PASTA_APP = Path(__file__).resolve().parent
ARQUIVO_REPO_LOCAL = PASTA_APP / "audio" / NOME_ARQUIVO
ARQUIVO_TEMP = Path(tempfile.gettempdir()) / NOME_ARQUIVO

# ============================================================
# ÁUDIO
# ============================================================

# 8 kHz é suficiente para uma portadora de 288 Hz e canal direito
# chegando a aproximadamente 298 Hz. O WAV final fica ~28,8 MB.
TAXA_AMOSTRAGEM = 8000
CHUNK_SEGUNDOS = 5

PORTADORA_HZ = 288.0

# Ganho digital moderado. O volume real depende do dispositivo/fone.
GANHO = 0.35

# Modulação rítmica suave nos dois canais.
# 0.35 = variação de amplitude moderada, sem zerar o som.
PROFUNDIDADE_MODULACAO = 0.35

# Fade somente no início e no final.
FADE_SEGUNDOS = 5

# ============================================================
# PROTOCOLO ALFA + THETA — 15 MINUTOS
# ============================================================
#
# 0:00–7:00   = 10 Hz estável (alfa)
# 7:00–8:00   = transição 10 -> 6 Hz
# 8:00–15:00  = 6 Hz estável (theta)
#
# Assim, 14 dos 15 minutos ficam em frequências-alvo estáveis.
# A transição inteira permanece entre 6 e 10 Hz.
#
# O canal esquerdo mantém a portadora em 288 Hz.
# O canal direito recebe 288 Hz + frequência-alvo instantânea.
#
# Além da diferença binaural, a mesma frequência-alvo modula
# suavemente a amplitude dos dois canais.

FASES = [
    {
        "nome": "Alfa",
        "tempo": 420,
        "alvo_inicio": 10.0,
        "alvo_fim": 10.0,
    },
    {
        "nome": "Transição Alfa → Theta",
        "tempo": 60,
        "alvo_inicio": 10.0,
        "alvo_fim": 6.0,
    },
    {
        "nome": "Theta",
        "tempo": 420,
        "alvo_inicio": 6.0,
        "alvo_fim": 6.0,
    },
]

DURACAO_TOTAL = sum(fase["tempo"] for fase in FASES)
TOTAL_AMOSTRAS = DURACAO_TOTAL * TAXA_AMOSTRAGEM

# ============================================================
# GITHUB — UTILITÁRIOS
# ============================================================


def obter_token():
    """Lê o token dos Secrets do Streamlit ou da variável de ambiente."""
    try:
        return st.secrets["GITHUB_TOKEN"]
    except Exception:
        return os.environ.get("GITHUB_TOKEN", "")



def github_headers(token="", accept="application/vnd.github+json"):
    headers = {
        "Accept": accept,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers



def github_request(method, endpoint, token="", timeout=60, **kwargs):
    return requests.request(
        method,
        f"{GITHUB_API}{endpoint}",
        headers=github_headers(token),
        timeout=timeout,
        **kwargs,
    )



def audio_existe_no_github(token=""):
    resposta = github_request(
        "GET",
        f"/contents/{CAMINHO_GITHUB}?ref={GITHUB_BRANCH}",
        token=token,
        timeout=30,
    )

    if resposta.status_code == 200:
        return True

    if resposta.status_code == 404:
        return False

    raise RuntimeError(
        "Falha ao verificar o arquivo no GitHub.\n"
        f"HTTP {resposta.status_code}: {resposta.text}"
    )



def baixar_audio_do_github(destino, token=""):
    """Baixa o WAV já existente usando a representação raw da API."""
    url = f"{GITHUB_API}/contents/{CAMINHO_GITHUB}?ref={GITHUB_BRANCH}"

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
            "Falha ao baixar o áudio do GitHub.\n"
            f"HTTP {resposta.status_code}: {resposta.text}"
        )

    destino = Path(destino)
    parcial = Path(str(destino) + ".part")

    with open(parcial, "wb") as arquivo:
        for bloco in resposta.iter_content(chunk_size=1024 * 1024):
            if bloco:
                arquivo.write(bloco)

    os.replace(parcial, destino)
    return True


# ============================================================
# ÁUDIO — MATEMÁTICA
# ============================================================


def segundos_antes_da_fase(indice_fase):
    return sum(FASES[i]["tempo"] for i in range(indice_fase))



def ciclos_alvo_antes_da_fase(indice_fase):
    """
    Retorna o total de ciclos da frequência-alvo acumulados antes
    da fase atual. Isso mantém a fase contínua nas transições.
    """
    ciclos = 0.0

    for i in range(indice_fase):
        fase = FASES[i]
        duracao = float(fase["tempo"])
        f0 = float(fase["alvo_inicio"])
        f1 = float(fase["alvo_fim"])

        # Integral de uma rampa linear = frequência média × duração.
        ciclos += ((f0 + f1) / 2.0) * duracao

    return ciclos



def gerar_bloco(fase, indice_fase, inicio_amostra, quantidade):
    """Gera um pequeno bloco estéreo, mantendo fase contínua."""

    indices_locais = (
        inicio_amostra
        + np.arange(quantidade, dtype=np.float64)
    )

    t_local = indices_locais / TAXA_AMOSTRAGEM

    inicio_global_segundos = segundos_antes_da_fase(indice_fase)
    t_global = inicio_global_segundos + t_local

    # --------------------------------------------------------
    # PORTADORA — 288 Hz contínuos
    # --------------------------------------------------------

    fase_portadora = 2.0 * np.pi * PORTADORA_HZ * t_global

    # --------------------------------------------------------
    # FREQUÊNCIA-ALVO INTEGRADA
    # --------------------------------------------------------
    #
    # Para uma frequência linear:
    #
    # f(t) = f0 + k*t
    #
    # a fase depende da integral:
    #
    # ciclos(t) = f0*t + 0.5*k*t²
    #
    # Isso permite variar 10 -> 6 Hz sem criar descontinuidades.

    duracao = float(fase["tempo"])
    alvo_inicio = float(fase["alvo_inicio"])
    alvo_fim = float(fase["alvo_fim"])

    inclinacao = (alvo_fim - alvo_inicio) / duracao

    ciclos_alvo = (
        ciclos_alvo_antes_da_fase(indice_fase)
        + alvo_inicio * t_local
        + 0.5 * inclinacao * (t_local ** 2)
    )

    fase_alvo = 2.0 * np.pi * ciclos_alvo

    # --------------------------------------------------------
    # BINAURAL
    # --------------------------------------------------------
    #
    # Alfa 10 Hz:
    # esquerdo = 288 Hz
    # direito  = 298 Hz
    #
    # Theta 6 Hz:
    # esquerdo = 288 Hz
    # direito  = 294 Hz

    esquerda = np.sin(fase_portadora)
    direita = np.sin(fase_portadora + fase_alvo)

    # --------------------------------------------------------
    # MODULAÇÃO RÍTMICA DE AMPLITUDE
    # --------------------------------------------------------
    #
    # A mesma fase-alvo também modula suavemente o volume dos
    # dois canais. Assim há uma pista rítmica física no áudio
    # além da diferença binaural L/R.

    modulacao = (
        1.0
        - (PROFUNDIDADE_MODULACAO / 2.0)
        + (PROFUNDIDADE_MODULACAO / 2.0) * np.sin(fase_alvo)
    )

    esquerda *= modulacao
    direita *= modulacao

    # --------------------------------------------------------
    # FADE GERAL — início e fim da sessão
    # --------------------------------------------------------

    inicio_global_amostras = int(
        inicio_global_segundos * TAXA_AMOSTRAGEM
    )

    indices_globais = inicio_global_amostras + indices_locais

    fade_amostras = FADE_SEGUNDOS * TAXA_AMOSTRAGEM
    envelope = np.ones(quantidade, dtype=np.float64)

    # Fade-in
    mascara_inicio = indices_globais < fade_amostras

    if np.any(mascara_inicio):
        envelope[mascara_inicio] = (
            indices_globais[mascara_inicio]
            / max(fade_amostras - 1, 1)
        )

    # Fade-out
    inicio_fade_final = TOTAL_AMOSTRAS - fade_amostras
    mascara_final = indices_globais >= inicio_fade_final

    if np.any(mascara_final):
        envelope[mascara_final] = (
            TOTAL_AMOSTRAS
            - 1
            - indices_globais[mascara_final]
        ) / max(fade_amostras - 1, 1)

    envelope = np.clip(envelope, 0.0, 1.0)

    esquerda *= envelope * GANHO
    direita *= envelope * GANHO

    return esquerda, direita



def gerar_audio(destino):
    """
    Gera os 15 minutos em blocos pequenos e grava imediatamente
    no disco, evitando manter o WAV inteiro na RAM.
    """

    destino = Path(destino)
    parcial = Path(str(destino) + ".gerando")

    if parcial.exists():
        parcial.unlink()

    chunk = TAXA_AMOSTRAGEM * CHUNK_SEGUNDOS
    progresso = st.progress(0, text="Gerando áudio alfa/theta...")

    amostras_gravadas = 0

    with wave.open(str(parcial), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)  # PCM 16-bit
        wav.setframerate(TAXA_AMOSTRAGEM)

        for indice_fase, fase in enumerate(FASES):
            total_fase = int(fase["tempo"] * TAXA_AMOSTRAGEM)
            inicio = 0

            while inicio < total_fase:
                quantidade = min(chunk, total_fase - inicio)

                esquerda, direita = gerar_bloco(
                    fase,
                    indice_fase,
                    inicio,
                    quantidade,
                )

                estereo = np.column_stack((esquerda, direita))

                pcm16 = np.clip(
                    estereo * 32767.0,
                    -32768,
                    32767,
                ).astype("<i2")

                wav.writeframes(pcm16.tobytes())

                inicio += quantidade
                amostras_gravadas += quantidade

                percentual = int(
                    100.0 * amostras_gravadas / TOTAL_AMOSTRAS
                )

                progresso.progress(
                    min(percentual, 100),
                    text=f"Gerando áudio... {min(percentual, 100)}%",
                )

    os.replace(parcial, destino)
    progresso.empty()

    return destino


# ============================================================
# GITHUB — PUBLICAÇÃO EM audio/
# ============================================================


def obter_head_da_branch(token):
    resposta = github_request(
        "GET",
        f"/git/ref/heads/{GITHUB_BRANCH}",
        token=token,
        timeout=30,
    )

    if resposta.status_code != 200:
        raise RuntimeError(
            f"Não foi possível obter a branch {GITHUB_BRANCH}.\n"
            f"HTTP {resposta.status_code}: {resposta.text}"
        )

    return resposta.json()["object"]["sha"]



def obter_commit(token, commit_sha):
    resposta = github_request(
        "GET",
        f"/git/commits/{commit_sha}",
        token=token,
        timeout=30,
    )

    if resposta.status_code != 200:
        raise RuntimeError(
            "Não foi possível consultar o commit atual.\n"
            f"HTTP {resposta.status_code}: {resposta.text}"
        )

    return resposta.json()



def criar_blob_do_audio(token, arquivo):
    """Cria o blob Git que será colocado em audio/<arquivo>."""

    tamanho = Path(arquivo).stat().st_size

    if tamanho >= 100 * 1024 * 1024:
        raise RuntimeError(
            "O WAV ficou maior que 100 MiB e não pode ser "
            "gravado como arquivo normal no GitHub."
        )

    with open(arquivo, "rb") as f:
        conteudo_b64 = base64.b64encode(f.read()).decode("ascii")

    resposta = github_request(
        "POST",
        "/git/blobs",
        token=token,
        timeout=900,
        json={
            "content": conteudo_b64,
            "encoding": "base64",
        },
    )

    # Libera a string grande assim que a requisição termina.
    del conteudo_b64

    if resposta.status_code != 201:
        raise RuntimeError(
            "O GitHub não aceitou o arquivo de áudio.\n"
            f"HTTP {resposta.status_code}: {resposta.text}"
        )

    return resposta.json()["sha"]



def criar_tree(token, base_tree_sha, blob_sha):
    resposta = github_request(
        "POST",
        "/git/trees",
        token=token,
        timeout=60,
        json={
            "base_tree": base_tree_sha,
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
            "Falha ao criar a árvore Git.\n"
            f"HTTP {resposta.status_code}: {resposta.text}"
        )

    return resposta.json()["sha"]



def criar_commit(token, tree_sha, parent_sha):
    resposta = github_request(
        "POST",
        "/git/commits",
        token=token,
        timeout=60,
        json={
            "message": "Adiciona áudio alfa/theta pré-processado",
            "tree": tree_sha,
            "parents": [parent_sha],
        },
    )

    if resposta.status_code != 201:
        raise RuntimeError(
            "Falha ao criar o commit do áudio.\n"
            f"HTTP {resposta.status_code}: {resposta.text}"
        )

    return resposta.json()["sha"]



def atualizar_branch(token, commit_sha):
    return github_request(
        "PATCH",
        f"/git/refs/heads/{GITHUB_BRANCH}",
        token=token,
        timeout=60,
        json={
            "sha": commit_sha,
            "force": False,
        },
    )



def publicar_audio_no_github(arquivo, token):
    """
    Faz o equivalente a um commit adicionando:

        audio/parceria_ceitec_ecomcs.wav

    diretamente na branch main.
    """

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN não configurado nos Secrets do Streamlit."
        )

    # O blob de ~28,8 MB é enviado uma única vez.
    blob_sha = criar_blob_do_audio(token, arquivo)

    # Se a branch mudar durante o upload, refaz tree/commit usando
    # o HEAD mais recente sem reenviar o WAV.
    for _ in range(3):
        head_sha = obter_head_da_branch(token)
        commit_atual = obter_commit(token, head_sha)
        base_tree_sha = commit_atual["tree"]["sha"]

        tree_sha = criar_tree(
            token,
            base_tree_sha,
            blob_sha,
        )

        commit_sha = criar_commit(
            token,
            tree_sha,
            head_sha,
        )

        resposta = atualizar_branch(
            token,
            commit_sha,
        )

        if resposta.status_code == 200:
            return True

        if resposta.status_code not in (409, 422):
            raise RuntimeError(
                "Falha ao atualizar a branch main.\n"
                f"HTTP {resposta.status_code}: {resposta.text}"
            )

    # Outra instância pode ter concluído primeiro.
    if audio_existe_no_github(token):
        return True

    raise RuntimeError(
        "Não foi possível atualizar a branch main. "
        "Verifique se há proteção de branch impedindo commits diretos."
    )


# ============================================================
# PREPARAÇÃO AUTOMÁTICA
# ============================================================


def preparar_audio():
    # --------------------------------------------------------
    # 1. Depois do primeiro commit/redeploy, o WAV virá junto
    #    com o próprio clone do repositório.
    # --------------------------------------------------------

    if ARQUIVO_REPO_LOCAL.exists():
        return ARQUIVO_REPO_LOCAL, "repositorio"

    token = obter_token()

    # --------------------------------------------------------
    # 2. Pode existir no GitHub, mas esta instância ainda ser
    #    anterior ao commit. Nesse caso apenas baixa o WAV.
    # --------------------------------------------------------

    try:
        if audio_existe_no_github(token):
            baixar_audio_do_github(
                ARQUIVO_TEMP,
                token,
            )
            return ARQUIVO_TEMP, "github"

    except Exception:
        if token:
            raise

    # --------------------------------------------------------
    # 3. Primeira execução: token obrigatório para publicar.
    # --------------------------------------------------------

    if not token:
        raise RuntimeError(
            "O áudio ainda não existe no repositório e "
            "GITHUB_TOKEN não foi configurado nos Secrets."
        )

    st.info(
        "Primeira execução: o áudio de 15 minutos ainda não existe. "
        "Ele será gerado uma vez e salvo na pasta `audio/` do GitHub."
    )

    # --------------------------------------------------------
    # 4. Gera localmente em /tmp.
    # --------------------------------------------------------

    gerar_audio(ARQUIVO_TEMP)

    # --------------------------------------------------------
    # 5. Evita duplicar commits se outra instância concluiu.
    # --------------------------------------------------------

    if audio_existe_no_github(token):
        return ARQUIVO_TEMP, "gerado_localmente"

    # --------------------------------------------------------
    # 6. Publica na main.
    # --------------------------------------------------------

    st.info(
        "Áudio pronto. Salvando em "
        "`audio/parceria_ceitec_ecomcs.wav` no repositório..."
    )

    publicar_audio_no_github(
        ARQUIVO_TEMP,
        token,
    )

    return ARQUIVO_TEMP, "publicado"


# ============================================================
# INTERFACE
# ============================================================

st.title("🎧 Experiência Sonora Alfa + Theta")

st.write(
    "Sessão estéreo de **15 minutos**, com estímulo auditivo "
    "programado para permanecer entre **10 Hz (alfa)** e "
    "**6 Hz (theta)**."
)

st.caption(
    "Use fones estéreo e mantenha o volume em um nível confortável."
)

with st.expander("Protocolo de frequências"):
    st.markdown(
        """
- **0:00–7:00:** 10 Hz — alfa estável
- **7:00–8:00:** transição gradual de 10 Hz para 6 Hz
- **8:00–15:00:** 6 Hz — theta estável

**Portadora:** 288 Hz  
**Canal esquerdo:** 288 Hz  
**Canal direito:** 288 Hz + frequência-alvo  
**Modulação:** a mesma frequência-alvo modula suavemente a amplitude dos dois canais.
        """
    )

# ============================================================
# PREPARA O ÁUDIO ANTES DE LIBERAR O BOTÃO
# ============================================================

if "arquivo_audio" not in st.session_state:
    try:
        with st.spinner("Preparando o áudio..."):
            caminho, origem = preparar_audio()

        st.session_state["arquivo_audio"] = str(caminho)
        st.session_state["origem_audio"] = origem

        if origem == "publicado":
            st.success(
                "Áudio gerado e enviado para "
                "`audio/parceria_ceitec_ecomcs.wav`."
            )

            st.info(
                "O commit na branch `main` pode provocar um redeploy "
                "único do Streamlit. Depois disso, o WAV já fará parte "
                "do próprio repositório."
            )

    except Exception as erro:
        st.error("Não foi possível preparar o áudio.")
        st.exception(erro)
        st.stop()

arquivo_audio = Path(st.session_state["arquivo_audio"])

if not arquivo_audio.exists():
    st.error("O arquivo de áudio não está disponível nesta instância.")
    st.stop()

# ============================================================
# BOTÃO + INSTRUÇÃO
# ============================================================

st.write("")

col_botao, col_instrucao = st.columns(
    [1, 2],
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
        "**Coloque os fones de ouvido.**  \n"
        "Escute por **15 minutos**."
    )

# ============================================================
# PLAYER
# ============================================================

if escutar:
    st.success("Sessão iniciada.")

    st.audio(
        arquivo_audio,
        format="audio/wav",
        autoplay=True,
        loop=False,
        alt="Sessão sonora estéreo alfa e theta de quinze minutos.",
        width="stretch",
    )

    st.caption(
        "Se sentir desconforto, interrompa a reprodução. "
        "Não use em volume elevado."
    )
