import zipfile
from logger_config import logger
import os

def tentar_desbloquear_zip(caminho_zip, caminho_wordlist):
    logger.info(f"Tentando desbloquear: {os.path.basename(caminho_zip)}")
    
    try:
        with zipfile.ZipFile(caminho_zip) as zf:
            info = zf.infolist()
            logger.info(f"Arquivo ZIP contém {len(info)} itens")
            
            # Verifica se o arquivo está realmente protegido
            senha_necessaria = any(i.flag_bits & 0x1 for i in info)
            if not senha_necessaria:
                logger.warning("Arquivo ZIP não está protegido por senha")
            
            # Contadores para logging
            total_senhas = sum(1 for _ in open(caminho_wordlist, 'rb'))
            logger.info(f"Wordlist contém {total_senhas} senhas")
            
            tentativas = 0
            with open(caminho_wordlist, 'rb') as f:
                for linha in f:
                    senha = linha.strip()
                    tentativas += 1
                    
                    if tentativas % 1000 == 0:
                        logger.info(f"Progresso: {tentativas}/{total_senhas} ({(tentativas/total_senhas)*100:.1f}%)")
                    
                    try:
                        zf.extractall(pwd=senha)
                        senha_str = senha.decode('utf-8')
                        logger.info(f"Senha encontrada: '{senha_str}'")
                        return senha_str
                    except:
                        continue
            
            logger.info(f"Nenhuma senha funcionou ({tentativas} tentativas)")
        return None
    except FileNotFoundError as e:
        logger.error(f"Arquivo não encontrado: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao desbloquear ZIP: {e}")
        return None
