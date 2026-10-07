import numpy as np
import streamlit as st
try:
    from scipy.io import wavfile
except ImportError:
    st.error("A biblioteca 'scipy' não foi encontrada. Instale-a adicionando 'scipy' ao seu requirements.txt.")
    raise

def gerar_sinal_parceria_industrial(filename="parceria_ceitec_ecomcs.wav"):
    taxa_amostragem = 44100  # 44.1 kHz
    
    # Roteiro: Estruturação Física do Silício -> Alinhamento Comercial -> Expansão Global
    fases = [
        {"tempo": 120, "base_inicio": 288, "base_fim": 288, "alvo_inicio": 15, "alvo_fim": 11},  
        {"tempo": 180, "base_inicio": 288, "base_fim": 288, "alvo_inicio": 11, "alvo_fim": 7},   
        {"tempo": 300, "base_inicio": 288, "base_fim": 288, "alvo_inicio": 7,  "alvo_fim": 2},   
        {"tempo": 300, "base_inicio": 288, "base_fim": 288, "alvo_inicio": 2,  "alvo_fim": 40}   
    ]
    
    audio_esquerdo_total = []
    audio_direito_total = []
    
    for i, fase in enumerate(fases):
        num_amostras = int(taxa_amostragem * fase["tempo"])
        
        freq_base = np.linspace(fase["base_inicio"], fase["base_fim"], num_amostras)
        freq_alvo = np.linspace(fase["alvo_inicio"], fase["alvo_fim"], num_amostras)
        
        fase_esq = 2 * np.pi * np.cumsum(freq_base) / taxa_amostragem
        fase_dir = 2 * np.pi * np.cumsum(freq_base + freq_alvo) / taxa_amostragem
        
        onda_esq = np.sin(fase_esq)
        onda_dir = np.sin(fase_dir)
        
        fade_t = int(taxa_amostragem * 2)
        envelope = np.ones(num_amostras)
        if i > 0:
            envelope[:fade_t] = np.linspace(0, 1, fade_t)
        if i < len(fases) - 1:
            envelope[-fade_t:] = np.linspace(1, 0, fade_t)
            
        audio_esquerdo_total.append(onda_esq * envelope)
        audio_direito_total.append(onda_dir * envelope)

    esq_final = np.concatenate(audio_esquerdo_total)
    dir_final = np.concatenate(audio_direito_total)
    
    esq_final = (esq_final / (np.max(np.abs(esq_final)) + 1e-10)) * 0.7
    dir_final = (dir_final / (np.max(np.abs(dir_final)) + 1e-10)) * 0.7
    
    audio_estereo = np.vstack((esq_final, dir_final)).T
    audio_16bit = (audio_estereo * 32767).astype(np.int16)
    
    wavfile.write(filename, taxa_amostragem, audio_16bit)
    return filename

# INTERFACE DO STREAMLIT
st.title("Gerador de Sinal - Parceria Industrial")
st.write("Modulando frequências de arrastamento escalar para Semicondutores e Logística Global...")

if st.button("Gerar Áudio .WAV"):
    with st.spinner("Processando matrizes de sinal..."):
        nome_arquivo = gerar_sinal_parceria_industrial()
        st.success("Sinal pronto para alinhar a produção física à distribuição de mercado!")
        
        # Player de áudio na tela
        with open(nome_arquivo, "rb") as f:
            st.audio(f.read(), format="audio/wav")
            
        # Botão para baixar o arquivo
        with open(nome_arquivo, "rb") as f:
            st.download_button(
                label="Baixar Arquivo .WAV",
                data=f,
                file_name=nome_arquivo,
                mime="audio/wav"
            )

# Execução padrão do Python corrigida com dois underlines (dunder)
if __name__ == "__main__":
    pass
