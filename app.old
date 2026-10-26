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
        
        # Otimização: Forçando float32 reduz o uso de RAM pela metade
        t = np.linspace(0, t_total, int(taxa * t_total), endpoint=False, dtype=np.float32)
        som_esq = np.sin(2 * np.pi * f_base * t).astype(np.float32)
        
        freqs_dir = np.zeros_like(t, dtype=np.float32)
        idx1 = int(taxa * (t_alfa - t_trans / 2))
        idx2 = int(taxa * (t_alfa + t_trans / 2))
        freqs_dir[:idx1] = f_base + 10.0
        freqs_dir[idx1:idx2] = np.linspace(f_base + 10.0, f_base + 40.0, idx2 - idx1, dtype=np.float32)
        freqs_dir[idx2:] = f_base + 40.0
        
        fase_dir = 2 * np.pi * np.cumsum(freqs_dir) / taxa
        del freqs_dir  # Libera memória imediatamente
        
        som_dir = np.sin(fase_dir).astype(np.float32)
        del fase_dir
        
        env = np.ones_like(t, dtype=np.float32)
        samples_fade = int(taxa * 3)
        env[:samples_fade] = np.linspace(0, 1, samples_fade, dtype=np.float32)
        env[-samples_fade:] = np.linspace(1, 0, samples_fade, dtype=np.float32)
        
        audio = np.vstack((som_esq * env, som_dir * env)).T
        del som_esq, som_dir, env, t
        
        audio_16 = (audio * 32767).astype(np.int16)
        del audio
        
        bytes_io = io.BytesIO()
        wavfile.write(bytes_io, taxa, audio_16)
        del audio_16
        
        st.success("Áudio de Disparo Pronto!")
        st.audio(bytes_io.getvalue(), format="audio/wav")

st.markdown("---")

# ==========================================
# FASE 2: PROTOCOLO NOTURNO (HÍBRIDO MONAURAL + ISOCRÔNICO) - ULTRA OTIMIZADO
# ==========================================
st.header("2. Fase Passiva: Incubação de Sono (Híbrido)")
st.write("Escute no **alto-falante do celular** com volume baixo (10% a 20%). 30 min em Teta e 30 min em Delta para desligar o ego e processar o destino.")

if st.button("Gerar Áudio de Sono (1 Hora Híbrido)"):
    with st.spinner("Processando áudio por blocos para proteger a memória RAM..."):
        taxa = 11025
        f_base = 100.0
        t_theta, t_delta, t_trans = 30 * 60, 30 * 60, 60
        t_total = t_theta + t_delta
        
        # Tamanho do bloco para geração: 1 minuto por vez para gastar pouquíssima RAM
        tamanho_bloco = taxa * 60  
        total_samples = int(taxa * t_total)
        
        idx1 = int(taxa * (t_theta - t_trans / 2))
        idx2 = int(taxa * (t_theta + t_trans / 2))
        
        chunks = []
        fase_acumulada_onda2 = 0.0
        fase_acumulada_iso = 0.0
        
        # Gerando o áudio em partes pequenas
        for i in range(0, total_samples, tamanho_bloco):
            fim = min(i + tamanho_bloco, total_samples)
            t_chunk = np.arange(i, fim, dtype=np.float32) / taxa
            
            # Frequência de pulso para este pedaço
            freqs_p = np.zeros(fim - i, dtype=np.float32)
            # Mapeamento dos índices globais dentro do bloco atual
            g_idx = np.arange(i, fim)
            freqs_p[g_idx < idx1] = 6.0
            mask_trans = (g_idx >= idx1) & (g_idx < idx2)
            if np.any(mask_trans):
                freqs_p[mask_trans] = np.linspace(6.0, 2.5, idx2 - idx1, dtype=np.float32)[g_idx[mask_trans] - idx1]
            freqs_p[g_idx >= idx2] = 2.5
            
            # Tom Monaural
            onda1 = np.sin(2 * np.pi * f_base * t_chunk)
            
            fase_onda2 = fase_acumulada_onda2 + 2 * np.pi * np.cumsum(f_base + freqs_p) / taxa
            if len(fase_onda2) > 0:
                fase_acumulada_onda2 = fase_onda2[-1]
            onda2 = np.sin(fase_onda2)
            
            som_monaural = (onda1 + onda2) / 2
            
            # Modulação Isocrônica
            fase_iso = fase_acumulada_iso + 2 * np.pi * np.cumsum(freqs_p) / taxa
            if len(fase_iso) > 0:
                fase_acumulada_iso = fase_iso[-1]
            mod_iso = np.sin(fase_iso) ** 2
            
            som_chunk = som_monaural * mod_iso
            
            # Aplica fade out final se for o último bloco
            if fim == total_samples:
                samples_fade = int(taxa * 15)
                if len(som_chunk) >= samples_fade:
                    som_chunk[-samples_fade:] *= np.linspace(1, 0, samples_fade, dtype=np.float32)
            
            # Converte logo para int16 para economizar 75% de espaço
            chunks.append((som_chunk * 32767).astype(np.int16))
        
        # Junta todas as pequenas partes de forma eficiente
        audio_16 = np.concatenate(chunks)
        del chunks
        
        bytes_io = io.BytesIO()
        wavfile.write(bytes_io, taxa, audio_16)
        del audio_16
        
        st.success("Áudio Híbrido Noturno de 1 Hora Pronto!")
        st.audio(bytes_io.getvalue(), format="audio/wav")
