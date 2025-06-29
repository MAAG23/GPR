import pygame
import numpy as np
import librosa
import sounddevice as sd
import random
import speech_recognition as sr
import threading
import time

# Audio initialization moved to initialize_audio() function

# Configurações iniciais
WIDTH, HEIGHT = 800, 600
screen = None  # Será inicializado na função main
clock = None   # Será inicializado na função main
font = None    # Será inicializado na função main
large_font = None  # Será inicializado na função main
small_font = None  # Será inicializado na função main

# Configurações de áudio
available_devices = []
selected_device = None
samplerate = 44100
win_s = 2048
hop_s = 1024
audio_stream = None

# Buffer para armazenar samples de áudio para análise de pitch
audio_buffer = np.zeros(win_s)
buffer_index = 0

# Variáveis globais do jogo
ball_x = 200
ball_y = HEIGHT - 50
ball_target_y = HEIGHT - 50
ball_radius = 20
lives = 3
invulnerable_frames = 0
pitch_detected = False
MIN_PITCH = 80
MAX_PITCH = 400
GROUND_Y = HEIGHT - 50
DESCENT_RESISTANCE = 0.05
barriers = []
barrier_width = 20
barrier_gap = 150
BASE_BARRIER_SPEED = 3.0
barrier_speed = BASE_BARRIER_SPEED
barrier_timer = 0
barrier_spawn_interval = 150
score = 0
game_state = "menu"
SPEED_INCREASE_INTERVAL = 2
SPEED_INCREASE_FACTOR = 1.25
SLOWDOWN_DURATION = 30
RECOVERY_SPEED = 0.1

# Variáveis para teste de microfone
mic_test_active = False
mic_test_volume = 0
mic_test_pitch = 0

# Variáveis para detecção de pitch
pitch_history = []
pitch_history_size = 5

# Variáveis para reconhecimento de comandos
voice_commands = {
    "correr": False,
    "saltar": False,
    "abaixar": False
}
command_recognition_active = False
last_command = ""
command_thread = None

# Variáveis para o segundo jogo (plataforma baseada em pixels)
player_grid_x = 0  # Posição no grid
player_grid_y = 0  # Altura no grid (0 = no chão, 1 = abaixado, 2 = pulando)
GRID_SIZE = 40  # Tamanho de cada "pixel" do grid
GRID_WIDTH = WIDTH // GRID_SIZE  # Quantos pixels cabem na tela
GRID_HEIGHT = HEIGHT // GRID_SIZE

# Estado do jogador para animação
player_animation_state = "normal"  # normal, ducking, jumping
animation_timer = 0

# Mapa do jogo - cada posição pode ter diferentes tipos
game_map = []
map_scroll_x = 0  # Para fazer o mapa rolar
map_length = 30  # Comprimento inicial do mapa
max_generated_x = 0  # Controla até onde o mapa foi gerado

# Controle de qual jogo foi jogado por último
last_game_mode = None  # "pitch" para tonalidade, "command" para comandos

# Tipos de terreno
TERRAIN_EMPTY = 0      # Vazio (buraco)
TERRAIN_GROUND = 1     # Chão normal
TERRAIN_LOW_CEILING = 2 # Teto baixo (precisa abaixar)
TERRAIN_PLATFORM = 3   # Plataforma

# Variável para controlar popup de ajuda
show_help_popup = False

def detect_pitch(audio_data):
    """
    Detecta o pitch usando librosa
    """
    try:
        # Usar librosa para detecção de pitch
        pitches, magnitudes = librosa.piptrack(y=audio_data, sr=samplerate, threshold=0.1)
        
        # Encontrar o pitch com maior magnitude
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        if pitch_values:
            return np.median(pitch_values)
        else:
            return 0
    except:
        return 0

def initialize_audio():
    """Inicializa configurações de áudio e lista dispositivos disponíveis"""
    global available_devices, selected_device
    
    print("\nCarregando dispositivos de áudio...")
    devices = sd.query_devices()
    available_devices = []
    
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:  # Dispositivos de entrada
            available_devices.append({
                'id': i,
                'name': device['name'],
                'channels': device['max_input_channels'],
                'samplerate': device['default_samplerate']
            })
    
    if available_devices:
        selected_device = available_devices[0]['id']
        print(f"Dispositivo padrão selecionado: {available_devices[0]['name']}")

def start_audio_stream():
    """Inicia o stream de áudio com o dispositivo selecionado"""
    global audio_stream
    
    if audio_stream:
        audio_stream.stop()
        audio_stream.close()
    
    try:
        audio_stream = sd.InputStream(
            device=selected_device,
            channels=1,
            callback=audio_callback,
            samplerate=samplerate,
            blocksize=hop_s
        )
        audio_stream.start()
        print(f"Stream de áudio iniciado com dispositivo {selected_device}")
    except Exception as e:
        print(f"Erro ao iniciar stream de áudio: {e}")

def audio_callback(indata, frames, time, status):
    """Callback para processamento de áudio"""
    global ball_target_y, pitch_detected, pitch_history, mic_test_volume, mic_test_pitch
    global audio_buffer, buffer_index
    
    samples = np.frombuffer(indata, dtype=np.float32).flatten()
    
    # Calcular volume para teste de microfone
    volume = np.sqrt(np.mean(samples**2))
    mic_test_volume = min(volume * 1000, 100)  # Normalizar para 0-100
    
    # Adicionar samples ao buffer circular
    samples_to_add = min(len(samples), len(audio_buffer) - buffer_index)
    audio_buffer[buffer_index:buffer_index + samples_to_add] = samples[:samples_to_add]
    buffer_index = (buffer_index + samples_to_add) % len(audio_buffer)
    
    # Detectar pitch quando temos buffer completo
    if volume > 0.01:  # Só processar se houver sinal significativo
        pitch = detect_pitch(audio_buffer)
        mic_test_pitch = pitch
        
        if game_state == "playing" and MIN_PITCH < pitch < MAX_PITCH:
            pitch_history.append(pitch)
            if len(pitch_history) > pitch_history_size:
                pitch_history.pop(0)
            avg_pitch = sum(pitch_history) / len(pitch_history)

            pitch_detected = True
            relative = ((avg_pitch - MIN_PITCH) / (MAX_PITCH - MIN_PITCH)) ** 0.8
            ball_target_y = int(HEIGHT - relative * (HEIGHT - 50))
        else:
            if game_state == "playing":
                pitch_detected = False
                pitch_history.clear()
                ball_target_y = GROUND_Y
    else:
        if game_state == "playing":
            pitch_detected = False
            pitch_history.clear()
            ball_target_y = GROUND_Y

def start_command_recognition():
    """Inicia o reconhecimento de comandos de voz em thread separada"""
    global command_recognition_active, command_thread
    
    if command_thread and command_thread.is_alive():
        return
    
    command_recognition_active = True
    command_thread = threading.Thread(target=command_recognition_loop, daemon=True)
    command_thread.start()

def stop_command_recognition():
    """Para o reconhecimento de comandos de voz"""
    global command_recognition_active
    command_recognition_active = False

def command_recognition_loop():
    """Loop de reconhecimento de comandos de voz"""
    global voice_commands, last_command
    
    recognizer = sr.Recognizer()
    
    # Configurações mais específicas para melhor reconhecimento
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.5
    recognizer.phrase_threshold = 0.3
    
    while command_recognition_active:
        try:
            # Usar o mesmo dispositivo selecionado para o jogo
            with sr.Microphone(device_index=selected_device) as source:
                print(f"Ouvindo comandos no dispositivo {selected_device}...")
                # Ajustar para ruído ambiente
                recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Ouvir com timeout mais longo
                audio = recognizer.listen(source, timeout=2, phrase_time_limit=2)
            
            try:
                # Reconhecer com Google (português brasileiro)
                command = recognizer.recognize_google(audio, language='pt-BR').lower()
                print(f"Comando reconhecido: '{command}'")
                
                # Reset all commands
                for key in voice_commands:
                    voice_commands[key] = False
                
                # Set detected command com mais variações
                if "correr" in command or "corre" in command or "corra" in command or "anda" in command or "andar" in command:
                    voice_commands["correr"] = True
                    last_command = "correr"
                    print("→ COMANDO: CORRER")
                elif "saltar" in command or "pular" in command or "salta" in command or "pula" in command or "salto" in command or "pulo" in command:
                    voice_commands["saltar"] = True
                    last_command = "saltar"
                    print("→ COMANDO: SALTAR")
                elif "abaixar" in command or "baixar" in command or "abaixa" in command or "agachar" in command or "abaixo" in command or "baixo" in command:
                    voice_commands["abaixar"] = True
                    last_command = "abaixar"
                    print("→ COMANDO: ABAIXAR")
                else:
                    print(f"Comando não reconhecido: {command}")
                
            except sr.UnknownValueError:
                # Silêncio ou comando não reconhecido - isso é normal
                pass
            except sr.RequestError as e:
                print(f"Erro no serviço de reconhecimento: {e}")
                time.sleep(1)
                
        except sr.WaitTimeoutError:
            # Timeout - normal quando não há fala
            pass
        except Exception as e:
            print(f"Erro no loop de reconhecimento: {e}")
            time.sleep(0.5)

def reset_game():
    """Reseta o jogo para o estado inicial"""
    global ball_x, ball_y, ball_target_y, lives, invulnerable_frames, barriers, barrier_timer, score, pitch_detected, barrier_speed
    ball_x = 200
    ball_y = HEIGHT - 50
    ball_target_y = HEIGHT - 50
    lives = 3
    invulnerable_frames = 0
    barriers = []
    barrier_timer = 0
    score = 0
    pitch_detected = False
    barrier_speed = BASE_BARRIER_SPEED
    pitch_history.clear()

def reset_command_game():
    """Reseta o jogo de comandos para o estado inicial"""
    global player_grid_x, player_grid_y, score, player_animation_state, animation_timer, map_scroll_x, lives, max_generated_x
    
    # Gerar mapa inicial menor
    generate_game_map()
    
    # Configurar jogador na posição inicial
    player_grid_x = 2  # Começar um pouco à frente
    player_grid_y = get_ground_level(player_grid_x)  # Posicionar no chão
    score = 0
    lives = 3
    player_animation_state = "normal"
    animation_timer = 0
    map_scroll_x = 0
    max_generated_x = len(game_map) - 1
    
    # Reset commands
    for key in voice_commands:
        voice_commands[key] = False
    
    print(f"Jogo resetado! Jogador na posição ({player_grid_x}, {player_grid_y})")
    print("Pronto para receber comandos de voz!")

def generate_game_map():
    """Gera o mapa inicial do jogo plano com obstáculos intercalados e maior dificuldade"""
    global game_map
    game_map = []
    
    # Altura do chão sempre a mesma (jogo plano)
    ground_level = GRID_HEIGHT - 3
    
    # Rastrear últimos obstáculos para garantir intercalação
    last_obstacle_types = []
    
    for x in range(map_length):
        column = [TERRAIN_EMPTY] * GRID_HEIGHT
        
        # Chão base sempre na mesma altura
        for y in range(ground_level, GRID_HEIGHT):
            column[y] = TERRAIN_GROUND
        
        # Adicionar obstáculos específicos depois da posição inicial (com maior frequência)
        if x > 5:
            rand = random.random()
            obstacle_added = None
            
            # Verificar se o último obstáculo foi do mesmo tipo para evitar consecutivos
            last_hole = any(t == "hole" for t in last_obstacle_types[-1:])
            last_ceiling = any(t == "low_ceiling" for t in last_obstacle_types[-1:])
            
            # Aumentar frequência de obstáculos: 45% total (vs anterior 25%)
            # Mas manter intercalação rigorosa
            if rand < 0.25 and not last_hole:  # 25% chance de buraco
                # Verificar se não há obstáculo baixo muito recente (precisa de espaço para aterrisar)
                can_add_hole = True
                if last_obstacle_types and last_obstacle_types[-1] == "low_ceiling":
                    can_add_hole = False
                
                if can_add_hole:
                    # Remover chão para criar buraco
                    for y in range(ground_level, GRID_HEIGHT):
                        column[y] = TERRAIN_EMPTY
                    obstacle_added = "hole"
                    print(f"Buraco criado na posição {x}")
                        
            elif rand < 0.45 and not last_ceiling:  # 20% chance adicional de obstáculo baixo
                # Verificar se não há buraco muito recente (jogador precisa de espaço para correr)
                can_add_ceiling = True
                if last_obstacle_types and last_obstacle_types[-1] == "hole":
                    can_add_ceiling = False
                
                if can_add_ceiling:
                    # Obstáculo baixo que precisa abaixar para passar
                    obstacle_y = ground_level - 1
                    column[obstacle_y] = TERRAIN_LOW_CEILING
                    obstacle_added = "low_ceiling"
                    print(f"Obstáculo baixo criado na posição {x}")
            
            # Rastrear últimos obstáculos (manter histórico de 2 posições para intercalação rigorosa)
            if obstacle_added:
                last_obstacle_types.append(obstacle_added)
            else:
                # Limitar sequências longas sem obstáculos
                if len(last_obstacle_types) >= 2 and all(t == "normal" for t in last_obstacle_types[-2:]):
                    # Força um obstáculo se houver 2 posições normais consecutivas
                    if rand < 0.7:  # 70% chance de forçar obstáculo
                        if not last_hole and random.random() < 0.5:
                            # Força buraco
                            for y in range(ground_level, GRID_HEIGHT):
                                column[y] = TERRAIN_EMPTY
                            obstacle_added = "hole"
                            print(f"Buraco forçado na posição {x} (evitar muito terreno vazio)")
                        elif not last_ceiling:
                            # Força obstáculo baixo
                            obstacle_y = ground_level - 1
                            column[obstacle_y] = TERRAIN_LOW_CEILING
                            obstacle_added = "low_ceiling"
                            print(f"Obstáculo baixo forçado na posição {x} (evitar muito terreno vazio)")
                
                if obstacle_added:
                    last_obstacle_types.append(obstacle_added)
                else:
                    last_obstacle_types.append("normal")
                
            if len(last_obstacle_types) > 2:
                last_obstacle_types.pop(0)
        else:
            # Posições iniciais sempre normais
            last_obstacle_types.append("normal")
        
        game_map.append(column)

def get_ground_level(grid_x):
    """Encontra o nível do chão em uma posição x específica"""
    if grid_x < 0 or grid_x >= len(game_map):
        return GRID_HEIGHT - 1
    
    column = game_map[grid_x]
    for y in range(GRID_HEIGHT):
        if column[y] == TERRAIN_GROUND:
            return y - 1  # Retorna a posição acima do chão
    return GRID_HEIGHT - 1  # Se não encontrar chão, usar o fundo

def can_move_to(grid_x, grid_y, action="normal"):
    """Verifica se o jogador pode se mover para uma posição com uma ação específica"""
    if grid_x < 0 or grid_x >= len(game_map):
        print(f"Movimento inválido: posição {grid_x} fora do mapa")
        return False
    
    if grid_y < 0 or grid_y >= GRID_HEIGHT:
        print(f"Movimento inválido: altura {grid_y} fora dos limites")
        return False
    
    column = game_map[grid_x]
    
    # Verificar se há chão para pisar (não é buraco)
    ground_found = False
    for y in range(grid_y + 1, GRID_HEIGHT):
        if column[y] == TERRAIN_GROUND:
            ground_found = True
            break
    
    if not ground_found:
        # É um buraco - só pode passar saltando
        if action != "saltar":
            print(f"Buraco detectado na posição {grid_x} - precisa saltar")
            return False
    
    # Verificar obstáculos na altura do jogador
    if column[grid_y] == TERRAIN_LOW_CEILING:
        # Há obstáculo baixo - só pode passar abaixado
        if action != "abaixar":
            print(f"Obstáculo baixo na posição {grid_x} - precisa abaixar")
            return False
    
    # Para correr, verificar se o terreno é normal
    if action == "correr":
        # Não pode correr se há buraco ou obstáculo baixo
        if not ground_found:
            print(f"Não pode correr: buraco na posição {grid_x}")
            return False
        if column[grid_y] == TERRAIN_LOW_CEILING:
            print(f"Não pode correr: obstáculo baixo na posição {grid_x}")
            return False
        print(f"Terreno normal na posição {grid_x} - pode correr")
    
    return True

def update_command_game():
    """Atualiza a lógica do jogo de comandos baseado em plataforma plana"""
    global player_grid_x, player_grid_y, player_animation_state, animation_timer, score, map_scroll_x, lives, invulnerable_frames
    
    # Geração dinâmica: sempre manter pelo menos 15 pixels à frente do jogador
    needed_length = player_grid_x + 15
    if needed_length > len(game_map):
        extend_game_map(needed_length)
    
    # Processar comandos de voz
    command_executed = False
    
    if voice_commands["correr"]:
        # Correr: move 1 pixel para a direita
        new_x = player_grid_x + 1
        new_y = get_ground_level(new_x)
        
        print(f"Tentando correr de {player_grid_x} para {new_x}")
        
        # Verificar se vai cair em buraco ou bater em obstáculo
        if new_x < len(game_map):
            # Verificar buraco
            is_hole = all(game_map[new_x][y] == TERRAIN_EMPTY for y in range(new_y + 1, GRID_HEIGHT))
            # Verificar obstáculo baixo
            has_obstacle = new_y >= 0 and game_map[new_x][new_y] == TERRAIN_LOW_CEILING
            
            if is_hole or has_obstacle:
                # Colidiu - perde vida e move para próximo pixel
                if invulnerable_frames == 0:
                    lives -= 1
                    invulnerable_frames = SLOWDOWN_DURATION
                    if is_hole:
                        print("💥 Caiu no buraco! Vida perdida, movendo para próximo pixel")
                    else:
                        print("💥 Bateu no obstáculo! Vida perdida, movendo para próximo pixel")
                
                # Move para o próximo pixel mesmo após colisão
                player_grid_x = new_x
                player_grid_y = new_y if not is_hole else get_ground_level(new_x + 1)
                if is_hole and new_x + 1 < len(game_map):
                    player_grid_x = new_x + 1  # Pula o buraco
                    player_grid_y = get_ground_level(player_grid_x)
            else:
                # Movimento normal
                player_grid_x = new_x
                player_grid_y = new_y
                score += 1
                print(f"✓ Jogador correu para posição {player_grid_x}")
            
            player_animation_state = "running"
            animation_timer = 20
            command_executed = True
            
        voice_commands["correr"] = False
        
    elif voice_commands["saltar"]:
        # Saltar: pula sobre buracos (move 2 para a direita)
        new_x = player_grid_x + 2
        new_y = get_ground_level(new_x)
        
        print(f"Tentando saltar de {player_grid_x} para {new_x}")
        
        if new_x < len(game_map) and can_move_to(new_x, new_y, "saltar"):
            player_grid_x = new_x
            player_grid_y = new_y
            player_animation_state = "jumping"
            animation_timer = 25
            score += 2
            command_executed = True
            print(f"✓ Jogador saltou para posição {player_grid_x}")
        else:
            # Falha ao saltar - geralmente não deveria acontecer se a geração estiver correta
            print("✗ Falha ao saltar!")
            
        voice_commands["saltar"] = False
        
    elif voice_commands["abaixar"]:
        # Abaixar: passa sob obstáculos baixos
        next_x = player_grid_x + 1
        
        # Verificar se há obstáculo baixo na próxima posição (na altura onde o jogador normalmente fica)
        has_obstacle = False
        if next_x < len(game_map):
            player_height = get_ground_level(next_x)  # Altura onde o jogador normalmente fica
            if player_height >= 0 and game_map[next_x][player_height] == TERRAIN_LOW_CEILING:
                has_obstacle = True
                print(f"Obstáculo baixo detectado na posição {next_x}, altura {player_height}")
        
        # Se há obstáculo baixo, passa por baixo e vai para a posição seguinte
        if has_obstacle:
            # Há obstáculo baixo - passa por baixo e vai para posição após o obstáculo
            final_x = next_x + 1
            print(f"Tentando abaixar de {player_grid_x}, passando por baixo do obstáculo em {next_x}, indo para {final_x}")
        else:
            # Não há obstáculo baixo - movimento normal de 1 pixel
            final_x = next_x
            print(f"Tentando abaixar de {player_grid_x} para {final_x} (sem obstáculo)")
        
        final_y = get_ground_level(final_x)
        
        # Verificar se pode mover para a posição final
        if final_x < len(game_map) and can_move_to(final_x, final_y, "normal"):
            player_grid_x = final_x
            player_grid_y = final_y
            player_animation_state = "ducking"
            animation_timer = 20
            # Dar pontos extras se passou por baixo de obstáculo
            if has_obstacle:
                score += 2  # Pontos extras por passar por obstáculo
                print(f"✓ Jogador passou por baixo do obstáculo e chegou na posição {player_grid_x}")
            else:
                score += 1
                print(f"✓ Jogador abaixou para posição {player_grid_x}")
            command_executed = True
        else:
            # Não conseguiu abaixar/passar
            print("✗ Falha ao abaixar!")
            
        voice_commands["abaixar"] = False
    
    # Atualizar scroll da tela para seguir o jogador
    target_scroll = player_grid_x - GRID_WIDTH // 3
    map_scroll_x = max(0, target_scroll)
    
    # Reduzir timer de animação
    if animation_timer > 0:
        animation_timer -= 1
        if animation_timer == 0:
            player_animation_state = "normal"
    
    # Verificar se o jogador chegou ao final do mapa
    if player_grid_x >= len(game_map) - 3:
        print("🎉 Jogador chegou ao final!")
        # Gerar mais mapa ou declarar vitória
        if invulnerable_frames == 0:
            score += 10  # Bônus por completar

def draw_game_map():
    """Desenha o mapa do jogo plano"""
    for grid_x in range(int(map_scroll_x), min(len(game_map), int(map_scroll_x) + GRID_WIDTH + 1)):
        screen_x = (grid_x - map_scroll_x) * GRID_SIZE
        column = game_map[grid_x]
        
        for grid_y in range(GRID_HEIGHT):
            screen_y = grid_y * GRID_SIZE
            terrain_type = column[grid_y]
            
            if terrain_type == TERRAIN_GROUND:
                # Chão - marrom
                pygame.draw.rect(screen, (139, 69, 19), (screen_x, screen_y, GRID_SIZE, GRID_SIZE))
                pygame.draw.rect(screen, (101, 67, 33), (screen_x, screen_y, GRID_SIZE, GRID_SIZE), 2)
                
            elif terrain_type == TERRAIN_LOW_CEILING:
                # Obstáculo baixo - meio pixel de altura com vão abaixo
                # Desenhar apenas a metade superior do grid como obstáculo
                obstacle_height = GRID_SIZE // 2
                pygame.draw.rect(screen, (128, 128, 128), (screen_x, screen_y, GRID_SIZE, obstacle_height))
                pygame.draw.rect(screen, (96, 96, 96), (screen_x, screen_y, GRID_SIZE, obstacle_height), 2)
                
                # Desenhar linhas pontilhadas para mostrar o vão abaixo
                gap_y = screen_y + obstacle_height
                gap_height = GRID_SIZE - obstacle_height
                
                # Linhas pontilhadas verticais para indicar o vão
                for i in range(0, GRID_SIZE, 8):
                    pygame.draw.line(screen, (200, 200, 200), 
                                   (screen_x + i, gap_y), 
                                   (screen_x + i, gap_y + gap_height // 2), 2)
                
                # Seta indicando para abaixar (agora na parte superior)
                center_x = screen_x + GRID_SIZE // 2
                center_y = screen_y + obstacle_height // 2
                pygame.draw.polygon(screen, (255, 255, 0), [
                    (center_x - 6, center_y - 3),
                    (center_x + 6, center_y - 3),
                    (center_x, center_y + 3)
                ])
                
                # Texto indicativo menor
                font_small = pygame.font.SysFont(None, 12)
                text = font_small.render("ABAIXAR", True, (255, 255, 255))
                text_rect = text.get_rect(center=(center_x, gap_y + gap_height // 2))
                screen.blit(text, text_rect)
    
    # Desenhar indicadores de buracos
    for grid_x in range(int(map_scroll_x), min(len(game_map), int(map_scroll_x) + GRID_WIDTH + 1)):
        screen_x = (grid_x - map_scroll_x) * GRID_SIZE
        column = game_map[grid_x]
        
        # Verificar se há buraco (ausência de chão)
        is_hole = True
        for y in range(GRID_HEIGHT - 3, GRID_HEIGHT):
            if column[y] == TERRAIN_GROUND:
                is_hole = False
                break
        
        if is_hole:
            # Desenhar indicação de buraco
            hole_y = GRID_HEIGHT - 3
            pygame.draw.rect(screen, (50, 25, 0), (screen_x, hole_y * GRID_SIZE, GRID_SIZE, GRID_SIZE * 3))
            
            # Texto indicativo no meio do buraco
            font_small = pygame.font.SysFont(None, 16)
            text = font_small.render("SALTAR", True, (255, 255, 255))
            text_rect = text.get_rect(center=(screen_x + GRID_SIZE // 2, (hole_y + 1) * GRID_SIZE + GRID_SIZE // 2))
            screen.blit(text, text_rect)

def draw_command_player():
    """Desenha o jogador no jogo de comandos baseado em plataforma"""
    global invulnerable_frames
    
    # Calcular posição na tela
    screen_x = (player_grid_x - map_scroll_x) * GRID_SIZE
    screen_y = player_grid_y * GRID_SIZE
    
    # Cores baseadas no estado de animação
    colors = {
        "normal": (100, 100, 255),
        "running": (0, 255, 0),
        "jumping": (255, 255, 0),
        "ducking": (255, 100, 0)
    }
    
    color = colors.get(player_animation_state, (255, 255, 255))
    
    # Efeito de invulnerabilidade (piscar)
    if invulnerable_frames > 0 and invulnerable_frames % 10 < 5:
        color = (color[0] // 2, color[1] // 2, color[2] // 2)  # Cor mais escura
    
    # Ajustar tamanho baseado no estado
    player_width = GRID_SIZE - 4
    player_height = GRID_SIZE - 4
    
    if player_animation_state == "ducking":
        player_height = GRID_SIZE // 2
        screen_y += GRID_SIZE // 2
    elif player_animation_state == "jumping":
        # Efeito de pulo
        bounce = abs(animation_timer - 15) * 2
        screen_y -= bounce
    
    # Desenhar o jogador
    pygame.draw.rect(screen, color, (screen_x + 2, screen_y + 2, player_width, player_height))
    
    # Desenhar olhos (só se não estiver piscando devido à invulnerabilidade)
    if player_animation_state != "ducking" and not (invulnerable_frames > 0 and invulnerable_frames % 10 < 5):
        eye_size = 3
        pygame.draw.circle(screen, (255, 255, 255), (screen_x + 10, screen_y + 10), eye_size)
        pygame.draw.circle(screen, (255, 255, 255), (screen_x + 25, screen_y + 10), eye_size)
        pygame.draw.circle(screen, (0, 0, 0), (screen_x + 10, screen_y + 10), 2)
        pygame.draw.circle(screen, (0, 0, 0), (screen_x + 25, screen_y + 10), 2)

def draw_command_info():
    """Desenha informações sobre comandos de voz (versão simplificada)"""
    global show_help_popup
    
    y_offset = HEIGHT - 80
    command_text = f"Último comando: {last_command}" if last_command else "Pronto para comandos de voz"
    text = font.render(command_text, True, (255, 255, 255))
    screen.blit(text, (10, y_offset))
    
    # Status do reconhecimento de voz
    recognition_status = "🎤 ATIVO" if command_recognition_active else "🎤 INATIVO"
    status_color = (0, 255, 0) if command_recognition_active else (255, 0, 0)
    status_text = font.render(recognition_status, True, status_color)
    screen.blit(status_text, (10, y_offset + 30))
    
    # Botão de ajuda (ponto de exclamação) - posicionado abaixo do score
    help_button_rect = draw_help_button((10, 70))
    
    # Popup de ajuda
    if show_help_popup:
        draw_help_popup()
    
    return help_button_rect

def draw_help_button(center):
    """Desenha botão de ajuda com ponto de exclamação"""
    rect = pygame.Rect(0, 0, 25, 25)
    rect.center = center
    
    # Círculo azul
    pygame.draw.circle(screen, (0, 100, 200), center, 12)
    pygame.draw.circle(screen, (255, 255, 255), center, 12, 2)
    
    # Ponto de exclamação
    exclamation_font = pygame.font.SysFont(None, 20, bold=True)
    exclamation_text = exclamation_font.render("!", True, (255, 255, 255))
    exclamation_rect = exclamation_text.get_rect(center=center)
    screen.blit(exclamation_text, exclamation_rect)
    
    return rect

def draw_help_popup():
    """Desenha popup com instruções dos comandos de voz"""
    # Fundo semi-transparente
    popup_surface = pygame.Surface((WIDTH, HEIGHT))
    popup_surface.set_alpha(180)
    popup_surface.fill((0, 0, 0))
    screen.blit(popup_surface, (0, 0))
    
    # Janela do popup
    popup_width = 600
    popup_height = 400
    popup_x = (WIDTH - popup_width) // 2
    popup_y = (HEIGHT - popup_height) // 2
    
    popup_rect = pygame.Rect(popup_x, popup_y, popup_width, popup_height)
    pygame.draw.rect(screen, (40, 40, 60), popup_rect, border_radius=10)
    pygame.draw.rect(screen, (100, 150, 255), popup_rect, 3, border_radius=10)
    
    # Título
    title_font = pygame.font.SysFont(None, 36, bold=True)
    title_text = title_font.render("📢 COMANDOS DE VOZ", True, (255, 255, 255))
    title_rect = title_text.get_rect(center=(WIDTH // 2, popup_y + 40))
    screen.blit(title_text, title_rect)
    
    # Instruções dos comandos
    commands_info = [
        "🏃 CORRER:",
        "  'correr', 'corre', 'corra', 'andar', 'anda'",
        "  → Move 1 pixel (terreno normal)",
        "",
        "🦘 SALTAR:",
        "  'saltar', 'salta', 'pular', 'pula', 'salto', 'pulo'",
        "  → Move 2 pixels (passa sobre buracos)",
        "",
        "🦆 ABAIXAR:",
        "  'abaixar', 'abaixa', 'baixar', 'agachar', 'baixo'",
        "  → Move 1-2 pixels (passa sob obstáculos baixos)",
        "",
        "⚠️  Perde vida ao cair em buraco ou bater em obstáculo",
        ""
    ]
    
    info_font = pygame.font.SysFont(None, 24)
    small_info_font = pygame.font.SysFont(None, 20)
    
    y_start = popup_y + 80
    for i, line in enumerate(commands_info):
        if line.startswith(("🏃", "🦘", "🦆")):
            # Títulos dos comandos
            text = info_font.render(line, True, (255, 255, 100))
        elif line.startswith("  "):
            # Detalhes dos comandos
            text = small_info_font.render(line, True, (200, 200, 200))
        elif line.startswith("⚠️") or line.startswith("⌨️"):
            # Informações importantes
            text = small_info_font.render(line, True, (255, 150, 150))
        else:
            # Linhas vazias ou normais
            text = small_info_font.render(line, True, (255, 255, 255))
        
        screen.blit(text, (popup_x + 30, y_start + i * 22))
    
    # Botão fechar
    close_font = pygame.font.SysFont(None, 18)
    close_text = close_font.render("Clique em qualquer lugar para fechar", True, (150, 150, 150))
    close_rect = close_text.get_rect(center=(WIDTH // 2, popup_y + popup_height - 25))
    screen.blit(close_text, close_rect)

def main_menu():
    """Tela principal do jogo"""
    screen.fill((10, 10, 30))
    title = large_font.render("Jogos de Voz", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 120))

    btn1 = draw_button("Desafio de Tonalidade", (WIDTH//2, 250))
    btn2 = draw_button("Comandos de Voz", (WIDTH//2, 330))
    btn3 = draw_button("Configurar Microfone", (WIDTH//2, 410))
    btn4 = draw_small_button("Sair", (WIDTH//2, 500))
    
    return btn1, btn2, btn3, btn4

def microphone_config_menu():
    """Tela de configuração de microfone"""
    screen.fill((15, 15, 40))
    title = large_font.render("Configurar Microfone", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    # Mostrar dispositivo atual
    if selected_device is not None:
        current_device = next((d for d in available_devices if d['id'] == selected_device), None)
        if current_device:
            current_text = f"Atual: {current_device['name'][:40]}..."
            text = font.render(current_text, True, (200, 255, 200))
            screen.blit(text, (50, 120))
    
    buttons = []
    y_start = 170
    
    # Lista de dispositivos
    for i, device in enumerate(available_devices[:8]):  # Mostrar até 8 dispositivos
        device_name = device['name'][:50] + "..." if len(device['name']) > 50 else device['name']
        is_selected = device['id'] == selected_device
        
        color = (100, 255, 100) if is_selected else (200, 200, 200)
        text = small_font.render(f"{device['id']}: {device_name}", True, color)
        rect = pygame.Rect(50, y_start + i*35, WIDTH-100, 30)
        
        if is_selected:
            pygame.draw.rect(screen, (50, 100, 50), rect, border_radius=5)
        
        screen.blit(text, (rect.x + 10, rect.y + 5))
        buttons.append({'rect': rect, 'device_id': device['id']})
    
    # Botões de ação
    test_btn = draw_button("Testar Microfone", (WIDTH//2 - 120, HEIGHT - 80))
    back_btn = draw_button("Voltar", (WIDTH//2 + 120, HEIGHT - 80))
    
    return buttons, test_btn, back_btn

def microphone_test_menu():
    """Tela de teste de microfone"""
    screen.fill((20, 20, 50))
    title = large_font.render("Teste de Microfone", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    # Mostrar dispositivo sendo testado
    if selected_device is not None:
        current_device = next((d for d in available_devices if d['id'] == selected_device), None)
        if current_device:
            device_text = f"Testando: {current_device['name'][:40]}..."
            text = font.render(device_text, True, (200, 255, 200))
            screen.blit(text, (WIDTH//2 - text.get_width()//2, 100))
    
    # Barra de volume
    volume_rect = pygame.Rect(100, 200, 600, 30)
    pygame.draw.rect(screen, (50, 50, 50), volume_rect, border_radius=15)
    
    volume_width = int(mic_test_volume * 6)  # Volume de 0-100, barra de 600px
    if volume_width > 0:
        color = (0, 255, 0) if mic_test_volume < 70 else (255, 255, 0) if mic_test_volume < 90 else (255, 0, 0)
        filled_rect = pygame.Rect(100, 200, volume_width, 30)
        pygame.draw.rect(screen, color, filled_rect, border_radius=15)
    
    volume_text = font.render(f"Volume: {mic_test_volume:.1f}%", True, (255, 255, 255))
    screen.blit(volume_text, (100, 250))
    
    # Informações de pitch
    if mic_test_pitch > 0:
        pitch_text = font.render(f"Pitch: {mic_test_pitch:.1f} Hz", True, (255, 255, 255))
        screen.blit(pitch_text, (100, 290))
        
        # Visualizador de pitch
        if 80 < mic_test_pitch < 400:
            pitch_bar_rect = pygame.Rect(100, 330, 600, 20)
            pygame.draw.rect(screen, (80, 80, 80), pitch_bar_rect, border_radius=10)
            
            pitch_position = ((mic_test_pitch - 80) / (400 - 80)) * 600
            pitch_indicator = pygame.Rect(100 + pitch_position - 5, 330, 10, 20)
            pygame.draw.rect(screen, (0, 255, 255), pitch_indicator, border_radius=5)
    
    instructions = [
        "Fale ou faça algum som para testar o microfone",
        "A barra verde mostra o volume detectado",
        "A linha azul mostra o tom (pitch) da sua voz"
    ]
    
    for i, instruction in enumerate(instructions):
        text = small_font.render(instruction, True, (200, 200, 200))
        screen.blit(text, (100, 380 + i*25))
    
    back_btn = draw_button("Voltar", (WIDTH//2, HEIGHT - 60))
    return back_btn

def game_over_menu():
    """Tela de game over"""
    screen.fill((20, 0, 20))
    title = large_font.render("Game Over", True, (255, 80, 80))
    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 230))
    
    retry_btn = draw_button("Tentar Novamente", (WIDTH//2, 320))
    menu_btn = draw_button("Menu Principal", (WIDTH//2, 400))
    return retry_btn, menu_btn

def update_barrier_speed():
    """Atualiza a velocidade das barreiras baseado no score"""
    global barrier_speed, barrier_spawn_interval
    level = score // SPEED_INCREASE_INTERVAL
    if level > 0:
        barrier_speed = BASE_BARRIER_SPEED * (SPEED_INCREASE_FACTOR ** level)
        barrier_spawn_interval = int(150 / (SPEED_INCREASE_FACTOR ** level))
        barrier_spawn_interval = max(30, barrier_spawn_interval)

def add_barrier():
    """Adiciona uma nova barreira"""
    gap_y = random.randint(100, HEIGHT - 250)
    barriers.append({'x': WIDTH, 'gap_y': gap_y, 'passed': False})

def draw_barriers():
    """Desenha as barreiras do jogo principal"""
    for b in barriers:
        pygame.draw.rect(screen, (0, 255, 0), (b['x'], 0, barrier_width, b['gap_y']))
        pygame.draw.rect(screen, (0, 255, 0), (b['x'], b['gap_y'] + barrier_gap, barrier_width, HEIGHT))

def check_collision():
    """Verifica colisão no jogo principal"""
    global lives, barriers
    for i, b in enumerate(barriers):
        if ball_x + ball_radius > b['x'] and ball_x - ball_radius < b['x'] + barrier_width:
            if not (b['gap_y'] < ball_y < b['gap_y'] + barrier_gap):
                lives -= 1
                barriers.pop(i)
                return True
    return False

def draw_lives():
    """Desenha as vidas restantes"""
    for i in range(lives):
        pygame.draw.circle(screen, (255, 0, 0), (WIDTH - 30 - i*30, 30), 10)

def draw_score():
    """Desenha o score atual"""
    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    screen.blit(score_text, (10, 10))
    
    # Só mostrar multiplicador de velocidade no jogo de tonalidade
    if game_state == "playing":
        level = score // SPEED_INCREASE_INTERVAL
        if level > 0:
            speed_text = font.render(f"Speed: {SPEED_INCREASE_FACTOR ** level:.2f}x", True, (255, 200, 0))
            screen.blit(speed_text, (10, 40))

def draw_pitch_info():
    """Desenha informações sobre o pitch detectado"""
    pygame.draw.line(screen, (100, 100, 100), (0, GROUND_Y), (WIDTH, GROUND_Y), 2)
    status_text = "Voice Detected!" if pitch_detected else "No Voice Detected"
    color = (0, 255, 0) if pitch_detected else (255, 0, 0)
    text = font.render(status_text, True, color)
    screen.blit(text, (10, GROUND_Y + 5))
    
    if pitch_detected and pitch_history:
        pitch_text = f"Pitch: {sum(pitch_history) / len(pitch_history):.1f} Hz"
        pitch_info = font.render(pitch_text, True, (200, 200, 200))
        screen.blit(pitch_info, (10, GROUND_Y + 35))

def draw_button(text, center, width=240, height=70):
    """Desenha um botão"""
    rect = pygame.Rect(0, 0, width, height)
    rect.center = center
    pygame.draw.rect(screen, (50, 120, 220), rect, border_radius=12)
    label = font.render(text, True, (255, 255, 255))
    screen.blit(label, (rect.centerx - label.get_width()//2, rect.centery - label.get_height()//2))
    return rect

def draw_small_button(text, center, width=180, height=40):
    """Desenha um botão pequeno"""
    rect = pygame.Rect(0, 0, width, height)
    rect.center = center
    pygame.draw.rect(screen, (80, 80, 80), rect, border_radius=8)
    label = small_font.render(text, True, (255, 255, 255))
    screen.blit(label, (rect.centerx - label.get_width()//2, rect.centery - label.get_height()//2))
    return rect

def extend_game_map(target_length):
    """Estende o mapa dinamicamente conforme o jogador progride"""
    global game_map, max_generated_x
    
    if target_length <= len(game_map):
        return  # Já temos terreno suficiente
    
    # Altura do chão sempre a mesma (jogo plano)
    ground_level = GRID_HEIGHT - 3
    
    # Usar histórico dos últimos obstáculos para intercalação
    last_obstacle_types = []
    
    # Obter histórico dos últimos 3 terrenos existentes
    if len(game_map) >= 3:
        for i in range(len(game_map) - 3, len(game_map)):
            column = game_map[i]
            if column[ground_level - 1] == TERRAIN_LOW_CEILING:
                last_obstacle_types.append("low_ceiling")
            elif all(column[y] == TERRAIN_EMPTY for y in range(ground_level, GRID_HEIGHT)):
                last_obstacle_types.append("hole")
            else:
                last_obstacle_types.append("normal")
    
    # Gerar novos segmentos
    for x in range(len(game_map), target_length):
        column = [TERRAIN_EMPTY] * GRID_HEIGHT
        
        # Chão base sempre na mesma altura
        for y in range(ground_level, GRID_HEIGHT):
            column[y] = TERRAIN_GROUND
        
        # Decisão de obstáculos com maior frequência mas intercalados
        rand = random.random()
        obstacle_added = None
        
        # Verificar se o último obstáculo foi do mesmo tipo para evitar consecutivos
        last_hole = any(t == "hole" for t in last_obstacle_types[-1:])
        last_ceiling = any(t == "low_ceiling" for t in last_obstacle_types[-1:])
        
        # Aumentar chance de obstáculos para mais dificuldade (40% total vs 25% antes)
        if rand < 0.25 and not last_hole:  # 25% chance de buraco
            # Verificar se não há obstáculo baixo muito recente
            can_add_hole = True
            if last_obstacle_types and last_obstacle_types[-1] == "low_ceiling":
                can_add_hole = False
            
            if can_add_hole:
                # Remover chão para criar buraco
                for y in range(ground_level, GRID_HEIGHT):
                    column[y] = TERRAIN_EMPTY
                obstacle_added = "hole"
                print(f"Buraco dinâmico criado na posição {x}")
                        
        elif rand < 0.4 and not last_ceiling:  # 15% chance adicional de obstáculo baixo
            # Verificar se não há buraco muito recente
            can_add_ceiling = True
            if last_obstacle_types and last_obstacle_types[-1] == "hole":
                can_add_ceiling = False
            
            if can_add_ceiling:
                # Obstáculo baixo que precisa abaixar para passar
                obstacle_y = ground_level - 1
                column[obstacle_y] = TERRAIN_LOW_CEILING
                obstacle_added = "low_ceiling"
                print(f"Obstáculo baixo dinâmico criado na posição {x}")
        
        # Rastrear obstáculos para intercalação (manter histórico de 2 posições)
        if obstacle_added:
            last_obstacle_types.append(obstacle_added)
        else:
            last_obstacle_types.append("normal")
            
        if len(last_obstacle_types) > 2:
            last_obstacle_types.pop(0)
        
        game_map.append(column)
    
    max_generated_x = len(game_map) - 1
    print(f"Mapa estendido até posição {max_generated_x}")

# ================== LOOP PRINCIPAL ==================

def main():
    """Função principal do jogo"""
    global game_state, selected_device, mic_test_active, running, last_game_mode
    global barrier_timer, ball_x, ball_y, ball_target_y, barriers, lives, invulnerable_frames
    global score, pitch_detected, barrier_speed, ball_radius, barrier_spawn_interval
    global player_grid_x, player_grid_y, player_animation_state, animation_timer, game_map, map_scroll_x
    global show_help_popup, screen, clock, font, large_font, small_font
    
    # Garantir inicialização completa do pygame
    pygame.init()
    pygame.mixer.init()
    
    # Inicializar display e atualizar variável global screen
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Jogo de Voz")
    except pygame.error as e:
        print(f"Erro ao inicializar display: {e}")
        return
    
    # Inicializar outras variáveis globais
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    large_font = pygame.font.SysFont(None, 64)
    small_font = pygame.font.SysFont(None, 24)
    
    # Inicializar áudio
    initialize_audio()
    start_audio_stream()
    
    running = True
    
    while running:
        mouse_clicked = False
        mouse_pos = (0, 0)  # Valor padrão seguro
        
        # Verificar se o display está funcionando antes de pegar posição do mouse
        try:
            mouse_pos = pygame.mouse.get_pos()
        except pygame.error:
            mouse_pos = (0, 0)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_clicked = True
            # Controles de teclado para o jogo de comandos
            if event.type == pygame.KEYDOWN and game_state == "command_playing":
                if event.key == pygame.K_w:  # W = Saltar
                    voice_commands["saltar"] = True
                elif event.key == pygame.K_s:  # S = Abaixar
                    voice_commands["abaixar"] = True
                elif event.key == pygame.K_a:  # A = Correr
                    voice_commands["correr"] = True

        if game_state == "menu":
            btn1, btn2, btn3, btn4 = main_menu()
            if mouse_clicked:
                if btn1.collidepoint(mouse_pos):
                    reset_game()
                    game_state = "playing"
                elif btn2.collidepoint(mouse_pos):
                    reset_command_game()
                    start_command_recognition()
                    game_state = "command_playing"
                elif btn3.collidepoint(mouse_pos):
                    game_state = "mic_config"
                elif btn4.collidepoint(mouse_pos):
                    running = False

        elif game_state == "mic_config":
            device_buttons, test_btn, back_btn = microphone_config_menu()
            if mouse_clicked:
                # Verificar clique em dispositivo
                for btn in device_buttons:
                    if btn['rect'].collidepoint(mouse_pos):
                        selected_device = btn['device_id']
                        start_audio_stream()
                        break
                
                if test_btn.collidepoint(mouse_pos):
                    mic_test_active = True
                    game_state = "mic_test"
                elif back_btn.collidepoint(mouse_pos):
                    game_state = "menu"

        elif game_state == "mic_test":
            back_btn = microphone_test_menu()
            if mouse_clicked and back_btn.collidepoint(mouse_pos):
                mic_test_active = False
                game_state = "mic_config"

        elif game_state == "game_over":
            retry_btn, menu_btn = game_over_menu()
            if mouse_clicked:
                if retry_btn.collidepoint(mouse_pos):
                    # Verificar qual foi o último jogo jogado
                    if last_game_mode == "command":
                        print("🔄 Reiniciando jogo de comandos de voz...")
                        reset_command_game()
                        start_command_recognition()
                        game_state = "command_playing"
                    else:
                        print("🔄 Reiniciando jogo de tonalidade...")
                        reset_game()
                        game_state = "playing"
                elif menu_btn.collidepoint(mouse_pos):
                    print("🏠 Voltando ao menu principal...")
                    stop_command_recognition()
                    game_state = "menu"

        elif game_state == "playing":
            last_game_mode = "pitch"
            screen.fill((20, 20, 30))

            # Atualizar barreiras
            barrier_timer += 1
            if barrier_timer > barrier_spawn_interval:
                add_barrier()
                barrier_timer = 0
            for b in barriers:
                b['x'] -= barrier_speed
            barriers = [b for b in barriers if b['x'] + barrier_width > 0]

            # Colisão
            if invulnerable_frames == 0 and (check_collision() or ball_y < 0 or ball_y > HEIGHT):
                invulnerable_frames = SLOWDOWN_DURATION
                if lives <= 0:
                    game_state = "game_over"
            elif invulnerable_frames > 0:
                invulnerable_frames -= 1

            # Score e atualização de velocidade
            for b in barriers:
                if not b['passed'] and b['x'] + barrier_width < ball_x:
                    score += 1
                    b['passed'] = True
                    update_barrier_speed()

            if not pitch_detected:
                ball_target_y = GROUND_Y

            # Movimento da bola
            if ball_y < ball_target_y:
                ball_y += (ball_target_y - ball_y) * DESCENT_RESISTANCE
            else:
                ball_y = ball_target_y

            color = (0, 200, 255) if invulnerable_frames == 0 else (100, 100, 255)
            pygame.draw.circle(screen, color, (int(ball_x), int(ball_y)), ball_radius)

            draw_barriers()
            draw_lives()
            draw_pitch_info()
            draw_score()

        elif game_state == "command_playing":
            last_game_mode = "command"
            screen.fill((30, 20, 20))

            # Verificar colisões e invulnerabilidade
            if invulnerable_frames > 0:
                invulnerable_frames -= 1

            update_command_game()

            # Verificar se perdeu todas as vidas
            if lives <= 0:
                stop_command_recognition()
                game_state = "game_over"

            # Desenhar fundo/céu
            pygame.draw.rect(screen, (135, 206, 235), (0, 0, WIDTH, HEIGHT // 2))  # Céu azul

            draw_game_map()
            draw_command_player()
            draw_lives()
            help_button_rect = draw_command_info()
            draw_score()
            
            # Gerenciar cliques no popup de ajuda
            if mouse_clicked:
                if show_help_popup:
                    # Se popup está aberto, qualquer clique fecha
                    show_help_popup = False
                elif help_button_rect.collidepoint(mouse_pos):
                    # Clique no botão de ajuda abre popup
                    show_help_popup = True

        pygame.display.flip()
        clock.tick(60)

    # Cleanup
    if audio_stream:
        audio_stream.stop()
        audio_stream.close()
    stop_command_recognition()
pygame.quit()

if __name__ == "__main__":
    main()
