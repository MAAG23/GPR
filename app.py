import streamlit as st
from rastreio import fazer_rastreio, carregar_historico
from captura_wifi import iniciar_captura, parar_captura, obter_interfaces_wifi
from zip_cracker import tentar_desbloquear_zip
from logger_config import logger
import pandas as pd
import json
import io
import os
import tempfile

# Configuração da página Streamlit
logger.info("Iniciando aplicação")
st.set_page_config(page_title="Ferramenta de Análise de Rede", layout="wide")

st.title("🧰 Ferramenta de Análise de Rede e Segurança")

abas = st.tabs(["🔍 Rastreio de Rede", "📡 Captura de Pacotes de Rede", "🗂️ Desbloqueio de Arquivo ZIP"])

# ----- Aba 1: Rastreio de Rede -----
with abas[0]:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("🖥️ Verificação de Portas Abertas na Rede")
        st.write("Escaneie a rede para detectar dispositivos e portas abertas - útil para identificar serviços e potenciais vulnerabilidades.")
    with col2:
        if st.button("📡 Iniciar novo rastreio", use_container_width=True):
            logger.info("Iniciando rastreio de rede")
            with st.spinner("Rastreando dispositivos e portas abertas na rede..."):
                try:
                    resultado = fazer_rastreio()
                    logger.info(f"Rastreio concluído: {len(resultado['dispositivos'])} dispositivos")
                    st.success(f"Rastreio realizado com sucesso em {resultado['timestamp']}")
                except Exception as e:
                    logger.error(f"Erro no rastreio: {e}")
                    st.error(f"Erro ao realizar rastreio: {e}")

    st.markdown("---")
    historico = carregar_historico()
    if historico:
        ultimo = historico[-1]
        st.subheader(f"🖥️ Último Rastreio — {ultimo['timestamp']}")
        
        # Criar uma tabela consolidada de dispositivos para melhor visualização
        dispositivos_dados = []
        for dispositivo in ultimo['dispositivos']:
            portas_abertas = [p for p in dispositivo['portas'] if p['estado'] == 'open']
            portas_str = ", ".join([f"{p['porta']}/{p['protocolo']} ({p.get('servico', '')})" for p in portas_abertas])
            dispositivos_dados.append({
                "IP": dispositivo['ip'],
                "Hostname": dispositivo['hostname'],
                "Portas Abertas": portas_str,
                "Total Portas Abertas": len(portas_abertas)
            })
        
        df_dispositivos = pd.DataFrame(dispositivos_dados)
        st.dataframe(df_dispositivos, use_container_width=True)
        
        # Detalhes por dispositivo
        st.subheader("Detalhes por Dispositivo")
        for dispositivo in ultimo['dispositivos']:
            portas_abertas = [p for p in dispositivo['portas'] if p['estado'] == 'open']
            if portas_abertas:  # Mostrar apenas dispositivos com portas abertas
                with st.expander(f"{dispositivo['ip']} ({dispositivo['hostname']}) - {len(portas_abertas)} portas abertas"):
                    df_portas = pd.DataFrame(dispositivo['portas'])
                    st.dataframe(df_portas, use_container_width=True)

        st.markdown("### 📜 Histórico completo")
        exportar_json = json.dumps(historico, indent=2)
        st.download_button("📥 Exportar JSON", exportar_json, file_name="historico.json")

        dados_csv = []
        for rastreio in historico:
            for dispositivo in rastreio['dispositivos']:
                for porta in dispositivo['portas']:
                    dados_csv.append({
                        "Data/Hora": rastreio['timestamp'],
                        "IP": dispositivo['ip'],
                        "Hostname": dispositivo['hostname'],
                        "Porta": porta['porta'],
                        "Protocolo": porta['protocolo'],
                        "Estado": porta['estado'],
                        "Serviço": porta.get('servico', ''),
                        "Versão": porta.get('versao', '')
                    })
        df_csv = pd.DataFrame(dados_csv)
        buffer_csv = io.StringIO()
        df_csv.to_csv(buffer_csv, index=False)
        st.download_button("📥 Exportar CSV", buffer_csv.getvalue(), file_name="historico.csv")
    else:
        st.warning("Nenhum rastreio foi realizado até agora.")

# ----- Aba 2: Captura de Pacotes de Rede -----
with abas[1]:
    st.subheader("📡 Captura de Pacotes de Rede")
    
    # Detectar automaticamente interfaces disponíveis
    try:
        interfaces_disponiveis = obter_interfaces_wifi()
    except Exception as e:
        logger.error(f"Erro ao obter interfaces: {e}")
        interfaces_disponiveis = []
    
    if interfaces_disponiveis:
        col1, col2 = st.columns(2)
        with col1:
            interface_selecionada = st.selectbox(
                "Interface de rede", 
                options=interfaces_disponiveis,
                index=0,
                help="Interface detectada automaticamente"
            )
        with col2:
            filtro = st.text_input("Filtro (opcional)", 
                                   value="icmp or arp", 
                                   help="Filtro tcpdump (ex: 'icmp' para pings, 'tcp port 80' para HTTP)")
    else:
        st.warning("Nenhuma interface de rede detectada. Verifique se você tem permissões suficientes.")
        interface_selecionada = st.text_input("Nome da interface manual", value="eth0")
        filtro = st.text_input("Filtro (opcional)", value="icmp or arp")

    # Inicializar variáveis de estado para a sessão
    if "captura_em_andamento" not in st.session_state:
        st.session_state.captura_em_andamento = False
        st.session_state.processo = None
        st.session_state.arquivo_pcap = None
        st.session_state.interface_usada = None
        st.session_state.arquivos_capturados = []
        st.session_state.analise_captura = None

    # Botões de controle para captura
    col1, col2 = st.columns(2)
    with col1:
        iniciar_btn = st.button("▶️ Iniciar captura", use_container_width=True) 
        if iniciar_btn and not st.session_state.captura_em_andamento:
            logger.info(f"Iniciando captura na interface {interface_selecionada}")
            try:
                proc, arquivo_pcap, interface_usada = iniciar_captura(interface_selecionada, filtro)
                st.session_state.captura_em_andamento = True
                st.session_state.processo = proc
                st.session_state.arquivo_pcap = arquivo_pcap
                st.session_state.interface_usada = interface_usada
                st.success(f"Captura iniciada na interface {interface_usada}. Arquivo: {os.path.basename(arquivo_pcap)}")
            except Exception as e:
                logger.error(f"Erro ao iniciar captura: {e}")
                st.error(f"Erro ao iniciar captura: {e}")
    
    with col2:
        parar_btn = st.button("⏹️ Parar captura", use_container_width=True)
        if parar_btn and st.session_state.captura_em_andamento:
            logger.info("Parando captura")
            try:
                # Parar a captura
                from captura_wifi import obter_arquivos_captura, interpretar_tipo_arquivo, analisar_captura
                
                # Aguardar um pouco para garantir que o tcpdump salve os pacotes
                if parar_captura(st.session_state.processo):
                    st.success("Processo de captura encerrado com sucesso.")
                    
                    # Dar um tempo para garantir que o arquivo foi salvo
                    # (tcpdump pode levar um momento para liberar o arquivo)
                    import time
                    time.sleep(1)
                    
                    # Verificar se o arquivo foi criado
                    arquivos = obter_arquivos_captura(st.session_state.arquivo_pcap)
                    st.session_state.arquivos_capturados = arquivos
                    
                    if arquivos:
                        st.success(f"Captura concluída com sucesso! Arquivo salvo: {os.path.basename(arquivos[0])}")
                        
                        # Analisar a captura para mostrar estatísticas
                        with st.spinner("Analisando captura..."):
                            resultado = analisar_captura(arquivos[0])
                            st.session_state.analise_captura = resultado
                    else:
                        st.warning("Captura encerrada, mas o arquivo não foi encontrado. Você pode precisar de permissões de superusuário.")
                else:
                    st.error("Não foi possível encerrar o processo de captura.")
                
                # Atualizar estado
                st.session_state.captura_em_andamento = False
                
            except Exception as e:
                logger.error(f"Erro ao parar captura: {e}")
                st.error(f"Erro ao parar captura: {e}")
                st.session_state.captura_em_andamento = False
    
    # Mostrar status da captura
    if st.session_state.captura_em_andamento:
        st.info(f"Captura em andamento na interface {st.session_state.interface_usada}...")
        st.info("Tente executar 'ping google.com' para ver se a captura detecta.")
        st.warning("Pressione o botão 'Parar captura' quando terminar de coletar dados.")

    # Se temos uma análise para mostrar
    if hasattr(st.session_state, 'analise_captura') and st.session_state.analise_captura:
        analise = st.session_state.analise_captura
        
        st.markdown("### 📊 Análise da Captura")
        
        if "erro" in analise:
            st.error(f"Erro na análise: {analise['erro']}")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de pacotes", analise["total_pacotes"])
            with col2:
                if "protocolos" in analise and analise["protocolos"]:
                    st.write("**Protocolos detectados:**")
                    for proto in analise["protocolos"]:
                        st.write(f"- {proto}")
                else:
                    st.write("Nenhum protocolo detectado")
            
            # Mostrar amostra de pings
            if "amostra_ping" in analise and analise["amostra_ping"] and analise["amostra_ping"] != "Nenhum pacote ICMP encontrado":
                st.markdown("#### Amostra de Pings Detectados:")
                st.code(analise["amostra_ping"])
    
    # Mostrar arquivos de captura (do atual ou de capturas anteriores)
    st.markdown("### Arquivos de Captura")
    
    # Tentar listar arquivos da captura atual
    arquivos_atuais = []
    if hasattr(st.session_state, 'arquivos_capturados'):
        arquivos_atuais = st.session_state.arquivos_capturados
    
    # Se não tiver arquivos da captura atual, listar todos os arquivos da pasta
    if not arquivos_atuais and os.path.exists("data/capturas"):
        from captura_wifi import interpretar_tipo_arquivo
        # Listar apenas arquivos .pcap
        arquivos_atuais = []
        for arquivo in os.listdir("data/capturas"):
            caminho_completo = os.path.join("data/capturas", arquivo)
            if os.path.isfile(caminho_completo) and arquivo.endswith('.pcap'):
                arquivos_atuais.append(caminho_completo)
        
        # Ordenar por data de modificação (mais recente primeiro)
        arquivos_atuais.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    if arquivos_atuais:
        for arquivo in arquivos_atuais:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                tipo_arquivo = interpretar_tipo_arquivo(arquivo)
                tamanho = os.path.getsize(arquivo)
                tamanho_str = f"{tamanho/1024:.1f} KB" if tamanho >= 1024 else f"{tamanho} bytes"
                st.write(f"📄 **{os.path.basename(arquivo)}** - {tipo_arquivo} ({tamanho_str})")
            with col2:
                with open(arquivo, "rb") as f:
                    st.download_button(
                        label="📥 Download",
                        data=f,
                        file_name=os.path.basename(arquivo),
                        mime="application/octet-stream",
                        key=f"download_{arquivo}"
                    )
            with col3:
                # Botão para analisar a captura
                if st.button("🔍 Analisar", key=f"analisar_{arquivo}"):
                    from captura_wifi import analisar_captura
                    with st.spinner("Analisando captura..."):
                        resultado = analisar_captura(arquivo)
                        st.session_state.analise_captura = resultado
                        st.experimental_rerun()
    else:
        st.info("Nenhum arquivo de captura encontrado. Inicie uma captura para gerar arquivos.")
    
    # Informação adicional
    with st.expander("ℹ️ Sobre a captura de pacotes"):
        st.markdown("""
        ### Como usar:
        1. Selecione a interface de rede (geralmente eth0 ou wlan0)
        2. Opcionalmente, defina um filtro para capturar apenas tipos específicos de pacotes
        3. Clique em **Iniciar captura**
        4. Execute comandos como `ping google.com` em outro terminal
        5. Clique em **Parar captura** quando terminar
        6. Os resultados serão analisados automaticamente
        
        ### Filtros comuns:
        - `icmp` - Captura pacotes ping
        - `tcp port 80` - Captura tráfego HTTP
        - `tcp port 443` - Captura tráfego HTTPS
        - `arp` - Captura pacotes ARP (descoberta de endereços na rede)
        - `host 8.8.8.8` - Captura todo tráfego para/de 8.8.8.8
        """)

# ----- Aba 3: Desbloqueio de ZIP -----
with abas[2]:
    st.subheader("🗂️ Desbloquear arquivo ZIP com wordlist")
    zip_file = st.file_uploader("Escolher arquivo ZIP", type="zip")
    wordlist = st.file_uploader("Escolher wordlist (.txt)", type="txt")

    desbloquear_btn = st.button("🔓 Tentar desbloquear")
    if zip_file and wordlist and desbloquear_btn:
        logger.info(f"Tentando desbloquear ZIP: {zip_file.name}")
        with st.spinner("Tentando encontrar senha..."):
            try:
                # Salvar arquivos temporariamente para usar com o zip_cracker
                with tempfile.NamedTemporaryFile(delete=False) as tmp_zip:
                    tmp_zip.write(zip_file.read())
                    tmp_zip_path = tmp_zip.name

                with tempfile.NamedTemporaryFile(delete=False) as tmp_wordlist:
                    tmp_wordlist.write(wordlist.read())
                    tmp_wordlist_path = tmp_wordlist.name

                senha = tentar_desbloquear_zip(tmp_zip_path, tmp_wordlist_path)

                if senha:
                    logger.info(f"Senha encontrada: {senha}")
                    st.success(f"✅ Senha encontrada: `{senha}`")
                else:
                    logger.info("Nenhuma senha funcionou")
                    st.error("❌ Nenhuma senha funcionou.")
                
                # Limpar arquivos temporários
                try:
                    os.unlink(tmp_zip_path)
                    os.unlink(tmp_wordlist_path)
                except Exception:
                    pass
            
            except Exception as e:
                logger.error(f"Erro ao desbloquear ZIP: {e}")
                st.error(f"Erro ao tentar desbloquear ZIP: {e}")

logger.info("Aplicação pronta")
