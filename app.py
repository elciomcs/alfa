import base64
import hashlib
import json
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
    page_title="Experiência Sonora",
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
CAMINHO_VERSAO_GITHUB = "audio/protocolo_version.txt"

GITHUB_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
GITHUB_API_VERSION = "2026-03-10"


# ============================================================
# ARQUIVOS LOCAIS
# ============================================================

PASTA_APP = Path(__file__).resolve().parent
ARQUIVO_REPO_LOCAL = PASTA_APP / "audio" / NOME_ARQUIVO
ARQUIVO_VERSAO_REPO_LOCAL = PASTA_APP / "audio" / "protocolo_version.txt"

ARQUIVO_TEMP = Path(tempfile.gettempdir()) / NOME_ARQUIVO


# ============================================================
# ÁUDIO
# ============================================================

# 8 kHz é suficiente para este projeto porque a maior frequência
# acústica utilizada é aproximadamente 288 + 40 = 328 Hz.
# Nyquist em 8 kHz = 4.000 Hz.
#
# WAV final aproximado:
# 900 s x 8.000 amostras/s x 2 canais x 2 bytes = 28,8 MB.

TAXA_AMOSTRAGEM = 8000
CHUNK_SEGUNDOS = 5

PORTADORA_HZ = 288.0
GANHO = 0.35
PROFUNDIDADE_MODULACAO = 0.35
FADE_SEGUNDOS = 5

# Se futuramente a fórmula matemática for alterada sem mudar as
# frequências/configurações abaixo, incremente esta string.
ALGORITMO_VERSAO = "binaural-am-v3-alpha-theta-gamma"


# ============================================================
# PROTOCOLO — 15 MINUTOS
# ============================================================
#
# 0:00–5:00   = 10 Hz (Alfa)
# 5:00–11:00  = 4,5 Hz (Theta)
# 11:00–12:00 = transição 4,5 -> 40 Hz
# 12:00–15:00 = 40 Hz (Gamma)
#
# Em todos os momentos:
# canal esquerdo = portadora de 288 Hz
# canal direito  = 288 Hz + frequência-alvo instantânea
#
# A mesma frequência-alvo também modula suavemente a amplitude
# dos dois canais.

FASES = [
    {
        "nome": "Alfa",
        "tempo": 300,
        "alvo_inicio": 10.0,
        "alvo_fim": 10.0,
    },
    {
        "nome": "Theta",
        "tempo": 360,
        "alvo_inicio": 4.5,
        "alvo_fim": 4.5,
    },
    {
        "nome": "Transição Theta → Gamma",
        "tempo": 60,
        "alvo_inicio": 4.5,
        "alvo_fim": 40.0,
    },
    {
        "nome": "Gamma",
        "tempo": 180,
        "alvo_inicio": 40.0,
        "alvo_fim": 40.0,
    },
]

DURACAO_TOTAL = sum(fase["tempo"] for fase in FASES)
TOTAL_AMOSTRAS = DURACAO_TOTAL * TAXA_AMOSTRAGEM

if DURACAO_TOTAL != 900:
    raise RuntimeError("O protocolo precisa totalizar exatamente 900 segundos.")


# ============================================================
# IDENTIDADE AUTOMÁTICA DO PROTOCOLO
# ============================================================
#
# Quando qualquer parâmetro relevante muda, este hash muda.
# Na primeira abertura após você publicar um app.py novo, o app
# detecta que o WAV existente é de outra versão, gera novamente e
# sobrescreve O MESMO arquivo no GitHub.
#
# Portanto, continua existindo um único WAV:
# audio/parceria_ceitec_ecomcs.wav

PROTOCOLO_CONFIG = {
    "algoritmo": ALGORITMO_VERSAO,
    "taxa_amostragem": TAXA_AMOSTRAGEM,
    "portadora_hz": PORTADORA_HZ,
    "ganho": GANHO,
    "profundidade_modulacao": PROFUNDIDADE_MODULACAO,
    "fade_segundos": FADE_SEGUNDOS,
    "fases": FASES,
}

PROTOCOLO_ID = hashlib.sha256(
    json.dumps(
        PROTOCOLO_CONFIG,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()


# ============================================================
# GITHUB — UTILITÁRIOS
# ============================================================


def obter_token():
    """Lê o token dos Secrets do Streamlit ou do ambiente."""
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



def ler_texto_github(caminho, token=""):
    """Retorna o conteúdo textual de um arquivo pequeno ou None se não existir."""
    url = f"{GITHUB_API}/contents/{caminho}?ref={GITHUB_BRANCH}"

    resposta = requests.get(
        url,
        headers=github_headers(token, "application/vnd.github.raw+json"),
        timeout=30,
    )

    if resposta.status_code == 404:
        return None

    if resposta.status_code != 200:
        raise RuntimeError(
            f"Falha ao ler {caminho} no GitHub.\n"
            f"HTTP {resposta.status_code}: {resposta.text}"
        )

    return resposta.text.strip()



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
        "Falha ao verificar o áudio no GitHub.\n"
        f"HTTP {resposta.status_code}: {resposta.text}"
    )



def baixar_audio_do_github(destino, token=""):
    """Baixa o WAV correto do GitHub para esta instância."""
    url = f"{GITHUB_API}/contents/{CAMINHO_GITHUB}?ref={GITHUB_BRANCH}"

    resposta = requests.get(
        url,
        headers=github_headers(token, "application/vnd.github.raw+json"),
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



def versao_local_corresponde():
    if not ARQUIVO_REPO_LOCAL.exists():
        return False

    if not ARQUIVO_VERSAO_REPO_LOCAL.exists():
        return False

    try:
        versao = ARQUIVO_VERSAO_REPO_LOCAL.read_text(
            encoding="utf-8"
        ).strip()
    except OSError:
        return False

    return versao == PROTOCOLO_ID


# ============================================================
# ÁUDIO — MATEMÁTICA
# ============================================================


def segundos_antes_da_fase(indice_fase):
    return sum(FASES[i]["tempo"] for i in range(indice_fase))



def ciclos_alvo_antes_da_fase(indice_fase):
    """
    Total de ciclos da frequência-alvo acumulados antes da fase.
    Mantém a fase matemática contínua nas transições.
    """
    ciclos = 0.0

    for i in range(indice_fase):
        fase = FASES[i]
        duracao = float(fase["tempo"])
        f0 = float(fase["alvo_inicio"])
        f1 = float(fase["alvo_fim"])

        ciclos += ((f0 + f1) / 2.0) * duracao

    return ciclos



def gerar_bloco(fase, indice_fase, inicio_amostra, quantidade):
    """Gera um bloco estéreo mantendo a portadora e o alvo contínuos."""

    indices_locais = inicio_amostra + np.arange(
        quantidade,
        dtype=np.float64,
    )

    t_local = indices_locais / TAXA_AMOSTRAGEM

    inicio_global_segundos = segundos_antes_da_fase(indice_fase)
    t_global = inicio_global_segundos + t_local

    # Portadora contínua de 288 Hz.
    fase_portadora = 2.0 * np.pi * PORTADORA_HZ * t_global

    duracao = float(fase["tempo"])
    alvo_inicio = float(fase["alvo_inicio"])
    alvo_fim = float(fase["alvo_fim"])

    inclinacao = (alvo_fim - alvo_inicio) / duracao

    # Integral da frequência-alvo instantânea:
    # ciclos(t) = f0*t + 0,5*k*t²
    ciclos_alvo = (
        ciclos_alvo_antes_da_fase(indice_fase)
        + alvo_inicio * t_local
        + 0.5 * inclinacao * (t_local ** 2)
    )

    fase_alvo = 2.0 * np.pi * ciclos_alvo

    # Binaural:
    # L = 288 Hz
    # R = 288 Hz + frequência-alvo instantânea.
    esquerda = np.sin(fase_portadora)
    direita = np.sin(fase_portadora + fase_alvo)

    # Modulação de amplitude usando a mesma frequência-alvo.
    # O envelope nunca zera completamente.
    modulacao = (
        1.0
        - (PROFUNDIDADE_MODULACAO / 2.0)
        + (PROFUNDIDADE_MODULACAO / 2.0) * np.sin(fase_alvo)
    )

    esquerda *= modulacao
    direita *= modulacao

    # Fade somente no início e no final da sessão completa.
    inicio_global_amostras = int(
        inicio_global_segundos * TAXA_AMOSTRAGEM
    )

    indices_globais = inicio_global_amostras + indices_locais
    fade_amostras = int(FADE_SEGUNDOS * TAXA_AMOSTRAGEM)

    envelope = np.ones(quantidade, dtype=np.float64)

    mascara_inicio = indices_globais < fade_amostras
    if np.any(mascara_inicio):
        envelope[mascara_inicio] = (
            indices_globais[mascara_inicio]
            / max(fade_amostras - 1, 1)
        )

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
    """Gera os 15 minutos em blocos e grava diretamente no disco."""

    destino = Path(destino)
    parcial = Path(str(destino) + ".gerando")

    if parcial.exists():
        parcial.unlink()

    chunk = int(TAXA_AMOSTRAGEM * CHUNK_SEGUNDOS)
    progresso = st.progress(0, text="Gerando o novo áudio...")

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
                    text=f"Gerando o novo áudio... {min(percentual, 100)}%",
                )

    os.replace(parcial, destino)
    progresso.empty()

    return destino


# ============================================================
# GITHUB — OBJETOS GIT
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



def criar_blob_bytes(token, dados):
    conteudo_b64 = base64.b64encode(dados).decode("ascii")

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

    del conteudo_b64

    if resposta.status_code != 201:
        raise RuntimeError(
            "O GitHub não aceitou um dos arquivos.\n"
            f"HTTP {resposta.status_code}: {resposta.text}"
        )

    return resposta.json()["sha"]



def criar_blob_do_audio(token, arquivo):
    tamanho = Path(arquivo).stat().st_size

    if tamanho >= 100 * 1024 * 1024:
        raise RuntimeError(
            "O WAV ficou maior que 100 MiB e não pode ser "
            "gravado como arquivo normal no GitHub."
        )

    with open(arquivo, "rb") as f:
        dados = f.read()

    try:
        return criar_blob_bytes(token, dados)
    finally:
        del dados



def listar_outros_wavs(token):
    """
    Lista WAVs antigos dentro de audio/ para que o commit novo deixe
    apenas parceria_ceitec_ecomcs.wav como arquivo de áudio.
    """
    resposta = github_request(
        "GET",
        f"/contents/audio?ref={GITHUB_BRANCH}",
        token=token,
        timeout=30,
    )

    if resposta.status_code == 404:
        return []

    if resposta.status_code != 200:
        raise RuntimeError(
            "Não foi possível listar a pasta audio/.\n"
            f"HTTP {resposta.status_code}: {resposta.text}"
        )

    itens = resposta.json()
    if not isinstance(itens, list):
        return []

    outros = []

    for item in itens:
        caminho = item.get("path", "")
        tipo = item.get("type", "")

        if (
            tipo == "file"
            and caminho.lower().endswith(".wav")
            and caminho != CAMINHO_GITHUB
        ):
            outros.append(caminho)

    return outros



def criar_tree(
    token,
    base_tree_sha,
    blob_audio_sha,
    blob_versao_sha,
    wavs_para_apagar,
):
    entradas = [
        {
            "path": CAMINHO_GITHUB,
            "mode": "100644",
            "type": "blob",
            "sha": blob_audio_sha,
        },
        {
            "path": CAMINHO_VERSAO_GITHUB,
            "mode": "100644",
            "type": "blob",
            "sha": blob_versao_sha,
        },
    ]

    for caminho in wavs_para_apagar:
        entradas.append(
            {
                "path": caminho,
                "mode": "100644",
                "type": "blob",
                "sha": None,
            }
        )

    resposta = github_request(
        "POST",
        "/git/trees",
        token=token,
        timeout=60,
        json={
            "base_tree": base_tree_sha,
            "tree": entradas,
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
            "message": "Atualiza áudio alfa/theta/gamma pré-processado",
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
    Sobrescreve o WAV de nome fixo e grava o hash da versão do
    protocolo no MESMO commit. Também remove outros .wav de audio/.
    """

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN não configurado nos Secrets do Streamlit."
        )

    status = st.empty()
    status.info("Enviando o novo áudio para o GitHub...")

    blob_audio_sha = criar_blob_do_audio(token, arquivo)
    blob_versao_sha = criar_blob_bytes(
        token,
        (PROTOCOLO_ID + "\n").encode("utf-8"),
    )

    wavs_para_apagar = listar_outros_wavs(token)

    # Se a branch mudar enquanto publicamos, reutilizamos os blobs e
    # reconstruímos apenas tree/commit a partir do HEAD mais recente.
    for _ in range(3):
        head_sha = obter_head_da_branch(token)
        commit_atual = obter_commit(token, head_sha)
        base_tree_sha = commit_atual["tree"]["sha"]

        tree_sha = criar_tree(
            token,
            base_tree_sha,
            blob_audio_sha,
            blob_versao_sha,
            wavs_para_apagar,
        )

        commit_sha = criar_commit(
            token,
            tree_sha,
            head_sha,
        )

        resposta = atualizar_branch(token, commit_sha)

        if resposta.status_code == 200:
            status.empty()
            return True

        if resposta.status_code not in (409, 422):
            raise RuntimeError(
                "Falha ao atualizar a branch main.\n"
                f"HTTP {resposta.status_code}: {resposta.text}"
            )

        # A lista pode ter mudado depois de outro commit concorrente.
        wavs_para_apagar = listar_outros_wavs(token)

    # Outra instância pode ter terminado primeiro.
    versao_remota = ler_texto_github(CAMINHO_VERSAO_GITHUB, token)

    if versao_remota == PROTOCOLO_ID and audio_existe_no_github(token):
        status.empty()
        return True

    raise RuntimeError(
        "Não foi possível atualizar a branch main. "
        "Verifique se há proteção de branch impedindo commits diretos."
    )


# ============================================================
# PREPARAÇÃO AUTOMÁTICA
# ============================================================


def preparar_audio():
    token = obter_token()

    # 1) Caso normal depois do primeiro commit/redeploy:
    # o clone já contém o WAV e o marcador da versão correta.
    if versao_local_corresponde():
        return ARQUIVO_REPO_LOCAL, "repositorio"

    # 2) Consulta o GitHub. Isso resolve também o caso em que outra
    # instância publicou a versão nova e esta instância ainda não fez
    # redeploy.
    try:
        versao_remota = ler_texto_github(
            CAMINHO_VERSAO_GITHUB,
            token,
        )

        if versao_remota == PROTOCOLO_ID and audio_existe_no_github(token):
            baixar_audio_do_github(ARQUIVO_TEMP, token)
            return ARQUIVO_TEMP, "github"

    except Exception:
        if token:
            raise

    # 3) A versão mudou (ou ainda não existe). Para publicar o novo
    # áudio, o token de escrita é obrigatório.
    if not token:
        raise RuntimeError(
            "O áudio do GitHub pertence a uma versão anterior do protocolo "
            "(ou ainda não existe), mas GITHUB_TOKEN não está configurado "
            "nos Secrets do Streamlit."
        )

    st.info(
        "Novo protocolo detectado. O áudio será gerado uma vez e "
        "substituirá o WAV anterior no GitHub."
    )

    # 4) Gera o novo áudio localmente.
    gerar_audio(ARQUIVO_TEMP)

    # 5) Evita publicação duplicada se outra instância terminou enquanto
    # esta estava gerando.
    versao_remota = ler_texto_github(CAMINHO_VERSAO_GITHUB, token)

    if versao_remota == PROTOCOLO_ID and audio_existe_no_github(token):
        return ARQUIVO_TEMP, "gerado_localmente"

    # 6) Sobrescreve o mesmo WAV e atualiza o marcador no mesmo commit.
    publicar_audio_no_github(
        ARQUIVO_TEMP,
        token,
    )

    return ARQUIVO_TEMP, "publicado"


# ============================================================
# INTERFACE
# ============================================================

st.title("🎧 Experiência Sonora")


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
                "Novo áudio gerado e salvo em "
                "`audio/parceria_ceitec_ecomcs.wav`."
            )

            st.info(
                "O commit na branch `main` pode provocar um redeploy "
                "único do Streamlit. Depois disso, todos os usuários "
                "usarão o WAV já armazenado no repositório."
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
        str(arquivo_audio),
        format="audio/wav",
        autoplay=True,
        loop=False,
    )

    st.caption(
        "Mantenha o volume em um nível confortável. "
        "Se sentir desconforto, interrompa a reprodução."
    )
