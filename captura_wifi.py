import subprocess
import os
import glob
import time
from datetime import datetime
from logger_config import logger

def obter_interfaces_wifi():
    """Retorna uma lista de interfaces de rede disponíveis."""
    logger.info("Detectando interfaces de rede")
    try:
        # Usar ip addr em vez de iwconfig para maior compatibilidade
        resultado = subprocess.run(["ip", "addr"], capture_output=True, text=True)
        interfaces = []
        
        # Procurar por interfaces de rede
        for linha in resultado.stdout.split("\n"):
            if ": " in linha and not linha.startswith(" "):
                # Linhas que começam com número são interfaces
                partes = linha.split(": ")
                if len(partes) >= 2:
                    # O formato é "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP>"
                    interface = partes[1].split(":")[0].strip()
                    if interface != "lo":  # Ignorar loopback
                        interfaces.append(interface)
        
        logger.info(f"Interfaces encontradas: {interfaces}")
        return interfaces
    except Exception as e:
        logger.error(f"Erro ao detectar interfaces: {e}")
        # Fallback para interfaces comuns
        return ["eth0", "wlan0"]

def iniciar_captura(interface=None, filtro=None):
    """Inicia a captura de pacotes usando tcpdump.
    
    Args:
        interface: Interface a ser usada
        filtro: Filtro tcpdump opcional (ex: 'icmp' para capturar pings)
    """
    logger.info(f"Iniciando captura. Interface: {interface}, Filtro: {filtro}")
    
    # Se interface não foi especificada, usa a primeira disponível
    if not interface:
        interfaces = obter_interfaces_wifi()
        if not interfaces:
            logger.error("Nenhuma interface de rede encontrada")
            raise Exception("Nenhuma interface de rede encontrada!")
        
        interface = interfaces[0]
        logger.info(f"Interface selecionada: {interface}")
    
    # Se filtro não foi especificado, usar um padrão que capture vários protocolos úteis
    if not filtro:
        filtro = "icmp or arp or tcp port 80 or tcp port 443 or udp port 53"
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Definir o diretório e o nome do arquivo
    dir_capturas = "data/capturas"
    arquivo_saida = os.path.join(dir_capturas, f"captura_{timestamp}.pcap")
    
    os.makedirs(dir_capturas, exist_ok=True)

    # Construir comando tcpdump
    # -i: interface
    # -w: arquivo de saída
    # -v: verbose
    # -n: não resolve nomes
    # -s 0: captura o pacote inteiro
    comando = ["tcpdump", "-i", interface, "-w", arquivo_saida, "-v", "-n", "-s", "0"]
    
    # Adicionar filtro se especificado
    if filtro:
        comando.append(filtro)
    
    logger.info(f"Comando: {' '.join(comando)}")
    
    try:
        # Pode ser necessário executar com sudo
        try:
            processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except PermissionError:
            logger.warning("Tentando executar com sudo...")
            comando = ["sudo"] + comando
            processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Verificar se o processo iniciou corretamente
        time.sleep(1)
        if processo.poll() is not None:
            # Processo já terminou, verificar erro
            _, stderr = processo.communicate()
            error_msg = stderr.decode('utf-8')
            logger.error(f"Erro ao iniciar tcpdump: {error_msg}")
            raise Exception(f"Erro ao iniciar tcpdump: {error_msg}")
        
        logger.info(f"Processo iniciado (PID: {processo.pid})")
        return processo, arquivo_saida, interface
    except Exception as e:
        logger.error(f"Erro ao iniciar captura: {e}")
        raise

def parar_captura(processo):
    """Para a captura e verifica se o arquivo foi gerado."""
    if not processo:
        logger.warning("Tentativa de parar captura com processo nulo")
        return False
        
    logger.info(f"Parando captura (PID: {processo.pid})")
    try:
        # Enviar sinal SIGTERM para interromper tcpdump graciosamente
        processo.terminate()
        
        # Aguardar que o processo termine
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Timeout esperando processo terminar, forçando encerramento")
            processo.kill()
        
        logger.info("Captura encerrada")
        return True
    except Exception as e:
        logger.error(f"Erro ao encerrar captura: {e}")
        raise

def obter_arquivos_captura(arquivo):
    """Verifica se o arquivo de captura foi criado."""
    if not arquivo:
        return []
    
    # Verificar se o arquivo existe
    if os.path.exists(arquivo) and os.path.getsize(arquivo) > 0:
        logger.info(f"Arquivo de captura encontrado: {arquivo} ({os.path.getsize(arquivo)} bytes)")
        return [arquivo]
    else:
        logger.warning(f"Arquivo de captura não encontrado ou vazio: {arquivo}")
        return []

def interpretar_tipo_arquivo(arquivo):
    """Retorna uma descrição amigável do tipo de arquivo de captura."""
    nome = os.path.basename(arquivo)
    ext = os.path.splitext(nome)[1].lower()
    
    if ext == '.pcap':
        return "Captura de pacotes (tcpdump)"
    else:
        return f"Arquivo {ext}"

def analisar_captura(arquivo_pcap, filtro=None):
    """Analisa um arquivo .pcap e retorna estatísticas básicas."""
    if not os.path.exists(arquivo_pcap):
        return {"erro": "Arquivo não encontrado"}
    
    try:
        # Contar pacotes no arquivo
        comando = ["tcpdump", "-r", arquivo_pcap, "-n"]
        if filtro:
            comando.append(filtro)
        comando.append("2>/dev/null | wc -l")
        
        # Executar como um único comando shell
        resultado = subprocess.run(" ".join(comando), shell=True, capture_output=True, text=True)
        contagem = resultado.stdout.strip()
        
        # Verificar tráfego ICMP (ping)
        comando_icmp = f"tcpdump -r {arquivo_pcap} -n icmp 2>/dev/null | head -10"
        pings = subprocess.run(comando_icmp, shell=True, capture_output=True, text=True)
        ping_sample = pings.stdout.strip()
        
        # Verificar protocolos presentes
        protocolos = []
        for proto in ["icmp", "tcp", "udp", "arp", "dns"]:
            cmd = f"tcpdump -r {arquivo_pcap} -n {proto} 2>/dev/null | wc -l"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            count = int(res.stdout.strip() or "0")
            if count > 0:
                protocolos.append(f"{proto}: {count}")
        
        return {
            "arquivo": arquivo_pcap,
            "total_pacotes": contagem,
            "protocolos": protocolos,
            "amostra_ping": ping_sample if ping_sample else "Nenhum pacote ICMP encontrado"
        }
    except Exception as e:
        logger.error(f"Erro ao analisar captura: {e}")
        return {"erro": str(e)}
