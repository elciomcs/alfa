import streamlit as st
import asyncio
import edge_tts
import base64
import tempfile
import os

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Manual Prático do Amor",
    page_icon="❤️",
    layout="centered"
)

st.title("❤️ Manual Prático do Amor")
st.caption("Sentir → compreender → escolher → agir")

st.markdown(
    """
Este aplicativo conduz uma jornada em quatro etapas:

1. **Amor em DEUS**
2. **Amor ao Próximo e Empatia**
3. **Anseio e Propósito**
4. **Integração Noturna — 1 hora**

A experiência foi estruturada para que a pessoa não precise operar vários controles durante a prática.

O fluxo é:

**voz → pausa → áudio → orientações pontuais → conclusão automática**
"""
)

# ============================================================
# CONFIGURAÇÕES
# ============================================================

st.sidebar.header("⚙️ Configurações")

voz_escolhida = st.sidebar.selectbox(
    "Escolha a voz",
    [
        "pt-BR-FranciscaNeural",
        "pt-BR-AntonioNeural"
    ],
    format_func=lambda x:
        "Feminina suave" if "Francisca" in x else "Masculina suave"
)

velocidade = st.sidebar.slider(
    "Velocidade da voz",
    min_value=-30,
    max_value=15,
    value=-12,
    step=1
)

st.sidebar.caption(
    "A narração neural precisa de internet no servidor Streamlit "
    "para ser gerada."
)

# ============================================================
# FUNÇÃO TTS
# ============================================================

async def gerar_voz_async(texto, voz, velocidade):
    communicate = edge_tts.Communicate(
        texto,
        voz,
        rate=f"{velocidade}%"
    )

    temp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    )

    temp.close()

    await communicate.save(temp.name)

    with open(temp.name, "rb") as f:
        audio_bytes = f.read()

    os.unlink(temp.name)

    return audio_bytes


def gerar_voz(texto, voz, velocidade):
    return asyncio.run(
        gerar_voz_async(
            texto,
            voz,
            velocidade
        )
    )


# ============================================================
# CONVERSÃO BASE64
# ============================================================

def bytes_para_base64(data):
    return base64.b64encode(data).decode()


# ============================================================
# PLAYER AUTOMÁTICO COM WEB AUDIO
# ============================================================

def player_sessao(
    voz_inicial,
    duracao_audio,
    frequencia_inicio,
    frequencia_fim=None,
    falas_intermediarias=None,
    volume=0.12,
    titulo="Sessão"
):

    voz_b64 = bytes_para_base64(voz_inicial)

    falas_js = []

    if falas_intermediarias:

        for tempo, audio_bytes in falas_intermediarias:

            falas_js.append(
                {
                    "tempo": tempo,
                    "audio": bytes_para_base64(audio_bytes)
                }
            )

    html = f"""
    <div style="
        padding:18px;
        border:1px solid #ddd;
        border-radius:14px;
        margin-top:15px;
    ">

        <h4>{titulo}</h4>

        <button
            onclick="iniciarSessao()"
            style="
                padding:12px 20px;
                font-size:16px;
                border-radius:10px;
                border:none;
                cursor:pointer;
            "
        >
            ▶️ Iniciar sessão
        </button>

        <button
            onclick="pararSessao()"
            style="
                padding:12px 20px;
                font-size:16px;
                border-radius:10px;
                border:none;
                cursor:pointer;
                margin-left:8px;
            "
        >
            ⏹️ Parar
        </button>

        <div
            id="status"
            style="
                margin-top:12px;
                font-size:14px;
                opacity:.8;
            "
        >
            Pronto para iniciar.
        </div>

    </div>

    <script>

    let ctx = null;
    let oscillator1 = null;
    let oscillator2 = null;
    let gainNode = null;
    let timers = [];
    let stopped = false;

    const voiceData =
        "data:audio/mp3;base64,{voz_b64}";

    const falas = {falas_js};

    function status(msg) {{
        document.getElementById("status").innerText = msg;
    }}

    function pararSessao() {{

        stopped = true;

        timers.forEach(
            timer => clearTimeout(timer)
        );

        timers = [];

        if (oscillator1) {{
            try {{
                oscillator1.stop();
            }} catch(e) {{}}
        }}

        if (oscillator2) {{
            try {{
                oscillator2.stop();
            }} catch(e) {{}}
        }}

        if (ctx) {{
            try {{
                ctx.close();
            }} catch(e) {{}}
        }}

        oscillator1 = null;
        oscillator2 = null;
        gainNode = null;
        ctx = null;

        status("Sessão encerrada.");

    }}

    async function tocarVoz(data) {{

        return new Promise(
            (resolve) => {{

                const audio = new Audio(data);

                audio.onended = resolve;
                audio.onerror = resolve;

                audio.play();

            }}
        );

    }}

    function iniciarSomFundo() {{

        ctx = new (
            window.AudioContext ||
            window.webkitAudioContext
        )();

        oscillator1 = ctx.createOscillator();
        oscillator2 = ctx.createOscillator();

        gainNode = ctx.createGain();

        oscillator1.type = "sine";
        oscillator2.type = "sine";

        oscillator1.frequency.value = 120;

        oscillator2.frequency.value =
            120 + {frequencia_inicio};

        gainNode.gain.value = {volume};

        oscillator1.connect(gainNode);
        oscillator2.connect(gainNode);

        gainNode.connect(ctx.destination);

        oscillator1.start();
        oscillator2.start();

        {"oscillator2.frequency.linearRampToValueAtTime(120 + " + str(frequencia_fim) + ", ctx.currentTime + " + str(duracao_audio) + ");" if frequencia_fim else ""}

        oscillator1.stop(
            ctx.currentTime + {duracao_audio}
        );

        oscillator2.stop(
            ctx.currentTime + {duracao_audio}
        );

    }}

    async function iniciarSessao() {{

        pararSessao();

        stopped = false;

        status("🎙️ Iniciando narração...");

        await tocarVoz(voiceData);

        if (stopped) return;

        status("Respire...");

        await new Promise(
            r => setTimeout(r, 3000)
        );

        if (stopped) return;

        status("🎧 Iniciando áudio...");

        iniciarSomFundo();

        falas.forEach(
            item => {{

                const timer = setTimeout(
                    async () => {{

                        if (stopped) return;

                        if (gainNode) {{
                            gainNode.gain.linearRampToValueAtTime(
                                0.035,
                                ctx.currentTime + 1
                            );
                        }}

                        await tocarVoz(
                            "data:audio/mp3;base64," + item.audio
                        );

                        if (stopped) return;

                        if (gainNode) {{
                            gainNode.gain.linearRampToValueAtTime(
                                {volume},
                                ctx.currentTime + 1.5
                            );
                        }}

                    }},
                    item.tempo * 1000
                );

                timers.push(timer);

            }}
        );

        const fim = setTimeout(
            () => {{

                if (!stopped) {{

                    status("✅ Sessão concluída.");

                }}

            }},
            {duracao_audio * 1000}
        );

        timers.push(fim);

    }}

    </script>
    """

    st.components.v1.html(
        html,
        height=190
    )


# ============================================================
# ROTEIROS
# ============================================================

ROTEIRO_DEUS = """
Encontre uma posição confortável.

Se puder, coloque uma das mãos sobre o coração.

Respire lentamente.

Não tente fabricar nenhuma emoção.

Apenas permita-se estar presente.

Agora recorde algo concreto que DEUS fez por você.

Pode ser uma pessoa.

Uma oportunidade.

Uma proteção.

Um recomeço.

Um aprendizado.

A própria vida.

Não permaneça apenas no pensamento.

Procure sentir a gratidão.

Perceba seu peito.

Sua respiração.

Seu corpo.

Permita que a gratidão ocupe espaço dentro de você.

Em silêncio, diga:

DEUS, obrigado.

Permaneça alguns instantes nessa sensação.

Agora permita que esse Amor passe do coração para o pensamento.

Pergunte:

Se eu viver a partir deste Amor hoje, o que muda em mim?

Que pensamento precisa mudar?

Que atitude pode nascer desse sentimento?

Ao longo desta experiência, não force nada.

Apenas permita.

Sentir.

Pensar.

Escolher.

Agir.
"""

FALA_DEUS_2 = """
Continue respirando lentamente.

Escolha agora um segundo motivo de gratidão.

Não apenas pense nele.

Procure sentir.

Permaneça alguns instantes nesse estado.
"""

FALA_DEUS_7 = """
Agora observe seus pensamentos.

Se você realmente estivesse vivendo a partir do Amor,
como enxergaria as situações da sua vida?

Como enxergaria as pessoas?

O que mudaria dentro de você?
"""

FALA_DEUS_10 = """
Agora transforme o sentimento em ação.

Escolha uma atitude concreta.

Pode ser agradecer alguém.

Telefonar.

Escutar.

Ajudar.

Pedir perdão.

Perdoar.

Servir.

O Amor se completa quando encontra uma forma de chegar à vida.
"""


ROTEIRO_PROXIMO = """
Traga à mente uma pessoa.

Não comece pelo problema dela.

Comece pelo Amor.

Reconheça que essa pessoa possui uma história.

Medos.

Desejos.

Feridas.

Esperanças.

Necessidades.

Respire lentamente.

Procure sentir boa vontade por ela.

Deseje sinceramente que ela esteja bem.

Agora pergunte:

O que essa pessoa pode estar vivendo?

Não suponha que você sabe tudo.

Apenas abra espaço para compreender.

Amar o próximo começa quando deixamos de olhar apenas para nós mesmos.

A empatia é uma ponte.

O Amor é o caminho.

Permita que esta experiência conduza você
da empatia para uma ação concreta.
"""

FALA_PROXIMO_3 = """
Pergunte agora:

Do que essa pessoa pode estar precisando?

Talvez precise ser ouvida.

Respeitada.

Compreendida.

Ajudada.

Acompanhada.

Ou simplesmente sentir que não está sozinha.
"""

FALA_PROXIMO_6 = """
Agora pergunte:

O que significa amar esta pessoa hoje?

Talvez seja ouvir sem interromper.

Oferecer ajuda.

Encaminhar uma mensagem.

Pedir perdão.

Respeitar um limite.

Ou simplesmente estar presente.
"""

FALA_PROXIMO_9 = """
Escolha agora uma ação concreta.

O Amor deixa de ser apenas sentimento
quando se transforma em presença,
palavra
e atitude.
"""


ROTEIRO_ANSEIO_BASE = """
Respire lentamente.

Agora volte sua atenção para algo
que você deseja profundamente em sua vida.

Não se apresse.

Pergunte a si mesmo:

Por que isso é importante para mim?

O que esse desejo representa?

Que tipo de vida ele aponta?

Agora conecte esse anseio ao Amor.

Pergunte:

Se isso acontecer,
como poderá produzir mais vida,
crescimento,
cuidado
ou contribuição?

Não transforme esperança em ansiedade.

Não tente controlar o futuro.

Apenas permita que o desejo encontre direção.

Sentimento.

Pensamento.

Visão.

Escolha.

Ação.
"""


ROTEIRO_NOITE = """
Agora você chegou à última etapa.

Não há mais nada para conquistar neste momento.

Apenas desacelerar.

Respire lentamente.

Relaxe a testa.

Os olhos.

A mandíbula.

Os ombros.

Permita que o corpo reconheça
que este é um momento de descanso.

Recorde algo bom deste dia.

Agradeça.

Se alguma preocupação aparecer,
não lute contra ela.

Reconheça.

E deixe passar.

Você não precisa resolver tudo agora.

Depois desta narração,
o áudio continuará sozinho por uma hora.

Não será necessário fazer mais nada.

Apenas repousar.
"""


# ============================================================
# ABAS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "❤️ Amor em DEUS",
        "🤝 Amor ao Próximo",
        "✨ Anseio e Propósito",
        "🌙 Integração 1h"
    ]
)


# ============================================================
# ETAPA 1
# ============================================================

with tab1:

    st.header("1. Amor em DEUS")

    st.write(
        """
Comece pelo Amor recebido.

A prática conduz:

**gratidão → sentimento → pensamento → ação**
"""
    )

    if st.button(
        "Preparar sessão Amor em DEUS"
    ):

        with st.spinner(
            "Preparando voz..."
        ):

            voz0 = gerar_voz(
                ROTEIRO_DEUS,
                voz_escolhida,
                velocidade
            )

            voz2 = gerar_voz(
                FALA_DEUS_2,
                voz_escolhida,
                velocidade
            )

            voz7 = gerar_voz(
                FALA_DEUS_7,
                voz_escolhida,
                velocidade
            )

            voz10 = gerar_voz(
                FALA_DEUS_10,
                voz_escolhida,
                velocidade
            )

        st.session_state["sessao_deus"] = (
            voz0,
            voz2,
            voz7,
            voz10
        )

    if "sessao_deus" in st.session_state:

        voz0, voz2, voz7, voz10 = (
            st.session_state["sessao_deus"]
        )

        player_sessao(
            voz_inicial=voz0,
            duracao_audio=12 * 60,
            frequencia_inicio=8,
            frequencia_fim=18,
            falas_intermediarias=[
                (120, voz2),
                (420, voz7),
                (600, voz10)
            ],
            volume=0.10,
            titulo="❤️ Sessão — Amor em DEUS"
        )


# ============================================================
# ETAPA 2
# ============================================================

with tab2:

    st.header(
        "2. Amor ao Próximo e Empatia"
    )

    st.write(
        """
A empatia é a ponte.

O objetivo é transformar:

**Amor → empatia → compreensão → ação**
"""
    )

    if st.button(
        "Preparar sessão Amor ao Próximo"
    ):

        with st.spinner(
            "Preparando voz..."
        ):

            voz0 = gerar_voz(
                ROTEIRO_PROXIMO,
                voz_escolhida,
                velocidade
            )

            voz3 = gerar_voz(
                FALA_PROXIMO_3,
                voz_escolhida,
                velocidade
            )

            voz6 = gerar_voz(
                FALA_PROXIMO_6,
                voz_escolhida,
                velocidade
            )

            voz9 = gerar_voz(
                FALA_PROXIMO_9,
                voz_escolhida,
                velocidade
            )

        st.session_state["sessao_proximo"] = (
            voz0,
            voz3,
            voz6,
            voz9
        )

    if "sessao_proximo" in st.session_state:

        voz0, voz3, voz6, voz9 = (
            st.session_state["sessao_proximo"]
        )

        player_sessao(
            voz_inicial=voz0,
            duracao_audio=10 * 60,
            frequencia_inicio=8,
            frequencia_fim=14,
            falas_intermediarias=[
                (180, voz3),
                (360, voz6),
                (540, voz9)
            ],
            volume=0.10,
            titulo="🤝 Sessão — Amor ao Próximo"
        )


# ============================================================
# ETAPA 3
# ============================================================

with tab3:

    st.header(
        "3. Anseio e Propósito"
    )

    st.write(
        """
Escolha algo significativo que deseja viver.

O processo será:

**anseio → sentimento → visão → escolha → ação**
"""
    )

    anseio = st.text_area(
        "Qual é o seu anseio?",
        placeholder=(
            "Ex.: melhorar minha relação familiar, "
            "realizar um projeto, encontrar trabalho..."
        )
    )

    if st.button(
        "Preparar sessão Anseio e Propósito"
    ):

        texto_anseio = (
            ROTEIRO_ANSEIO_BASE
            + "\n\nSeu anseio escolhido é:\n"
            + anseio
            if anseio
            else ROTEIRO_ANSEIO_BASE
        )

        fala_meio = """
Agora imagine por alguns instantes
como seria viver de maneira coerente
com esse propósito.

Observe como você pensaria.

Como agiria.

Como trataria as pessoas.
"""

        fala_final = """
Agora escolha o menor passo real
que depende de você.

A esperança ganha direção
quando encontra ação.
"""

        with st.spinner(
            "Preparando voz..."
        ):

            voz0 = gerar_voz(
                texto_anseio,
                voz_escolhida,
                velocidade
            )

            voz_meio = gerar_voz(
                fala_meio,
                voz_escolhida,
                velocidade
            )

            voz_final = gerar_voz(
                fala_final,
                voz_escolhida,
                velocidade
            )

        st.session_state["sessao_anseio"] = (
            voz0,
            voz_meio,
            voz_final
        )

    if "sessao_anseio" in st.session_state:

        voz0, voz_meio, voz_final = (
            st.session_state["sessao_anseio"]
        )

        player_sessao(
            voz_inicial=voz0,
            duracao_audio=10 * 60,
            frequencia_inicio=8,
            frequencia_fim=18,
            falas_intermediarias=[
                (300, voz_meio),
                (480, voz_final)
            ],
            volume=0.10,
            titulo="✨ Sessão — Anseio e Propósito"
        )


# ============================================================
# ETAPA 4
# ============================================================

with tab4:

    st.header(
        "4. Integração Noturna — 1 Hora"
    )

    st.write(
        """
Esta é a última etapa.

Depois da narração inicial,
o som continua sozinho por **1 hora**.

Estrutura:

- primeira metade: aproximadamente **6 Hz**
- transição gradual
- segunda metade: aproximadamente **2,5 Hz**

O som combina modulação
monaural e isocrônica.
"""
    )

    st.warning(
        "Use volume baixo. "
        "Não utilize enquanto dirige "
        "ou realiza atividades que exigem atenção."
    )

    if st.button(
        "Preparar Integração Noturna"
    ):

        with st.spinner(
            "Preparando voz..."
        ):

            voz_noite = gerar_voz(
                ROTEIRO_NOITE,
                voz_escolhida,
                velocidade
            )

        st.session_state[
            "sessao_noite"
        ] = voz_noite

    if "sessao_noite" in st.session_state:

        player_sessao(
            voz_inicial=
                st.session_state["sessao_noite"],
            duracao_audio=60 * 60,
            frequencia_inicio=6,
            frequencia_fim=2.5,
            falas_intermediarias=[],
            volume=0.08,
            titulo="🌙 Integração Noturna — 1 Hora"
        )


# ============================================================
# INFORMAÇÕES IMPORTANTES
# ============================================================

st.divider()

with st.expander(
    "ℹ️ Sobre frequências, coração e bem-estar"
):

    st.markdown(
        """
Os sons e frequências deste aplicativo
são usados como suporte para
relaxamento, atenção, contemplação
e organização da experiência interior.

Eles não devem ser interpretados
como garantia de indução de estados
cerebrais específicos.

Da mesma forma,
conceitos como energia,
campo do coração
ou destino podem ser utilizados
como linguagem simbólica,
espiritual ou contemplativa.

O aplicativo não afirma
que pensamentos ou sentimentos
alterem fisicamente acontecimentos futuros
por meio de campos eletromagnéticos.

Depressão e ansiedade
são condições multifatoriais.

Amor,
vínculo,
espiritualidade,
sentido,
apoio social
e práticas contemplativas
podem contribuir para o bem-estar,
mas não substituem acompanhamento
médico ou psicológico quando necessário.
"""
    )


# ============================================================
# FECHAMENTO
# ============================================================

st.divider()

st.markdown(
    """
## O caminho completo

**DEUS → Amor → Gratidão → Coração → Pensamento → Amor ao Próximo → Empatia → Propósito → Escolha → Ação → Acolhimento → Comunidade → Paz**
"""
)

st.caption(
    "Manual Prático do Amor — experiência de contemplação, "
    "empatia, propósito e ação."
)
