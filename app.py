import io
import wave
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
import json

# ============================================================
# CONFIGURAÇÃO
# ============================================================
st.set_page_config(
    page_title="Laboratório do Amor",
    page_icon="❤️",
    layout="centered"
)

st.title("❤️ Laboratório do Amor")
st.caption("Sentir → compreender → escolher → agir")

st.markdown(
    """
Este aplicativo acompanha o **Manual Prático do Amor** com **narração guiada pelo navegador** e experiências sonoras:

1. **Amor em DEUS e gratidão** — desacelerar, respirar, recordar o bem recebido e transformar o sentimento em pensamento e ação.
2. **Amor ao Próximo e Empatia** — sentir boa vontade pelo outro, compreender sua experiência e transformar esse Amor em presença e ação concreta.
3. **Anseio e propósito** — sentir um desejo significativo, conectá-lo ao Amor, formar uma visão e transformá-la em direção e ação.
4. **Integração Noturna — 1 hora** — encerrar a jornada com o protocolo híbrido monaural + isocrônico de 6 Hz para 2,5 Hz.

> O objetivo não é “sentir a outra pessoa” nem transmitir emoções por um campo invisível.  
> É cultivar um estado interno de presença, gratidão e empatia que possa se tornar **palavra, gesto, cuidado e ação**, criando condições para que o outro também experimente acolhimento, segurança e bem-estar.
"""
)

# ============================================================
# AVISOS
# ============================================================
with st.expander("Antes de usar"):
    st.markdown(
        """
- Use volume confortável. Nunca use este áudio dirigindo ou operando máquinas.
- Ritmos binaurais exigem **fones estéreo** para que cada ouvido receba um tom diferente.
- Sons rítmicos podem ajudar algumas pessoas a relaxar ou concentrar-se, mas os efeitos variam e não constituem tratamento médico.
- “Coerência” aqui significa principalmente **respiração lenta, atenção e regulação cardiorrespiratória**.
- O coração gera atividade elétrica e magnética mensurável, mas não há evidência estabelecida de que sentimentos sejam transmitidos entre pessoas por esse campo.
- Depressão e ansiedade são condições multifatoriais. Amor, vínculo, espiritualidade e apoio social podem ajudar no bem-estar, mas não substituem cuidado profissional quando necessário.
"""
    )

# ============================================================
# FUNÇÕES DE ÁUDIO
# ============================================================
def _fade_envelope(global_start, n, total_samples, sample_rate, fade_seconds):
    """Envelope de fade in/out calculado apenas para o bloco atual."""
    idx = np.arange(global_start, global_start + n, dtype=np.int64)
    env = np.ones(n, dtype=np.float32)
    fade_samples = max(1, int(sample_rate * fade_seconds))

    mask_in = idx < fade_samples
    if np.any(mask_in):
        env[mask_in] = idx[mask_in] / fade_samples

    mask_out = idx >= (total_samples - fade_samples)
    if np.any(mask_out):
        env[mask_out] = np.minimum(
            env[mask_out],
            (total_samples - 1 - idx[mask_out]) / fade_samples
        )

    return np.clip(env, 0.0, 1.0)


def _soft_chime(t, sample_rate, start_s, duration=0.8, freq=660.0, amp=0.12):
    """Pequeno marcador sonoro suave dentro de um bloco."""
    local_t = t - start_s
    mask = (local_t >= 0) & (local_t < duration)
    if not np.any(mask):
        return np.zeros_like(t, dtype=np.float32)

    out = np.zeros_like(t, dtype=np.float32)
    x = local_t[mask]
    env = np.exp(-4.0 * x / duration).astype(np.float32)
    out[mask] = (amp * np.sin(2 * np.pi * freq * x) * env).astype(np.float32)
    return out


def gerar_binaural_amor(
    duracao_min=12,
    sample_rate=22050,
    base_freq=150.0,
    volume=0.28,
    chunk_seconds=20
):
    """
    Protocolo:
      0–2 min   : respiração / presença — diferença 8 Hz
      2–7 min   : gratidão / Amor em DEUS — diferença 10 Hz
      7–10 min  : empatia — diferença 10 Hz
      10–12 min : intenção / ação — transição 10 -> 20 Hz

    As durações são escaladas proporcionalmente se o usuário escolher
    uma duração diferente de 12 minutos.
    """
    total_s = float(duracao_min * 60)
    total_samples = int(sample_rate * total_s)
    chunk_samples = int(sample_rate * chunk_seconds)

    # Pontos proporcionais do protocolo-base de 12 min
    p1 = total_s * (2 / 12)
    p2 = total_s * (7 / 12)
    p3 = total_s * (10 / 12)

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        phase_l = 0.0
        phase_r = 0.0

        for start in range(0, total_samples, chunk_samples):
            end = min(start + chunk_samples, total_samples)
            n = end - start

            absolute_t = np.arange(start, end, dtype=np.float64) / sample_rate

            beat = np.empty(n, dtype=np.float32)
            beat[absolute_t < p1] = 8.0
            beat[(absolute_t >= p1) & (absolute_t < p3)] = 10.0

            final_mask = absolute_t >= p3
            if np.any(final_mask):
                frac = np.clip((absolute_t[final_mask] - p3) / max(total_s - p3, 1e-9), 0, 1)
                beat[final_mask] = (10.0 + 10.0 * frac).astype(np.float32)

            freq_l = np.full(n, base_freq, dtype=np.float32)
            freq_r = base_freq + beat

            # Fase contínua entre blocos
            inc_l = 2 * np.pi * freq_l / sample_rate
            inc_r = 2 * np.pi * freq_r / sample_rate

            ph_l = phase_l + np.cumsum(inc_l, dtype=np.float64)
            ph_r = phase_r + np.cumsum(inc_r, dtype=np.float64)
            phase_l = float(ph_l[-1] % (2 * np.pi))
            phase_r = float(ph_r[-1] % (2 * np.pi))

            left = np.sin(ph_l).astype(np.float32)
            right = np.sin(ph_r).astype(np.float32)

            env = _fade_envelope(start, n, total_samples, sample_rate, 3.0)
            left *= env * volume
            right *= env * volume

            # Marcadores suaves nas mudanças de etapa
            for marker in (p1, p2, p3):
                chime = _soft_chime(absolute_t, sample_rate, marker, duration=0.8, freq=660.0)
                left += chime
                right += chime

            stereo = np.column_stack((left, right))
            pcm = np.clip(stereo, -1.0, 1.0)
            pcm = (pcm * 32767).astype("<i2")
            wf.writeframes(pcm.tobytes())

    return buffer.getvalue()


def gerar_relaxamento_noturno(
    duracao_min=30,
    sample_rate=11025,
    base_freq=100.0,
    volume=0.22,
    chunk_seconds=30
):
    """
    Áudio mono de relaxamento:
      primeira metade: modulação lenta ~6 Hz
      segunda metade: transição gradual até ~2.5 Hz

    Não é apresentado como indutor garantido de estados cerebrais.
    """
    total_s = float(duracao_min * 60)
    total_samples = int(sample_rate * total_s)
    chunk_samples = int(sample_rate * chunk_seconds)
    midpoint = total_s / 2
    transition = min(60.0, total_s * 0.12)
    t1 = midpoint - transition / 2
    t2 = midpoint + transition / 2

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        phase_carrier = 0.0
        phase_mod = 0.0

        for start in range(0, total_samples, chunk_samples):
            end = min(start + chunk_samples, total_samples)
            n = end - start
            absolute_t = np.arange(start, end, dtype=np.float64) / sample_rate

            pulse = np.empty(n, dtype=np.float32)
            pulse[absolute_t < t1] = 6.0

            trans_mask = (absolute_t >= t1) & (absolute_t < t2)
            if np.any(trans_mask):
                frac = (absolute_t[trans_mask] - t1) / max(t2 - t1, 1e-9)
                pulse[trans_mask] = (6.0 + (2.5 - 6.0) * frac).astype(np.float32)

            pulse[absolute_t >= t2] = 2.5

            inc_carrier = np.full(n, 2 * np.pi * base_freq / sample_rate, dtype=np.float32)
            inc_mod = 2 * np.pi * pulse / sample_rate

            ph_c = phase_carrier + np.cumsum(inc_carrier, dtype=np.float64)
            ph_m = phase_mod + np.cumsum(inc_mod, dtype=np.float64)

            phase_carrier = float(ph_c[-1] % (2 * np.pi))
            phase_mod = float(ph_m[-1] % (2 * np.pi))

            carrier = np.sin(ph_c).astype(np.float32)

            # Modulação suave 0..1, evitando pulsos agressivos
            modulation = (0.35 + 0.65 * (0.5 + 0.5 * np.sin(ph_m))).astype(np.float32)
            audio = carrier * modulation * volume

            env = _fade_envelope(start, n, total_samples, sample_rate, 8.0)
            audio *= env

            pcm = np.clip(audio, -1.0, 1.0)
            pcm = (pcm * 32767).astype("<i2")
            wf.writeframes(pcm.tobytes())

    return buffer.getvalue()




def gerar_hibrido_noturno_1h(
    sample_rate=11025,
    base_freq=100.0,
    volume=0.24,
    chunk_seconds=30
):
    """
    Protocolo noturno fixo de 1 hora:
      - 0–29:30       : pulso/modulação em 6 Hz
      - 29:30–30:30   : transição suave de 6 Hz para 2,5 Hz
      - 30:30–60:00   : pulso/modulação em 2,5 Hz

    Combina:
      1) batimento monaural: mistura de dois tons próximos;
      2) modulação isocrônica: variação rítmica de amplitude.

    O arquivo é escrito em blocos diretamente no WAV em memória,
    evitando manter uma hora inteira de arrays numpy simultaneamente.

    Observação: os rótulos "Teta" e "Delta" descrevem as frequências
    de modulação usadas no áudio; não significam que o aplicativo
    garanta a indução de um estado cerebral específico.
    """
    total_s = 60 * 60
    theta_s = 30 * 60
    transition_s = 60

    t1 = theta_s - transition_s / 2   # 29:30
    t2 = theta_s + transition_s / 2   # 30:30

    total_samples = int(sample_rate * total_s)
    chunk_samples = int(sample_rate * chunk_seconds)

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        phase_base = 0.0
        phase_offset = 0.0
        phase_iso = 0.0

        for start in range(0, total_samples, chunk_samples):
            end = min(start + chunk_samples, total_samples)
            n = end - start
            absolute_t = np.arange(start, end, dtype=np.float64) / sample_rate

            pulse = np.empty(n, dtype=np.float32)

            before = absolute_t < t1
            trans = (absolute_t >= t1) & (absolute_t < t2)
            after = absolute_t >= t2

            pulse[before] = 6.0

            if np.any(trans):
                frac = (absolute_t[trans] - t1) / (t2 - t1)
                pulse[trans] = (6.0 + (2.5 - 6.0) * frac).astype(np.float32)

            pulse[after] = 2.5

            # ------------------------------------------------
            # BATIMENTO MONAURAL
            # tom 1: frequência base
            # tom 2: frequência base + frequência de batimento
            # ------------------------------------------------
            inc_base = np.full(
                n,
                2 * np.pi * base_freq / sample_rate,
                dtype=np.float32
            )
            inc_offset = 2 * np.pi * (base_freq + pulse) / sample_rate

            ph1 = phase_base + np.cumsum(inc_base, dtype=np.float64)
            ph2 = phase_offset + np.cumsum(inc_offset, dtype=np.float64)

            phase_base = float(ph1[-1] % (2 * np.pi))
            phase_offset = float(ph2[-1] % (2 * np.pi))

            onda1 = np.sin(ph1).astype(np.float32)
            onda2 = np.sin(ph2).astype(np.float32)
            monaural = (onda1 + onda2) * 0.5

            # ------------------------------------------------
            # MODULAÇÃO ISOCRÔNICA
            # sin² produz pulsação de amplitude suave e positiva
            # ------------------------------------------------
            inc_iso = 2 * np.pi * pulse / sample_rate
            ph_iso = phase_iso + np.cumsum(inc_iso, dtype=np.float64)
            phase_iso = float(ph_iso[-1] % (2 * np.pi))

            iso = (np.sin(ph_iso) ** 2).astype(np.float32)

            # Evita "cortar" completamente o som em cada pulso:
            # 18% de piso + 82% de modulação.
            mod = (0.18 + 0.82 * iso).astype(np.float32)

            audio = monaural * mod * volume

            # Fade-in inicial de 8 s e fade-out final de 15 s.
            env = np.ones(n, dtype=np.float32)
            idx = np.arange(start, end, dtype=np.int64)

            fade_in = int(sample_rate * 8)
            m_in = idx < fade_in
            if np.any(m_in):
                env[m_in] *= (idx[m_in] / max(fade_in, 1)).astype(np.float32)

            fade_out = int(sample_rate * 15)
            m_out = idx >= total_samples - fade_out
            if np.any(m_out):
                remaining = (total_samples - 1 - idx[m_out]) / max(fade_out, 1)
                env[m_out] *= np.clip(remaining, 0.0, 1.0).astype(np.float32)

            audio *= env

            pcm = np.clip(audio, -1.0, 1.0)
            pcm = (pcm * 32767).astype("<i2")
            wf.writeframes(pcm.tobytes())

    return buffer.getvalue()

# ============================================================
# NARRADOR PELO NAVEGADOR (SEM API EXTERNA)
# ============================================================
def narrador_browser(titulo, segmentos, rate=0.88, volume=1.0, pausa_ms=2200, altura=190):
    """
    Usa Web Speech API do navegador.
    O usuário aciona a voz diretamente no componente, evitando bloqueios de autoplay.
    Procura uma voz pt-BR; se não houver, usa pt-PT ou a voz padrão do navegador.
    """
    payload = json.dumps(segmentos, ensure_ascii=False)
    titulo_js = json.dumps(titulo, ensure_ascii=False)

    html = f"""
    <div style="
        font-family: Arial, sans-serif;
        padding: 14px;
        border: 1px solid rgba(128,128,128,.30);
        border-radius: 12px;
        background: rgba(128,128,128,.05);
    ">
      <div style="font-weight:700; margin-bottom:10px;">🎙️ {titulo}</div>

      <div style="display:flex; gap:8px; flex-wrap:wrap;">
        <button onclick="startNarration()" style="padding:8px 12px; cursor:pointer;">▶️ Iniciar</button>
        <button onclick="pauseNarration()" style="padding:8px 12px; cursor:pointer;">⏸️ Pausar</button>
        <button onclick="resumeNarration()" style="padding:8px 12px; cursor:pointer;">⏯️ Continuar</button>
        <button onclick="stopNarration()" style="padding:8px 12px; cursor:pointer;">⏹️ Parar</button>
      </div>

      <div id="status" style="margin-top:10px; font-size:13px; opacity:.8;">
        Toque em “Iniciar” para ouvir a prática guiada.
      </div>
    </div>

    <script>
      const segmentos = {payload};
      const titulo = {titulo_js};
      const rate = {float(rate)};
      const volume = {float(volume)};
      const pausa = {int(pausa_ms)};

      let index = 0;
      let stopped = false;
      let timer = null;

      function getVoice() {{
        const voices = window.speechSynthesis.getVoices();
        return (
          voices.find(v => (v.lang || '').toLowerCase() === 'pt-br') ||
          voices.find(v => (v.lang || '').toLowerCase().startsWith('pt-br')) ||
          voices.find(v => (v.lang || '').toLowerCase().startsWith('pt')) ||
          voices[0] ||
          null
        );
      }}

      function updateStatus(msg) {{
        document.getElementById("status").innerText = msg;
      }}

      function speakNext() {{
        if (stopped || index >= segmentos.length) {{
          if (!stopped) updateStatus("✅ Prática narrada concluída.");
          return;
        }}

        const texto = segmentos[index];
        const u = new SpeechSynthesisUtterance(texto);
        const voice = getVoice();
        if (voice) u.voice = voice;
        u.lang = voice?.lang || "pt-BR";
        u.rate = rate;
        u.volume = volume;
        u.pitch = 1.0;

        updateStatus(`🎧 Etapa ${{index + 1}} de ${{segmentos.length}}`);

        u.onend = function() {{
          index += 1;
          if (!stopped) {{
            timer = setTimeout(speakNext, pausa);
          }}
        }};

        u.onerror = function(e) {{
          updateStatus("Não foi possível usar a voz do navegador neste dispositivo.");
        }};

        window.speechSynthesis.speak(u);
      }}

      function startNarration() {{
        stopNarration();
        stopped = false;
        index = 0;

        // Alguns navegadores carregam a lista de vozes só após a primeira interação.
        window.speechSynthesis.getVoices();
        updateStatus("🎙️ Iniciando " + titulo + "...");
        speakNext();
      }}

      function pauseNarration() {{
        if (window.speechSynthesis.speaking) {{
          window.speechSynthesis.pause();
          updateStatus("⏸️ Narração pausada.");
        }}
      }}

      function resumeNarration() {{
        if (window.speechSynthesis.paused) {{
          window.speechSynthesis.resume();
          updateStatus("▶️ Narração retomada.");
        }}
      }}

      function stopNarration() {{
        stopped = true;
        if (timer) clearTimeout(timer);
        window.speechSynthesis.cancel();
        updateStatus("⏹️ Narração parada.");
      }}

      window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();
    </script>
    """
    components.html(html, height=altura)


ROTEIRO_AMOR_DEUS = [
    "Encontre uma posição confortável. Se puder, coloque uma das mãos sobre o coração.",
    "Feche os olhos, se isso for confortável para você. Inspire suavemente pelo nariz e expire devagar.",
    "Não tente fabricar nenhuma emoção. Apenas desacelere e perceba que você está vivo, aqui e agora.",
    "Agora recorde algo concreto pelo qual você é profundamente grato a Deus.",
    "Pode ser a vida, uma pessoa, uma oportunidade, um cuidado recebido, um recomeço ou algo simples que normalmente passa despercebido.",
    "Não fique apenas na ideia. Permita que a gratidão seja sentida no corpo. Perceba o peito, a respiração, o rosto e o estado interior.",
    "Repita em silêncio: Deus, obrigado por este bem que recebi.",
    "Escolha um segundo motivo de gratidão. Depois um terceiro. Permaneça alguns instantes com cada um.",
    "Agora pergunte a si mesmo: se eu viver a partir deste Amor hoje, como meus pensamentos podem mudar?",
    "Que julgamento pode dar lugar à compreensão? Que medo pode dar lugar à confiança? Que dureza pode dar lugar à gentileza?",
    "Por fim, escolha uma ação concreta. Algo pequeno e real: agradecer, telefonar, ajudar, pedir perdão, escutar, acolher ou servir.",
    "Leve o Amor do sentimento ao pensamento, e do pensamento à ação."
]

ROTEIRO_EMPATIA = [
    "Traga à mente uma pessoa. Comece não pelo problema dela, mas pelo Amor. Reconheça que diante de você existe uma vida que possui valor, história, medos, desejos e necessidades.",
    "Respire lentamente e procure sentir boa vontade, respeito e desejo sincero de que essa pessoa esteja bem.",
    "Agora pergunte: o que eu realmente sei sobre o que essa pessoa está vivendo?",
    "Separe fatos de suposições. Amar também é não reduzir o outro às nossas interpretações.",
    "Pergunte: o que essa pessoa pode estar sentindo? E do que ela pode estar precisando?",
    "Pode ser necessidade de ser ouvida, respeitada, protegida, compreendida, ajudada, acompanhada ou simplesmente de não estar sozinha.",
    "Permita que a humanidade dessa pessoa toque o seu coração sem tomar para si todo o sofrimento dela.",
    "Empatia é a ponte. Amor ao próximo é o destino da prática.",
    "Pergunte agora: o que significa amar esta pessoa hoje?",
    "Talvez seja escutar sem interromper, oferecer ajuda, encorajar, pedir perdão, perdoar, estar presente, respeitar um limite ou simplesmente não abandonar.",
    "Imagine sua presença transmitindo calma, respeito, dignidade e cuidado.",
    "Quando possível, pergunte diretamente: como você está de verdade? Como posso ajudar?",
    "Escolha uma ação concreta. O Amor deixa de ser apenas sentimento quando se transforma em presença, palavra e atitude.",
    "Leve o Amor do coração ao pensamento, do pensamento à escolha, e da escolha ao próximo."
]

ROTEIRO_RELAXAMENTO = [
    "Este momento não exige desempenho. Apenas permita que o corpo reduza o ritmo.",
    "Inspire suavemente. Expire um pouco mais devagar.",
    "Relaxe a testa, os olhos, a mandíbula e os ombros.",
    "Recorde algo bom deste dia, por menor que tenha sido.",
    "Agradeça em silêncio.",
    "Se alguma preocupação aparecer, reconheça-a sem lutar com ela e volte à respiração.",
    "Você não precisa resolver tudo agora.",
    "Permita que este seja um tempo de repouso, confiança e entrega.",
    "Que o Amor recebido hoje se transforme em descanso para você e em cuidado para as pessoas ao seu redor."
]


def gerar_audio_intencao(
    duracao_min=10,
    sample_rate=22050,
    base_freq=110.0,
    volume=0.24,
    chunk_seconds=20
):
    """
    Paisagem sonora simbólica para acompanhar:
      0–2 min  : anseio / presença        (~8 Hz de diferença binaural)
      2–5 min  : gratidão / convicção     (~10 Hz)
      5–8 min  : visão / clareza          (10 -> 14 Hz)
      8–10 min : decisão / ação           (14 -> 18 Hz)

    O áudio NÃO é apresentado como mecanismo capaz de alterar o "destino".
    Ele funciona como suporte acústico para foco, visualização, emoção e ação.
    """
    total_s = float(duracao_min * 60)
    total_samples = int(sample_rate * total_s)
    chunk_samples = int(sample_rate * chunk_seconds)

    # Fases proporcionais ao protocolo-base de 10 min
    p1 = total_s * 0.20
    p2 = total_s * 0.50
    p3 = total_s * 0.80

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        phase_l = 0.0
        phase_r = 0.0
        phase_pad = 0.0

        for start in range(0, total_samples, chunk_samples):
            end = min(start + chunk_samples, total_samples)
            n = end - start

            absolute_t = np.arange(start, end, dtype=np.float64) / sample_rate

            beat = np.empty(n, dtype=np.float32)
            beat[absolute_t < p1] = 8.0
            beat[(absolute_t >= p1) & (absolute_t < p2)] = 10.0

            m2 = (absolute_t >= p2) & (absolute_t < p3)
            if np.any(m2):
                frac = (absolute_t[m2] - p2) / max(p3 - p2, 1e-9)
                beat[m2] = (10.0 + 4.0 * frac).astype(np.float32)

            m3 = absolute_t >= p3
            if np.any(m3):
                frac = (absolute_t[m3] - p3) / max(total_s - p3, 1e-9)
                beat[m3] = (14.0 + 4.0 * frac).astype(np.float32)

            # Portadora binaural
            freq_l = np.full(n, base_freq, dtype=np.float32)
            freq_r = base_freq + beat

            inc_l = 2 * np.pi * freq_l / sample_rate
            inc_r = 2 * np.pi * freq_r / sample_rate

            ph_l = phase_l + np.cumsum(inc_l, dtype=np.float64)
            ph_r = phase_r + np.cumsum(inc_r, dtype=np.float64)
            phase_l = float(ph_l[-1] % (2 * np.pi))
            phase_r = float(ph_r[-1] % (2 * np.pi))

            left = np.sin(ph_l).astype(np.float32)
            right = np.sin(ph_r).astype(np.float32)

            # Camada harmônica suave crescente, para representar simbolicamente
            # anseio -> clareza -> movimento.
            pad_freq = np.where(
                absolute_t < p2,
                220.0,
                np.where(absolute_t < p3, 247.0, 261.63)
            ).astype(np.float32)
            inc_pad = 2 * np.pi * pad_freq / sample_rate
            ph_pad = phase_pad + np.cumsum(inc_pad, dtype=np.float64)
            phase_pad = float(ph_pad[-1] % (2 * np.pi))
            pad = np.sin(ph_pad).astype(np.float32)

            # Crescimento muito suave do pad ao longo da sessão
            growth = (0.03 + 0.07 * (absolute_t / max(total_s, 1e-9))).astype(np.float32)

            env = _fade_envelope(start, n, total_samples, sample_rate, 4.0)
            left = (left * volume + pad * growth) * env
            right = (right * volume + pad * growth) * env

            # Sinos suaves nas transições
            for marker, freq in ((p1, 523.25), (p2, 659.25), (p3, 783.99)):
                chime = _soft_chime(
                    absolute_t,
                    sample_rate,
                    marker,
                    duration=1.2,
                    freq=freq,
                    amp=0.08
                )
                left += chime
                right += chime

            stereo = np.column_stack((left, right))
            pcm = np.clip(stereo, -1.0, 1.0)
            pcm = (pcm * 32767).astype("<i2")
            wf.writeframes(pcm.tobytes())

    return buffer.getvalue()


def roteiro_intencao_dinamico(anseio):
    desejo = (anseio or "").strip()

    if desejo:
        foco = f"Seu anseio escolhido é: {desejo}."
        imagem = f"Imagine por alguns instantes como seria viver de maneira coerente com este anseio: {desejo}."
    else:
        foco = "Escolha agora um anseio verdadeiro da sua vida. Algo que tenha significado para você."
        imagem = "Imagine por alguns instantes como seria viver de maneira coerente com esse anseio."

    return [
        "Encontre uma posição confortável e respire lentamente.",
        "Antes de pensar no futuro, volte ao presente. Perceba seu corpo, sua respiração e seu coração.",
        foco,
        "Não force uma resposta. Pergunte: por que isso é realmente importante para mim?",
        "Agora conecte esse anseio ao Amor. Se ele se realizar, como poderá produzir mais vida, cuidado, crescimento ou bem para você e para outras pessoas?",
        "Recorde algo pelo qual você já é grato. Gratidão ajuda a sair da sensação de falta e entrar em um estado de presença.",
        "Permita-se sentir esperança sem confundir esperança com certeza absoluta.",
        imagem,
        "Observe quais pensamentos surgem quando você se imagina caminhando nessa direção.",
        "Agora transforme a visão em compromisso. Qual é o menor passo real que você pode dar?",
        "Fé, aqui, não é passividade. É sustentar esperança, sentido e direção enquanto você age.",
        "Leve o anseio do coração ao pensamento, do pensamento à escolha e da escolha à ação.",
        "O futuro não precisa ser controlado neste momento. Concentre-se no próximo passo que depende de você."
    ]

# ============================================================
# GUIA PRINCIPAL
# ============================================================
with st.expander("🎙️ Configurações da voz"):
    velocidade_voz = st.slider(
        "Velocidade da narração",
        min_value=0.65,
        max_value=1.15,
        value=0.88,
        step=0.05,
        help="Valores menores deixam a voz mais contemplativa."
    )
    pausa_voz = st.slider(
        "Pausa entre trechos (segundos)",
        min_value=1.0,
        max_value=8.0,
        value=2.5,
        step=0.5
    )
    st.caption(
        "A voz é fornecida pelo próprio navegador/dispositivo. "
        "A qualidade e o timbre podem variar entre celular, computador e navegador."
    )

tab1, tab2, tab3, tab4 = st.tabs(
    ["❤️ Amor em DEUS", "🤝 Amor ao Próximo", "✨ Anseio e Propósito", "🌙 Integração 1h"]
)

# ------------------------------------------------------------
# TAB 1
# ------------------------------------------------------------
with tab1:
    st.subheader("1. Volta ao Amor Principal")
    st.markdown(
        """
**Propósito:** começar no coração, não na obrigação.

Durante a prática:

**0–2 min — Presença**  
Respire devagar. Não force sentimento algum. Apenas perceba que você está vivo.

**2–7 min — Gratidão**  
Recorde, uma a uma, coisas concretas pelas quais você agradece a DEUS: vida, pessoas, oportunidades, aprendizados, proteção, alimento, natureza, perdão, recomeços.

**7–10 min — Deixar o sentimento chegar ao pensamento**  
Pergunte: *“Se eu realmente viver a partir deste Amor, o que muda na maneira como penso hoje?”*

**10–12 min — Transformar em ação**  
Escolha uma atitude concreta que expresse o Amor recebido.
"""
    )

    st.markdown("#### 🎙️ Prática guiada")
    narrador_browser(
        "Amor em DEUS e Gratidão",
        ROTEIRO_AMOR_DEUS,
        rate=velocidade_voz,
        pausa_ms=int(pausa_voz * 1000)
    )

    st.caption(
        "Você pode iniciar a narração e, em seguida, tocar o áudio binaural abaixo em volume baixo, "
        "se desejar usar os dois juntos."
    )

    dur1 = st.select_slider(
        "Duração da prática",
        options=[6, 8, 10, 12, 15, 20],
        value=12,
        key="dur_amor"
    )

    if st.button("Gerar áudio: Amor em DEUS", type="primary", use_container_width=True):
        with st.spinner("Gerando o áudio..."):
            audio = gerar_binaural_amor(duracao_min=dur1)
        st.session_state["audio_amor"] = audio

    if "audio_amor" in st.session_state:
        st.audio(st.session_state["audio_amor"], format="audio/wav")
        st.download_button(
            "Baixar áudio",
            data=st.session_state["audio_amor"],
            file_name=f"amor_em_deus_{dur1}min.wav",
            mime="audio/wav",
            use_container_width=True
        )

    st.markdown("#### Depois do áudio")
    gratidao = st.text_area(
        "Por quais 3 coisas você agradece hoje?",
        placeholder="1. ...\n2. ...\n3. ...",
        key="gratidao"
    )
    acao_deus = st.text_input(
        "Que ação concreta nascerá desse sentimento?",
        placeholder="Ex.: telefonar para alguém, pedir perdão, ajudar, agradecer...",
        key="acao_deus"
    )

# ------------------------------------------------------------
# TAB 2
# ------------------------------------------------------------
with tab2:
    st.subheader("2. Amor ao Próximo: sentir empatia e transformar em Amor")
    st.markdown(
        """
Aqui o objetivo não é apenas compreender a pessoa. É **amar o próximo**.

A **empatia** é uma ponte: ajuda você a reconhecer a humanidade do outro, considerar o que ele pode estar vivendo e abrir o coração para uma resposta de Amor.

O movimento desta etapa é:

### AMOR → EMPATIA → COMPREENSÃO → PENSAMENTO → ESCOLHA → AÇÃO → BEM-ESTAR DO OUTRO

Amar o próximo significa desejar e favorecer o bem da outra pessoa — com presença, escuta, respeito, palavras, ajuda concreta, perdão quando possível e limites quando necessários.

### Prática
1. Traga uma pessoa à mente.
2. Respire lentamente e procure sentir Amor e boa vontade por ela.
3. Pergunte: **“O que essa pessoa pode estar vivendo?”**
4. Pergunte: **“Do que ela pode estar precisando?”**
5. Evite presumir que você sabe exatamente o que ela sente.
6. Imagine-se escutando sem julgar e sem tentar controlar.
7. Pergunte: **“O que significa amar esta pessoa hoje?”**
8. Escolha um gesto real de cuidado.
9. Transforme o Amor sentido em uma ação que possa favorecer acolhimento, segurança, dignidade e bem-estar.
"""
    )

    st.markdown("#### 🎙️ Prática guiada de Amor ao Próximo e Empatia")
    narrador_browser(
        "Amor ao Próximo e Empatia",
        ROTEIRO_EMPATIA,
        rate=velocidade_voz,
        pausa_ms=int(pausa_voz * 1000)
    )

    pessoa = st.text_input(
        "Pessoa em quem você deseja concentrar a prática",
        placeholder="Nome ou apenas 'uma pessoa da família', 'um colega'...",
        key="pessoa"
    )

    situacao = st.text_area(
        "O que você sabe — sem adivinhar — sobre o que essa pessoa está vivendo?",
        key="situacao"
    )

    necessidade = st.text_area(
        "Que necessidade humana pode estar presente?",
        placeholder="Ex.: ser ouvida, sentir segurança, receber ajuda prática, descanso, respeito...",
        key="necessidade"
    )

    acao_empatia = st.text_input(
        "Qual ação concreta pode expressar Amor ao próximo?",
        placeholder="Ex.: escutar 10 minutos sem interromper; oferecer ajuda específica...",
        key="acao_empatia"
    )

    st.info(
        "Empatia não é leitura da mente. Quando possível, confirme com a própria pessoa: "
        "“É isso que você está sentindo?” ou “Como posso ajudar de verdade?”"
    )

# ------------------------------------------------------------
# TAB 3
# ------------------------------------------------------------
with tab3:
    st.subheader("3. Anseio, Propósito e Direção")
    st.markdown(
        """
Esta prática trabalha o movimento:

### ANSEIO → SENTIMENTO → PENSAMENTO → VISÃO → ESCOLHA → AÇÃO

Você pode trazer algo que deseja profundamente para sua vida: reconciliação, saúde, trabalho, um projeto, uma mudança, uma relação melhor, crescimento espiritual ou outro propósito significativo.

A prática usa **voz + paisagem sonora** para ajudar você a sustentar atenção, gratidão, esperança e clareza.

> A expressão “energia no destino” pode ser usada aqui como **metáfora para a força psicológica e espiritual de uma intenção sentida e sustentada**.  
> O áudio não é apresentado como prova de que ondas sonoras ou campos do coração alterem fisicamente acontecimentos futuros.
"""
    )

    anseio = st.text_area(
        "Qual é o seu anseio neste momento?",
        placeholder="Ex.: construir uma relação mais amorosa com minha família; realizar um projeto; encontrar um trabalho com propósito...",
        key="anseio"
    )

    sentido_anseio = st.text_area(
        "Por que isso é importante para você?",
        placeholder="O que esse anseio representa em termos de Amor, vida, crescimento ou contribuição?",
        key="sentido_anseio"
    )

    st.markdown("#### 🎙️ Narração do anseio")
    narrador_browser(
        "Anseio, Fé, Visão e Ação",
        roteiro_intencao_dinamico(anseio),
        rate=max(0.72, velocidade_voz - 0.03),
        pausa_ms=int(max(3.0, pausa_voz) * 1000),
        altura=195
    )

    st.markdown("#### 🎧 Paisagem sonora do propósito")
    st.caption(
        "Use fones de ouvido se desejar perceber a diferença binaural. "
        "O desenho sonoro cresce suavemente do anseio para clareza e ação."
    )

    dur_intencao = st.select_slider(
        "Duração da prática de intenção",
        options=[6, 8, 10, 12, 15],
        value=10,
        key="dur_intencao"
    )

    if st.button("Gerar áudio: Anseio e Propósito", use_container_width=True):
        with st.spinner("Gerando a paisagem sonora..."):
            audio_intencao = gerar_audio_intencao(duracao_min=dur_intencao)
        st.session_state["audio_intencao"] = audio_intencao

    if "audio_intencao" in st.session_state:
        st.audio(st.session_state["audio_intencao"], format="audio/wav")
        st.download_button(
            "Baixar áudio de Anseio e Propósito",
            data=st.session_state["audio_intencao"],
            file_name=f"anseio_proposito_{dur_intencao}min.wav",
            mime="audio/wav",
            use_container_width=True
        )

    st.markdown("#### Transforme a energia interior em direção")
    visao = st.text_area(
        "Se esse anseio avançar, o que muda concretamente na sua vida?",
        key="visao_anseio"
    )

    proximo_passo = st.text_input(
        "Qual é o próximo passo real que depende de você?",
        placeholder="Uma ligação, uma conversa, estudar, escrever, procurar ajuda, iniciar uma tarefa...",
        key="proximo_passo_anseio"
    )

    obstaculo = st.text_input(
        "Qual obstáculo você precisa reconhecer sem negar a realidade?",
        placeholder="Ex.: medo, falta de informação, tempo, recursos, conversa difícil...",
        key="obstaculo_anseio"
    )

    st.success(
        "A prática termina com ação: sentir e visualizar podem organizar atenção e motivação, "
        "mas o passo concreto conecta o propósito à vida real."
    )


# ------------------------------------------------------------
# TAB 4 — ÚLTIMA ETAPA
# ------------------------------------------------------------
with tab4:
    st.subheader("4. Integração Noturna — 1 Hora")
    st.markdown(
        """
Esta é a **última etapa da jornada**.

Depois de trabalhar **Amor em DEUS**, **Amor ao Próximo** e **Anseio/Propósito**, esta faixa encerra a experiência com **1 hora de som híbrido monaural + isocrônico** em volume baixo.

### Estrutura fixa da hora
- **Primeiros 29 min 30 s:** modulação em **6 Hz**
- **60 s de transição:** de **6 Hz para 2,5 Hz**
- **Últimos 29 min 30 s:** modulação em **2,5 Hz**

O desenho sonoro combina dois mecanismos acústicos:

**Monaural:** dois tons próximos são misturados no mesmo sinal, produzindo uma pulsação acústica pela diferença entre as frequências.

**Isocrônico:** a amplitude do som é modulada ritmicamente na frequência escolhida.

> No aplicativo, “Teta” e “Delta” identificam as frequências de modulação do protocolo.  
> O áudio pode ser usado como apoio para relaxamento e preparação para o sono, mas não garante a indução de um estado cerebral específico.
"""
    )

    st.warning(
        "Use em volume baixo e nunca enquanto dirige ou realiza atividade que exija atenção. "
        "Se o som causar desconforto, interrompa o uso."
    )

    st.markdown("#### 🎙️ Preparação guiada")
    narrador_browser(
        "Preparação para a Integração Noturna",
        ROTEIRO_RELAXAMENTO,
        rate=max(0.70, velocidade_voz - 0.05),
        pausa_ms=int(max(3.0, pausa_voz) * 1000),
        altura=195
    )

    st.caption(
        "Ouça primeiro a preparação guiada. Depois inicie a faixa de 1 hora. "
        "Alto-falante é suficiente para este modo, pois o áudio final é mono."
    )

    if st.button(
        "Gerar Áudio Noturno — 1 Hora Monaural + Isocrônico",
        type="primary",
        use_container_width=True
    ):
        with st.spinner(
            "Gerando 1 hora de áudio em blocos para reduzir o uso de memória..."
        ):
            audio_hibrido = gerar_hibrido_noturno_1h()
        st.session_state["audio_hibrido_1h"] = audio_hibrido
        st.success("Áudio noturno de 1 hora pronto.")

    if "audio_hibrido_1h" in st.session_state:
        st.audio(
            st.session_state["audio_hibrido_1h"],
            format="audio/wav"
        )
        st.download_button(
            "Baixar áudio noturno de 1 hora",
            data=st.session_state["audio_hibrido_1h"],
            file_name="integracao_noturna_1h_monaural_isocronico.wav",
            mime="audio/wav",
            use_container_width=True
        )

    st.markdown(
        """
### Encerramento da jornada
**Amor recebido → Amor ao próximo → propósito → descanso e integração.**

Ao terminar, não é necessário produzir nenhum pensamento adicional.  
A proposta desta última etapa é simplesmente **desacelerar e repousar**.
"""
    )


# ============================================================
# CICLO COMPLETO DO MANUAL
# ============================================================
st.divider()
st.subheader("O ciclo do Manual")

st.markdown(
    """
### DEUS → coração → Amor → empatia → compreensão → pensamento → escolha → ação → próximo → acolhimento → comunidade → paz

O teste da prática não é apenas **“o que eu senti?”**, mas também:

- O que esse sentimento mudou no meu pensamento?
- O que mudou na maneira como enxerguei outra pessoa?
- Que ação concreta nasceu disso?
- Minha presença aumentou ou diminuiu o medo, a tensão e a solidão ao meu redor?
"""
)

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Hoje eu recebi")
    recebido = st.text_area(
        "O que você sentiu ou reconheceu como Amor?",
        key="recebido"
    )

with col2:
    st.markdown("#### Hoje eu entregarei")
    entregue = st.text_area(
        "Como esse Amor chegará a alguém por meio de você?",
        key="entregue"
    )

# ============================================================
# REGISTRO DA SESSÃO
# ============================================================
st.divider()
st.subheader("Registro da sessão")

if st.button("Preparar resumo da prática", use_container_width=True):
    resumo = f"""MANUAL PRÁTICO DO AMOR — REGISTRO DA SESSÃO

GRATIDÃO
{st.session_state.get("gratidao", "")}

AÇÃO NASCIDA DO AMOR EM DEUS
{st.session_state.get("acao_deus", "")}

PESSOA / FOCO DE EMPATIA
{st.session_state.get("pessoa", "")}

O QUE SEI SOBRE A SITUAÇÃO
{st.session_state.get("situacao", "")}

NECESSIDADE POSSÍVEL
{st.session_state.get("necessidade", "")}

AÇÃO DE EMPATIA
{st.session_state.get("acao_empatia", "")}

ANSEIO / PROPÓSITO
{st.session_state.get("anseio", "")}

POR QUE É IMPORTANTE
{st.session_state.get("sentido_anseio", "")}

VISÃO CONCRETA
{st.session_state.get("visao_anseio", "")}

PRÓXIMO PASSO
{st.session_state.get("proximo_passo_anseio", "")}

OBSTÁCULO RECONHECIDO
{st.session_state.get("obstaculo_anseio", "")}

O QUE RECEBI
{st.session_state.get("recebido", "")}

O QUE ENTREGAREI
{st.session_state.get("entregue", "")}
"""
    st.session_state["resumo_pratica"] = resumo

if "resumo_pratica" in st.session_state:
    st.code(st.session_state["resumo_pratica"], language=None)
    st.download_button(
        "Baixar registro em TXT",
        data=st.session_state["resumo_pratica"].encode("utf-8"),
        file_name="registro_manual_do_amor.txt",
        mime="text/plain",
        use_container_width=True
    )

st.divider()
st.caption(
    "Laboratório do Amor — ferramenta de contemplação, gratidão, empatia e ação. "
    "Não é dispositivo médico nem promessa de indução de estados cerebrais específicos."
)
