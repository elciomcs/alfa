import streamlit as st
import numpy as np
from scipy.io import wavfile
import io

# Configuração da página do Streamlit
st.set_page_config(page_title="Laboratório Mental Quântico", page_icon="🧠", layout="centered")

st.title("🧠 Laboratório Mental - Coerência e Conexão")
st.write("Gere e toque os estímulos acústicos para o seu protocolo de 48 horas.")

# ==========================================
# FASE 1: PROTOCOLO ATIVO (BINAURAL ALFA/GAMA)
# ==========================================
st.header("1. Fase Ativa: Disparo do Laser de Gama")
st.write("Use **fones de ouvido**. Nos primeiros 7 minutos (Alfa), sintonize gratidão, amor e fé. Nos 3 minutos finais (Gama), projete a informação do pensamento na Malha.")

if st.button("Gerar Áudio de Disparo (10 min Binaural)"):
    with st.spinner("Modulando frequências Alfa e Gama..."):
        taxa = 44100
        f_base = 150.0
        t_alfa, t_gama, t_trans = 7 * 60, 3 * 60, 10
        t_total = t_alfa + t_gama
        
        t = np.linspace(0, t_total, int(taxa * t_total), endpoint=False)
        som_esq = np.sin(2 * np.pi * f_base * t)
        
        freqs_dir = np.zeros_like(t)
        idx1 = int(taxa * (t_alfa - t_trans / 2))
        idx2 = int(taxa * (t_alfa + t_trans / 2))
        
        freqs_dir[:idx1] = f_base + 10.0
        freqs_dir[idx1:idx2] = np.linspace(f_base + 10.0, f_base + 40.0, idx2 - idx1)
        freqs_dir[idx2:] = f_base + 40.0
        
        fase_dir = 2 * np.pi * np.cumsum(freqs_dir) / taxa
        som_dir = np.sin(fase_dir)
        
        # Fade inicial e final
        env = np.ones_like(t)
        samples_fade = int(taxa * 3)
        env[:samples_fade] = np.linspace(0, 1, samples_fade)
        env[-samples_fade:] = np.linspace(1, 0, samples_fade)
        
        audio = np.vstack((som_esq * env, som_dir * env)).T
        audio_16 = (audio * 32767).astype(np.int16)
        
        # Salva na memória para o Streamlit player
        bytes_io = io.BytesIO()
        wavfile.write(bytes_io, taxa, audio_16)
        
        st.success("Áudio de Disparo Pronto!")
        st.audio(bytes_io.getvalue(), format="audio/wav")

st.markdown("---")

# ==========================================
# FASE 2: PROTOCOLO NOTURNO (HÍBRIDO MONAURAL + ISOCRÔNICO)
# ==========================================
st.header("2. Fase Passiva: Incubação de Sono (Híbrido)")
st.write("Escute no **alto-falante do celular** com volume baixo (10% a 20%). 30 min em Teta e 30 min em Delta para desligar o ego e processar o destino.")

if st.button("Gerar Áudio de Sono (1 H_ora Híbrido)"):
    with st.spinner("Processando dupla modulação Teta/Delta (1 hora)..."):
        taxa = 44100
        f_base = 100.0
        t_theta, t_delta, t_trans = 30 * 60, 30 * 60, 60
        t_total = t_theta + t_delta
        
        t = np.linspace(0, t_total, int(taxa * t_total), endpoint=False)
        
        freqs_pulso = np.zeros_like(t)
        idx1 = int(taxa * (t_theta - t_trans / 2))
        idx2 = int(taxa * (t_theta + t_trans / 2))
        
        freqs_pulso[:idx1] = 6.0
        freqs_pulso[idx1:idx2] = np.linspace(6.0, 2.5, idx2 - idx1)
        freqs_pulso[idx2:] = 2.5
        
        # Tom Monaural
        onda1 = np.sin(2 * np.pi * f_base * t)
        fase_onda2 = 2 * np.pi * np.cumsum(f_base + freqs_pulso) / taxa
        onda2 = np.sin(fase_onda2)
        som_monaural = (onda1 + onda2) / 2
        
        # Modulação Isocrônica
        fase_iso = 2 * np.pi * np.cumsum(freqs_pulso) / taxa
        mod_iso = np.sin(fase_iso) ** 2
        
        som_final = som_monaural * mod_iso
        
        # Fade out final
        samples_fade = int(taxa * 15)
        som_final[-samples_fade:] *= np.linspace(1, 0, samples_fade)
        
        audio_16 = (som_final * 32767).astype(np.int16)
        
        bytes_io = io.BytesIO()
        wavfile.write(bytes_io, taxa, audio_16)
        
        st.success("Áudio Híbrido Noturno Pronto!")
        st.audio(bytes_io.getvalue(), format="audio/wav")
