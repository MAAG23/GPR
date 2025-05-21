import nmap
import json
from datetime import datetime
import os
import socket
from logger_config import logger

MODO_TESTE = False

HISTORY_FILE = "data/history.json"
os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

if not os.path.isfile(HISTORY_FILE):
    with open(HISTORY_FILE, "w") as f:
        json.dump([], f)

def obter_range_rede():
    """Obtém o range da rede local baseado no IP da máquina."""
    try:
        # Obtém endereço IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
        
        # Converte para range CIDR
        partes = ip_local.split('.')
        range_rede = f"{partes[0]}.{partes[1]}.{partes[2]}.0/24"
        logger.info(f"Range de rede: {range_rede}")
        return range_rede
    except Exception as e:
        fallback = "192.168.1.0/24"
        logger.error(f"Erro ao obter range de rede: {e}. Usando {fallback}")
        return fallback

def fazer_rastreio():
    logger.info("Iniciando rastreio de rede")
    
    if MODO_TESTE:
        logger.info("Usando dados de teste")
        dispositivos = [
            {"ip": "192.168.1.10", "hostname": "Dispositivo-Teste-1", "portas": [{"porta": 22, "estado": "open", "protocolo": "tcp"}, {"porta": 80, "estado": "open", "protocolo": "tcp"}]},
            {"ip": "192.168.1.25", "hostname": "Dispositivo-Teste-2", "portas": [{"porta": 443, "estado": "open", "protocolo": "tcp"}]},
            {"ip": "192.168.1.55", "hostname": "Impressora-Teste", "portas": []}
        ]
    else:
        try:
            nm = nmap.PortScanner()
            
            # Determina o range de rede automaticamente
            range_rede = obter_range_rede()
            
            # Constrói argumentos nmap
            args = "-T4 -F --open -sV"
            logger.info(f"Executando nmap em {range_rede}")
            
            # Escaneia portas comuns e faz detecção de serviço
            nm.scan(hosts=range_rede, arguments=args)
            logger.info(f"Scan concluído. Hosts encontrados: {len(nm.all_hosts())}")
            
            dispositivos = []
            for host in nm.all_hosts():
                info = {"ip": host, "hostname": nm[host].hostname(), "portas": []}
                
                # Processa portas TCP
                if 'tcp' in nm[host]:
                    tcp_count = 0
                    for porta in nm[host]['tcp']:
                        estado = nm[host]['tcp'][porta]
                        if estado['state'] == 'open':
                            tcp_count += 1
                            servico_info = estado.get('product', '') + ' ' + estado.get('version', '')
                            servico_info = servico_info.strip()
                            info["portas"].append({
                                "porta": porta, 
                                "estado": estado['state'], 
                                "protocolo": "tcp",
                                "servico": estado.get('name', 'desconhecido'),
                                "versao": servico_info
                            })
                
                # Processa portas UDP
                if 'udp' in nm[host]:
                    for porta in nm[host]['udp']:
                        estado = nm[host]['udp'][porta]
                        if estado['state'] == 'open':
                            servico_info = estado.get('product', '') + ' ' + estado.get('version', '')
                            servico_info = servico_info.strip()
                            info["portas"].append({
                                "porta": porta, 
                                "estado": estado['state'], 
                                "protocolo": "udp",
                                "servico": estado.get('name', 'desconhecido'),
                                "versao": servico_info
                            })
                
                logger.info(f"Host {host}: {len(info['portas'])} portas abertas")
                dispositivos.append(info)
        except Exception as e:
            logger.error(f"Erro durante o rastreio: {e}")
            raise

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    resultado = {"timestamp": timestamp, "dispositivos": dispositivos}
    logger.info(f"Rastreio concluído: {len(dispositivos)} dispositivos")
    
    # Salva no histórico
    guardar_historico(resultado)
    return resultado

def guardar_historico(dados):
    try:
        historico = carregar_historico()
        historico.append(dados)
        with open(HISTORY_FILE, "w") as f:
            json.dump(historico, f, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar histórico: {e}")

def carregar_historico():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {e}")
        return []
