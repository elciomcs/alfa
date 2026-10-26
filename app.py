import streamlit as st
import streamlit.components.v1 as components

import asyncio
import edge_tts

import base64
import tempfile
import os
import json
import html


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Manual Prático do Amor",
    page_icon="❤️",
    layout="centered"
)

st.title("❤️ Manual Prático do Amor")

st.caption(
    "Sentir → observar → compreender → escolher → agir"
)

st.markdown(
    """
Uma jornada prática em quatro etapas:

**1. Amor em DEUS**  
**2. Amor ao Próximo e Empatia**  
**3. Anseio e Propósito**  
**4. Integração Noturna — 1 hora**

O princípio central é:

### SENTIR → OBSERVAR O PENSAMENTO → ESCOLHER → AGIR
"""
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

with st.sidebar:

    st.header("⚙️ Configurações")

    voz_escolhida = st.selectbox(
        "Escolha a voz",
        [
            "pt-BR-FranciscaNeural",
            "pt-BR-AntonioNeural"
        ],
        format_func=lambda voz:
            "Feminina suave"
            if "Francisca" in voz
            else "Masculina suave"
    )

    velocidade = st.slider(
        "Velocidade da voz",
        min_value=-30,
        max_value=10,
        value=-15,
        step=1
    )

    pausa_inicial = st.slider(
        "Pausa entre a narração e o áudio",
        min_value=1,
        max_value=10,
        value=4,
        step=1
    )


# ============================================================
# EDGE TTS
# ============================================================

async def gerar_voz_async(
    texto,
    voz,
    velocidade
):

    rate = f"{velocidade:+d}%"

    communicate = edge_tts.Communicate(
        text=texto,
        voice=voz,
        rate=rate
    )

    arquivo = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    )

    arquivo.close()

    try:

        await communicate.save(
            arquivo.name
        )

        with open(
            arquivo.name,
            "rb"
        ) as f:

            dados = f.read()

        return dados

    finally:

        if os.path.exists(
            arquivo.name
        ):
            os.unlink(
                arquivo.name
            )


@st.cache_data(show_spinner=False)
def gerar_voz(
    texto,
    voz,
    velocidade
):

    loop = asyncio.new_event_loop()

    try:

        asyncio.set_event_loop(
            loop
        )

        return loop.run_until_complete(
            gerar_voz_async(
                texto,
                voz,
                velocidade
            )
        )

    finally:

        loop.close()


# ============================================================
# BASE64
# ============================================================

def para_base64(
    dados
):

    return base64.b64encode(
        dados
    ).decode("utf-8")


# ============================================================
# PLAYER AUTOMÁTICO
# ============================================================

def player_sessao(
    titulo,
    voz_inicial,
    duracao_audio,
    frequencia_inicio,
    frequencia_fim,
    falas_intermediarias=None,
    volume=0.08,
    modo="binaural",
    pausa=4
):

    if falas_intermediarias is None:
        falas_intermediarias = []

    inicial_b64 = para_base64(
        voz_inicial
    )

    falas = []

    for tempo, audio in falas_intermediarias:

        falas.append(
            {
                "tempo": tempo,
                "audio": para_base64(
                    audio
                )
            }
        )

    falas_json = json.dumps(
        falas,
        ensure_ascii=False
    )

    titulo_html = html.escape(
        titulo
    )

    titulo_json = json.dumps(
        titulo,
        ensure_ascii=False
    )

    html_player = f"""
    <div style="
        border:1px solid rgba(120,120,120,.30);
        border-radius:16px;
        padding:18px;
        margin-top:10px;
        background:rgba(120,120,120,.04);
        font-family:Arial,sans-serif;
    ">

        <div style="
            font-size:18px;
            font-weight:700;
            margin-bottom:14px;
        ">
            {titulo_html}
        </div>

        <div style="
            display:flex;
            gap:8px;
            flex-wrap:wrap;
        ">

            <button
                onclick="iniciarSessao()"
                style="
                    border:none;
                    border-radius:10px;
                    padding:11px 18px;
                    cursor:pointer;
                    font-size:15px;
                "
            >
                ▶️ Iniciar sessão
            </button>

            <button
                onclick="pausarSessao()"
                style="
                    border:none;
                    border-radius:10px;
                    padding:11px 18px;
                    cursor:pointer;
                "
            >
                ⏸️ Pausar
            </button>

            <button
                onclick="continuarSessao()"
                style="
                    border:none;
                    border-radius:10px;
                    padding:11px 18px;
                    cursor:pointer;
                "
            >
                ⏯️ Continuar
            </button>

            <button
                onclick="pararSessao()"
                style="
                    border:none;
                    border-radius:10px;
                    padding:11px 18px;
                    cursor:pointer;
                "
            >
                ⏹️ Parar
            </button>

        </div>

        <div
            id="status"
            style="
                margin-top:13px;
                font-size:14px;
                opacity:.80;
            "
        >
            Toque em “Iniciar sessão”.
        </div>

    </div>


    <script>

    const titulo =
        {titulo_json};

    const vozInicial =
        "data:audio/mp3;base64,{inicial_b64}";

    const falas =
        {falas_json};

    const duracao =
        {float(duracao_audio)};

    const freqInicio =
        {float(frequencia_inicio)};

    const freqFim =
        {float(frequencia_fim)};

    const volumeBase =
        {float(volume)};

    const modo =
        "{modo}";

    const pausaInicial =
        {int(pausa * 1000)};


    let ctx = null;

    let osciladores = [];

    let timers = [];

    let duckGain = null;

    let parado = false;

    let audioVozAtual = null;


    function status(texto) {{

        document.getElementById(
            "status"
        ).innerText = texto;

    }}


    function limparTimers() {{

        timers.forEach(
            timer => clearTimeout(timer)
        );

        timers = [];

    }}


    function limparAudio() {{

        limparTimers();

        if (audioVozAtual) {{

            try {{
                audioVozAtual.pause();
                audioVozAtual.currentTime = 0;
            }}
            catch(e) {{}}

            audioVozAtual = null;

        }}

        osciladores.forEach(
            o => {{

                try {{
                    o.stop();
                }}
                catch(e) {{}}

            }}
        );

        osciladores = [];

        if (ctx) {{

            try {{
                ctx.close();
            }}
            catch(e) {{}}

            ctx = null;

        }}

        duckGain = null;

    }}


    function tocarVoz(
        origem
    ) {{

        return new Promise(
            resolve => {{

                audioVozAtual =
                    new Audio(origem);

                audioVozAtual.onended =
                    () => {{

                        audioVozAtual = null;

                        resolve();

                    }};

                audioVozAtual.onerror =
                    () => {{

                        audioVozAtual = null;

                        resolve();

                    }};

                audioVozAtual.play()
                    .catch(
                        () => resolve()
                    );

            }}
        );

    }}


    function criarContexto() {{

        ctx = new (
            window.AudioContext ||
            window.webkitAudioContext
        )();

        duckGain =
            ctx.createGain();

        duckGain.gain.value =
            1.0;

        duckGain.connect(
            ctx.destination
        );

    }}


    function iniciarBinaural() {{

        const agora =
            ctx.currentTime;

        const oscEsq =
            ctx.createOscillator();

        const oscDir =
            ctx.createOscillator();

        const ganhoEsq =
            ctx.createGain();

        const ganhoDir =
            ctx.createGain();

        const merger =
            ctx.createChannelMerger(2);

        const master =
            ctx.createGain();


        oscEsq.type = "sine";

        oscDir.type = "sine";


        const base = 150;


        oscEsq.frequency.setValueAtTime(
            base,
            agora
        );

        oscDir.frequency.setValueAtTime(
            base + freqInicio,
            agora
        );


        oscDir.frequency.linearRampToValueAtTime(
            base + freqFim,
            agora + duracao
        );


        ganhoEsq.gain.value =
            0.50;

        ganhoDir.gain.value =
            0.50;


        master.gain.setValueAtTime(
            0.0001,
            agora
        );

        master.gain.linearRampToValueAtTime(
            volumeBase,
            agora + 3
        );

        master.gain.setValueAtTime(
            volumeBase,
            agora + Math.max(
                3,
                duracao - 5
            )
        );

        master.gain.linearRampToValueAtTime(
            0.0001,
            agora + duracao
        );


        oscEsq.connect(
            ganhoEsq
        );

        oscDir.connect(
            ganhoDir
        );


        ganhoEsq.connect(
            merger,
            0,
            0
        );

        ganhoDir.connect(
            merger,
            0,
            1
        );


        merger.connect(
            master
        );

        master.connect(
            duckGain
        );


        oscEsq.start();

        oscDir.start();


        oscEsq.stop(
            agora + duracao
        );

        oscDir.stop(
            agora + duracao
        );


        osciladores.push(
            oscEsq,
            oscDir
        );

    }}


    function iniciarHibridoNoturno() {{

        const agora =
            ctx.currentTime;

        const base =
            100;

        const transicaoInicio =
            29.5 * 60;

        const transicaoFim =
            30.5 * 60;


        // -------------------------
        // MONAURAL
        // -------------------------

        const osc1 =
            ctx.createOscillator();

        const osc2 =
            ctx.createOscillator();

        const mistura =
            ctx.createGain();


        osc1.type =
            "sine";

        osc2.type =
            "sine";


        osc1.frequency.setValueAtTime(
            base,
            agora
        );


        osc2.frequency.setValueAtTime(
            base + 6,
            agora
        );

        osc2.frequency.setValueAtTime(
            base + 6,
            agora + transicaoInicio
        );

        osc2.frequency.linearRampToValueAtTime(
            base + 2.5,
            agora + transicaoFim
        );

        osc2.frequency.setValueAtTime(
            base + 2.5,
            agora + duracao
        );


        mistura.gain.value =
            0.5;


        osc1.connect(
            mistura
        );

        osc2.connect(
            mistura
        );


        // -------------------------
        // ISOCRÔNICO
        // -------------------------

        const isoGain =
            ctx.createGain();

        isoGain.gain.value =
            0.59;


        const lfo =
            ctx.createOscillator();

        const lfoAmplitude =
            ctx.createGain();


        lfo.type =
            "sine";


        lfo.frequency.setValueAtTime(
            6,
            agora
        );

        lfo.frequency.setValueAtTime(
            6,
            agora + transicaoInicio
        );

        lfo.frequency.linearRampToValueAtTime(
            2.5,
            agora + transicaoFim
        );

        lfo.frequency.setValueAtTime(
            2.5,
            agora + duracao
        );


        lfoAmplitude.gain.value =
            0.41;


        lfo.connect(
            lfoAmplitude
        );

        lfoAmplitude.connect(
            isoGain.gain
        );


        mistura.connect(
            isoGain
        );


        // -------------------------
        // VOLUME
        // -------------------------

        const master =
            ctx.createGain();


        master.gain.setValueAtTime(
            0.0001,
            agora
        );

        master.gain.linearRampToValueAtTime(
            volumeBase,
            agora + 8
        );

        master.gain.setValueAtTime(
            volumeBase,
            agora + duracao - 15
        );

        master.gain.linearRampToValueAtTime(
            0.0001,
            agora + duracao
        );


        isoGain.connect(
            master
        );

        master.connect(
            duckGain
        );


        osc1.start();

        osc2.start();

        lfo.start();


        osc1.stop(
            agora + duracao
        );

        osc2.stop(
            agora + duracao
        );

        lfo.stop(
            agora + duracao
        );


        osciladores.push(
            osc1,
            osc2,
            lfo
        );

    }}


    function iniciarSom() {{

        if (modo === "noturno") {{

            iniciarHibridoNoturno();

        }}
        else {{

            iniciarBinaural();

        }}

    }}


    async function falarDuranteSom(
        audioBase64
    ) {{

        if (
            parado ||
            !ctx
        ) return;


        status(
            "🎙️ Orientação..."
        );


        duckGain.gain.cancelScheduledValues(
            ctx.currentTime
        );

        duckGain.gain.setTargetAtTime(
            0.20,
            ctx.currentTime,
            0.25
        );


        await new Promise(
            resolve =>
                setTimeout(
                    resolve,
                    900
                )
        );


        if (parado) return;


        await tocarVoz(
            "data:audio/mp3;base64,"
            + audioBase64
        );


        if (parado) return;


        duckGain.gain.cancelScheduledValues(
            ctx.currentTime
        );

        duckGain.gain.setTargetAtTime(
            1.0,
            ctx.currentTime,
            0.45
        );


        status(
            "🎧 Continue a prática..."
        );

    }}


    async function iniciarSessao() {{

        limparAudio();

        parado =
            false;


        criarContexto();


        try {{

            await ctx.resume();

        }}
        catch(e) {{}}


        status(
            "🎙️ Narração inicial..."
        );


        await tocarVoz(
            vozInicial
        );


        if (parado) return;


        status(
            "Respire..."
        );


        await new Promise(
            resolve => {{

                const timer =
                    setTimeout(
                        resolve,
                        pausaInicial
                    );

                timers.push(
                    timer
                );

            }}
        );


        if (parado) return;


        status(
            "🎧 Iniciando áudio..."
        );


        iniciarSom();


        falas.forEach(
            item => {{

                const timer =
                    setTimeout(
                        () => {{

                            falarDuranteSom(
                                item.audio
                            );

                        }},
                        item.tempo * 1000
                    );

                timers.push(
                    timer
                );

            }}
        );


        const fim =
            setTimeout(
                () => {{

                    if (!parado) {{

                        status(
                            "✅ Sessão concluída."
                        );

                    }}

                }},
                duracao * 1000
            );


        timers.push(
            fim
        );

    }}


    function pausarSessao() {{

        if (ctx) {{

            ctx.suspend();

        }}

        if (audioVozAtual) {{

            audioVozAtual.pause();

        }}

        status(
            "⏸️ Sessão pausada."
        );

    }}


    function continuarSessao() {{

        if (ctx) {{

            ctx.resume();

        }}

        if (audioVozAtual) {{

            audioVozAtual.play();

        }}

        status(
            "▶️ Sessão retomada."
        );

    }}


    function pararSessao() {{

        parado =
            true;

        limparAudio();

        status(
            "⏹️ Sessão encerrada."
        );

    }}

    </script>
    """

    components.html(
        html_player,
        height=190
    )


# ============================================================
# ROTEIROS — ETAPA 1
# ============================================================

ROTEIRO_DEUS = """
Encontre uma posição confortável.

Se puder, coloque uma das mãos sobre o coração.

Respire lentamente.

Antes de mudar qualquer coisa,
apenas observe.

Qual pensamento estava ocupando sua mente
antes de começar esta experiência?

Não lute contra ele.

Apenas perceba.

Agora volte sua atenção para a respiração.

Recorde algo concreto
que DEUS fez por você.

Algo pelo qual você
é verdadeiramente grato.

Pode ser a vida.

Uma pessoa.

Uma oportunidade.

Uma proteção.

Um aprendizado.

Um recomeço.

Não permaneça somente na ideia.

Procure sentir a gratidão.

Observe o peito.

A respiração.

O rosto.

O corpo.

Permita que a gratidão
se torne uma experiência.

Em silêncio,
diga:

DEUS,
obrigado.

Permaneça alguns instantes
nessa sensação.

Agora observe novamente sua mente.

O pensamento que estava presente
no começo continua igual?

Não tente obrigá-lo a mudar.

Apenas perceba.

Sentir.

Observar.

Pensar.

Escolher.

Agir.
"""


FALA_DEUS_2 = """
Escolha agora
um segundo motivo de gratidão.

Não apenas pense.

Procure sentir.

Depois escolha um terceiro.

Perceba o que acontece
com sua mente
quando sua atenção permanece
na gratidão.
"""


FALA_DEUS_7 = """
Agora observe seus pensamentos.

Pergunte a si mesmo:

se eu viver a partir deste Amor,
como posso enxergar
esta situação de outra maneira?

Que pensamento nasce
quando o medo
não é a única voz dentro de mim?
"""


FALA_DEUS_10 = """
Compare seu estado atual
com o início da prática.

O que mudou?

Agora transforme
essa mudança interna
em uma escolha.

Qual atitude concreta
pode nascer deste Amor?

Agradecer.

Telefonar.

Ajudar.

Escutar.

Pedir perdão.

Perdoar.

Servir.

Escolha uma.
"""


# ============================================================
# ROTEIROS — ETAPA 2
# ============================================================

ROTEIRO_PROXIMO = """
Agora traga à mente
uma pessoa.

Antes de pensar
sobre o que ela fez
ou deixou de fazer,
observe sua própria mente.

Que julgamento aparece primeiro?

Que interpretação você já criou
sobre essa pessoa?

Apenas perceba.

Agora respire lentamente.

Lembre-se:

diante de você existe
uma vida inteira.

Uma história.

Medos.

Desejos.

Feridas.

Esperanças.

Necessidades.

Procure sentir
boa vontade por essa pessoa.

Deseje sinceramente
que ela esteja bem.

Agora pergunte:

o que eu realmente sei
sobre o que ela está vivendo?

E o que eu apenas imaginei?

A empatia começa
quando distinguimos
a realidade
das nossas interpretações.

Abra espaço para compreender.

A empatia é a ponte.

O Amor ao próximo
é aquilo que atravessa essa ponte.
"""


FALA_PROXIMO_3 = """
Pergunte agora:

o que essa pessoa
pode estar sentindo?

Do que ela
pode estar precisando?

Talvez precise
ser ouvida.

Respeitada.

Compreendida.

Ajudada.

Acompanhada.

Ou simplesmente sentir
que não está sozinha.
"""


FALA_PROXIMO_6 = """
Agora observe novamente
o pensamento que você tinha
sobre essa pessoa.

Ele continua exatamente igual?

Existe alguma coisa
que você consegue perceber agora
que não percebia antes?

Pergunte:

o que significa
amar esta pessoa hoje?
"""


FALA_PROXIMO_9 = """
Agora transforme
a compreensão
em atitude.

Talvez seja ouvir
sem interromper.

Perguntar
como ela realmente está.

Oferecer ajuda.

Pedir perdão.

Perdoar.

Respeitar um limite.

Ou simplesmente estar presente.

Escolha uma ação concreta.

O Amor se torna visível
quando chega ao próximo.
"""


# ============================================================
# ROTEIROS — ETAPA 3
# ============================================================

ROTEIRO_ANSEIO = """
Respire lentamente.

Agora observe
o que está acontecendo
dentro de você.

Existe algum desejo
que ocupa sua mente repetidamente?

Existe algo
que você gostaria profundamente
de viver?

Não julgue esse desejo.

Observe.

Pergunte:

por que isso
é tão importante para mim?

O que acredito
que vou sentir
quando isso acontecer?

Agora vá um pouco mais fundo.

O que esse anseio
representa?

Amor?

Segurança?

Pertencimento?

Realização?

Contribuição?

Liberdade?

Crescimento?

Não fique apenas
na imagem do resultado.

Perceba a necessidade
que existe por trás dele.

Agora conecte esse anseio
ao Amor.

Pergunte:

se eu caminhar nessa direção,
como isso poderá gerar
mais vida,
mais crescimento,
mais cuidado
ou mais contribuição?

Permita-se sentir esperança.

Depois observe
os pensamentos que aparecem.

Quais ajudam você
a caminhar?

Quais apenas repetem medo?

Observe.

Escolha conscientemente
qual pensamento
merece ser alimentado.
"""


FALA_ANSEIO_5 = """
Agora imagine
uma cena concreta.

Você vivendo
de maneira coerente
com aquilo que deseja.

Observe como você pensa.

Como se comporta.

Como trata as pessoas.

Não observe apenas
o resultado.

Observe quem você
precisaria se tornar
para caminhar nessa direção.
"""


FALA_ANSEIO_8 = """
Agora saia da imaginação
e volte para a realidade.

Pergunte:

qual é o menor passo
que depende de mim?

Não amanhã.

Não quando tudo estiver perfeito.

Qual passo
pode começar na vida real?
"""


# ============================================================
# ROTEIRO — ETAPA 4
# ============================================================

ROTEIRO_NOITE = """
Agora você chegou
à última etapa.

Neste momento,
não há nada
que precise conquistar.

Não há nada
que precise provar.

Apenas desacelere.

Respire lentamente.

Relaxe a testa.

Os olhos.

A mandíbula.

Os ombros.

Solte o peso do corpo.

Recorde algo bom
deste dia.

Mesmo que tenha sido pequeno.

Agradeça.

Se algum pensamento aparecer,
observe-o.

Você não precisa segui-lo.

Você pode perceber
um pensamento
sem entrar dentro dele.

Se alguma preocupação aparecer,
reconheça.

E volte para a respiração.

Você não precisa
resolver tudo agora.

Depois desta narração,
o áudio continuará sozinho
por uma hora.

Não será necessário
pensar em mais nada.

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

    st.header(
        "1. Amor em DEUS"
    )

    st.markdown(
        """
### Gratidão → Sentimento → Pensamento → Ação

O ponto de partida
é perceber o Amor recebido.
"""
    )

    if st.button(
        "Preparar Amor em DEUS",
        key="preparar_deus",
        use_container_width=True
    ):

        with st.spinner(
            "Preparando a experiência..."
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

        st.session_state[
            "sessao_deus"
        ] = (
            voz0,
            voz2,
            voz7,
            voz10
        )

    if "sessao_deus" in st.session_state:

        voz0, voz2, voz7, voz10 = (
            st.session_state[
                "sessao_deus"
            ]
        )

        player_sessao(
            titulo="❤️ Amor em DEUS",
            voz_inicial=voz0,
            duracao_audio=12 * 60,
            frequencia_inicio=8,
            frequencia_fim=18,
            falas_intermediarias=[
                (120, voz2),
                (420, voz7),
                (600, voz10)
            ],
            volume=0.07,
            modo="binaural",
            pausa=pausa_inicial
        )

    with st.expander(
        "🧠 Registro metacognitivo opcional"
    ):

        st.text_area(
            "Que pensamento predominava antes?",
            key="meta_deus_antes"
        )

        st.text_area(
            "O que mudou na maneira de pensar depois?",
            key="meta_deus_depois"
        )


# ============================================================
# ETAPA 2
# ============================================================

with tab2:

    st.header(
        "2. Amor ao Próximo e Empatia"
    )

    st.markdown(
        """
### Amor → Empatia → Compreensão → Ação

A empatia é a ponte.

O objetivo é que o Amor
chegue concretamente ao próximo.
"""
    )

    if st.button(
        "Preparar Amor ao Próximo",
        key="preparar_proximo",
        use_container_width=True
    ):

        with st.spinner(
            "Preparando a experiência..."
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

        st.session_state[
            "sessao_proximo"
        ] = (
            voz0,
            voz3,
            voz6,
            voz9
        )

    if "sessao_proximo" in st.session_state:

        voz0, voz3, voz6, voz9 = (
            st.session_state[
                "sessao_proximo"
            ]
        )

        player_sessao(
            titulo="🤝 Amor ao Próximo",
            voz_inicial=voz0,
            duracao_audio=10 * 60,
            frequencia_inicio=8,
            frequencia_fim=14,
            falas_intermediarias=[
                (180, voz3),
                (360, voz6),
                (540, voz9)
            ],
            volume=0.07,
            modo="binaural",
            pausa=pausa_inicial
        )

    with st.expander(
        "🧠 Registro metacognitivo opcional"
    ):

        st.text_area(
            "Qual era meu julgamento inicial sobre essa pessoa?",
            key="meta_proximo_antes"
        )

        st.text_area(
            "O que consigo perceber agora que não percebia antes?",
            key="meta_proximo_depois"
        )

        st.text_input(
            "Que ação de Amor realizarei?",
            key="acao_proximo"
        )


# ============================================================
# ETAPA 3
# ============================================================

with tab3:

    st.header(
        "3. Anseio e Propósito"
    )

    st.markdown(
        """
### Anseio → Sentimento → Pensamento → Visão → Escolha → Ação
"""
    )

    anseio = st.text_area(
        "Qual é o seu anseio?",
        placeholder=(
            "Ex.: melhorar uma relação, "
            "realizar um projeto, "
            "encontrar um trabalho com propósito..."
        ),
        key="anseio"
    )

    if st.button(
        "Preparar Anseio e Propósito",
        key="preparar_anseio",
        use_container_width=True
    ):

        texto_inicial = (
            ROTEIRO_ANSEIO
        )

        if anseio.strip():

            texto_inicial += (
                "\n\n"
                "O anseio que você escolheu "
                "para esta prática é: "
                + anseio
                + "."
            )

        with st.spinner(
            "Preparando a experiência..."
        ):

            voz0 = gerar_voz(
                texto_inicial,
                voz_escolhida,
                velocidade
            )

            voz5 = gerar_voz(
                FALA_ANSEIO_5,
                voz_escolhida,
                velocidade
            )

            voz8 = gerar_voz(
                FALA_ANSEIO_8,
                voz_escolhida,
                velocidade
            )

        st.session_state[
            "sessao_anseio"
        ] = (
            voz0,
            voz5,
            voz8
        )

    if "sessao_anseio" in st.session_state:

        voz0, voz5, voz8 = (
            st.session_state[
                "sessao_anseio"
            ]
        )

        player_sessao(
            titulo="✨ Anseio e Propósito",
            voz_inicial=voz0,
            duracao_audio=10 * 60,
            frequencia_inicio=8,
            frequencia_fim=18,
            falas_intermediarias=[
                (300, voz5),
                (480, voz8)
            ],
            volume=0.07,
            modo="binaural",
            pausa=pausa_inicial
        )

    with st.expander(
        "🧠 Registro metacognitivo opcional"
    ):

        st.text_area(
            "O que acredito que esse desejo me dará?",
            key="meta_anseio_significado"
        )

        st.text_area(
            "Que pensamentos me aproximam ou me afastam dele?",
            key="meta_anseio_pensamentos"
        )

        st.text_input(
            "Qual é o próximo passo que depende de mim?",
            key="meta_anseio_acao"
        )


# ============================================================
# ETAPA 4
# ============================================================

with tab4:

    st.header(
        "4. Integração Noturna — 1 Hora"
    )

    st.markdown(
        """
Esta é a **última etapa**.

Primeiro vem a narração.

Depois de uma pequena pausa,
o áudio começa automaticamente
e segue sozinho por uma hora.

### Estrutura

**0:00 até 29:30**  
Monaural + isocrônico em **6 Hz**

**29:30 até 30:30**  
Transição gradual

**30:30 até 60:00**  
Monaural + isocrônico em **2,5 Hz**
"""
    )

    st.caption(
        "Use volume baixo. "
        "Esta etapa é destinada ao repouso."
    )

    if st.button(
        "Preparar Integração Noturna",
        key="preparar_noite",
        use_container_width=True
    ):

        with st.spinner(
            "Preparando a narração..."
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
            titulo="🌙 Integração Noturna — 1 Hora",
            voz_inicial=(
                st.session_state[
                    "sessao_noite"
                ]
            ),
            duracao_audio=60 * 60,
            frequencia_inicio=6,
            frequencia_fim=2.5,
            falas_intermediarias=[],
            volume=0.045,
            modo="noturno",
            pausa=pausa_inicial
        )


# ============================================================
# CAMINHO COMPLETO
# ============================================================

st.divider()

st.markdown(
    """
## O Caminho do Amor

**DEUS → Amor → Gratidão → Coração → Consciência → Pensamento → Amor ao Próximo → Empatia → Propósito → Escolha → Ação → Acolhimento → Comunidade → Paz**
"""
)

st.caption(
    "Manual Prático do Amor"
)
