import numpy as np
try:
    from scipy.io import wavfile
except ImportError:
    print("\n[ERRO] A biblioteca 'scipy' não foi encontrada.")
    print("Por favor, instale executando no seu terminal: pip install numpy scipy\n")
    raise

def gerar_sinal_parceria_industrial(filename="parceria_ceitec_ecomcs.wav"):
    taxa_amostragem = 44100  # 44.1 kHz
    
    # Roteiro: Estruturação Física do Silício -> Alinhamento Comercial -> Expansão Global
    fases = [
        # Fase 1: Ancoragem Industrial (288Hz portadora - Desacelerando ruídos em Alfa 11Hz)
        {"tempo": 120, "base_inicio": 288, "base_fim": 288, "alvo_inicio": 15, "alvo_fim": 11},  
        
        # Fase 2: Alinhamento de Microtúbulos e Ativação do Silício (Theta 7Hz para Engenharia Fina)
        {"tempo": 180, "base_inicio": 288, "base_fim": 288, "alvo_inicio": 11, "alvo_fim": 7},   
        
        # Fase 3: Sinergia de Intenção Ceitec (Manifestação da manufatura e interesse técnico em Delta 2Hz)
        {"tempo": 300, "base_inicio": 288, "base_fim": 288, "alvo_inicio": 7,  "alvo_fim": 2},   
        
        # Fase 4: O Estalo da Comercialização/Exportação pela ECO-MCS (Frequência Gamma 40Hz para Fechamento de Contrato Global)
        {"tempo": 300, "base_inicio": 288, "base_fim": 288, "alvo_inicio": 2,  "alvo_fim": 40}   
    ]
    
    audio_esquerdo_total = []
    audio_direito_total = []
    
    print("Modulando frequências de arrastamento escalar para Semicondutores e Logística Global...")
    
    for i, fase in enumerate(fases):
        num_amostras = int(taxa_amostragem * fase["tempo"])
        
        freq_base = np.linspace(fase["base_inicio"], fase["base_fim"], num_amostras)
        freq_alvo = np.linspace(fase["alvo_inicio"], fase["alvo_fim"], num_amostras)
        
        # Modulação estéreo por cancelamento de fase escalar pura
        fase_esq = 2 * np.pi * np.cumsum(freq_base) / taxa_amostragem
        fase_dir = 2 * np.pi * np.cumsum(freq_base + freq_alvo) / taxa_amostragem
        
        onda_esq = np.sin(fase_esq)
        onda_dir = np.sin(fase_dir)
        
        # Fade de 2 segundos para transição suave
        fade_t = int(taxa_amostragem * 2)
        envelope = np.ones(num_amostras)
        if i > 0:
            envelope[:fade_t] = np.linspace(0, 1, fade_t)
        if i < len(fases) - 1:
            envelope[-fade_t:] = np.linspace(1, 0, fade_t)
            
        audio_esquerdo_total.append(onda_esq * envelope)
        audio_direito_total.append(onda_dir * envelope)
        print(f" -> Matriz da Fase {i+1}/4 integrada ao sinal.")

    esq_final = np.concatenate(audio_esquerdo_total)
    dir_final = np.concatenate(audio_direito_total)
    
    # Trava de segurança contra divisão por zero e ganho limpo
    esq_final = (esq_final / (np.max(np.abs(esq_final)) + 1e-10)) * 0.7
    dir_final = (dir_final / (np.max(np.abs(dir_final)) + 1e-10)) * 0.7
    
    audio_estereo = np.vstack((esq_final, dir_final)).T
    audio_16bit = (audio_estereo * 32767).astype(np.int16)
    
    try:
        wavfile.write(filename, taxa_amostragem, audio_16bit)
        print(f"\n[SUCESSO] Arquivo '{filename}' gerado perfeitamente!")
        print("Sinal pronto para alinhar a produção física à distribuição de mercado.")
    except Exception as e:
        print(f"\n[ERRO] Falha ao salvar o arquivo: {e}")


if __name__ == "__main__":
    gerar_sinal_parceria_industrial()

